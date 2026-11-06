"""Fail closed: permit only version-pinned, reviewed desktop applications."""
import json
import pathlib
import subprocess
import sys


def read_status(text):
    packages = {}
    for paragraph in text.split('\n\n'):
        fields = {}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ': ' in line:
                key, value = line.split(': ', 1)
                fields[key] = value
        if fields.get('Status') == 'install ok installed':
            packages[fields['Package']] = fields
    return packages


def check_app(name, fields, review, owned_files):
    if not isinstance(review, dict):
        raise ValueError(f'{name}: missing reviewed-apps.json entry')
    for key in ('version', 'reason', 'desktop'):
        if not isinstance(review.get(key), str) or not review[key].strip():
            raise ValueError(f'{name}: missing review field {key}')
    if review['version'] != fields.get('Version'):
        raise ValueError(f'{name}: reviewed version differs from installed version')
    if fields.get('Essential') == 'yes' or fields.get('Protected') == 'yes':
        raise ValueError(f'{name}: Essential/Protected package')
    if fields.get('Priority', '').lower() not in ('optional', 'extra'):
        raise ValueError(f'{name}: only optional/extra applications may be removed')
    section = fields.get('Section', '').split('/')[-1]
    if section in {'admin', 'libs', 'libdevel', 'kernel', 'metapackages',
                   'x11', 'fonts', 'localization', 'debian-installer'}:
        raise ValueError(f'{name}: protected package section {section}')
    desktop = pathlib.PurePosixPath(review['desktop'])
    if (desktop.parent != pathlib.PurePosixPath('/usr/share/applications')
            or desktop.suffix != '.desktop' or str(desktop) not in owned_files):
        raise ValueError(f'{name}: must own the reviewed desktop launcher')
    # A desktop launcher alone is insufficient: system settings also own them.
    protected_prefixes = ('/boot/', '/lib/modules/', '/usr/lib/modules/',
                          '/lib/systemd/', '/usr/lib/systemd/',
                          '/usr/share/initramfs-tools/', '/etc/pam.d/',
                          '/usr/share/polkit-1/', '/usr/share/xsessions/',
                          '/usr/share/wayland-sessions/')
    if any(path.startswith(protected_prefixes) for path in owned_files):
        raise ValueError(f'{name}: owns protected system integration files')


def main():
    root, list_file, review_file = map(pathlib.Path, sys.argv[1:])
    installed = read_status((root / 'var/lib/dpkg/status').read_text())
    reviews = json.loads(review_file.read_text())
    selected = [line.split('#', 1)[0].strip() for line in list_file.read_text().splitlines()]
    for name in filter(None, selected):
        if name not in installed:
            raise ValueError(f'{name}: not installed')
        files = subprocess.check_output(['chroot', str(root), 'dpkg-query', '-L', name], text=True).splitlines()
        check_app(name, installed[name], reviews.get(name), files)
        launcher = root / reviews[name]['desktop'].lstrip('/')
        if not launcher.is_file():
            raise ValueError(f'{name}: launcher missing')
        print(f'APPROVED\t{name}\t{reviews[name]["version"]}\t{reviews[name]["reason"]}')


if __name__ == '__main__':
    main()
