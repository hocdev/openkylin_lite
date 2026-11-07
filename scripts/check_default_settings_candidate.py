"""Verify the defaults rebuild changes only version, telemetry dependency and changelog."""
from pathlib import Path
import stat
import subprocess
import sys
import tempfile


def dependency_groups(value):
    return [group.strip() for group in value.split(',') if group.strip()]


def check_dependencies(before, after):
    original, patched = dependency_groups(before), dependency_groups(after)
    if original.count('kylin-daq') != 1 or patched != [g for g in original if g != 'kylin-daq']:
        raise ValueError('Defaults dependencies differ beyond the reviewed telemetry removal')


def check_payload(before, after):
    def entries(root):
        return {p.relative_to(root).as_posix(): p for p in root.rglob('*')}
    old, new = entries(before), entries(after)
    if old.keys() != new.keys():
        raise ValueError('Defaults payload paths changed')
    changelogs = {'usr/share/doc/openkylin-default-settings/changelog.gz',
                 'usr/share/doc/openkylin-default-settings/changelog.Debian.gz'}
    for relative in old:
        a, b = old[relative], new[relative]
        if stat.S_IFMT(a.lstat().st_mode) != stat.S_IFMT(b.lstat().st_mode):
            raise ValueError(f'Defaults entry type changed: {relative}')
        if stat.S_IMODE(a.lstat().st_mode) != stat.S_IMODE(b.lstat().st_mode):
            raise ValueError(f'Defaults entry permissions changed: {relative}')
        if a.is_symlink():
            if a.readlink() != b.readlink():
                raise ValueError(f'Defaults symlink changed: {relative}')
        elif a.is_file() and relative not in changelogs and a.read_bytes() != b.read_bytes():
            raise ValueError(f'Desktop defaults asset changed: {relative}')


def main(original, patched):
    def field(deb, name):
        return subprocess.check_output(['dpkg-deb', '-f', deb, name], text=True).strip()
    if field(original, 'Version') != '1:3.0.2' or not field(patched, 'Version').startswith('1:3.0.2+lite'):
        raise ValueError('Unexpected defaults package versions')
    for name in ('Package', 'Architecture', 'Pre-Depends', 'Recommends', 'Suggests'):
        if field(original, name) != field(patched, name):
            raise ValueError(f'Defaults metadata changed: {name}')
    check_dependencies(field(original, 'Depends'), field(patched, 'Depends'))
    with tempfile.TemporaryDirectory() as directory:
        before, after = Path(directory) / 'before', Path(directory) / 'after'
        subprocess.run(['dpkg-deb', '-x', original, str(before)], check=True)
        subprocess.run(['dpkg-deb', '-x', patched, str(after)], check=True)
        check_payload(before, after)
    print('Desktop defaults payload preserved; only the telemetry dependency was removed.')


if __name__ == '__main__':
    main(*sys.argv[1:])
