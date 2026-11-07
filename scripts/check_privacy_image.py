"""Reject images with telemetry/cloud packages or activation hooks still present."""
from pathlib import Path
import re
import subprocess
import sys
from check_apps import PRIVACY_COMPONENTS, read_status


def audit(root):
    installed = read_status((root / 'var/lib/dpkg/status').read_text())
    remaining = set(installed) & set(PRIVACY_COMPONENTS)
    if remaining:
        raise ValueError(f'Telemetry/cloud packages remain: {sorted(remaining)}')
    for name, fields in installed.items():
        for field in ('Depends', 'Pre-Depends'):
            names = re.findall(r'[a-z0-9][a-z0-9+.-]*', re.sub(r'\([^)]*\)', '', fields.get(field, '')))
            if set(names) & set(PRIVACY_COMPONENTS):
                raise ValueError(f'{name}: hard dependency on a removed privacy component in {field}')
    sdk = installed.get('libkysdk-datacollect', {})
    if not sdk.get('Version', '').startswith('3.0.1.0-0k0.1update1+lite'):
        raise ValueError('The disabled telemetry SDK is missing')
    marker = re.compile(rb'com\.kylin\.(?:daq|cloud-sync)|org\.kylinssoclient|'
                        rb'(?<![\w-])(?:kylin-daq(?:-daemon)?|kylin-sso-client|kylin-cloud-sync)(?![\w-])')
    for relative in ('etc/xdg/autostart', 'usr/share/autostart', 'etc/systemd',
                     'usr/lib/systemd', 'lib/systemd', 'etc/dbus-1', 'usr/share/dbus-1'):
        directory = root / relative
        if not directory.is_dir():
            continue
        for path in directory.rglob('*'):
            if path.is_symlink():
                target = path.readlink().as_posix().encode()
                if marker.search(target):
                    raise ValueError(f'Telemetry/cloud activation symlink remains: {path}')
            elif path.is_file() and marker.search(path.read_bytes()):
                raise ValueError(f'Telemetry/cloud activation hook remains: {path}')
    libraries = list((root / 'usr/lib').glob('*/libkysdk-datacollect.so.3.0.0'))
    if len(libraries) != 1:
        raise ValueError('Expected exactly one disabled telemetry shared library')
    symbols = subprocess.check_output(['nm', '-D', '--undefined-only', str(libraries[0])], text=True)
    # The replacement must remain allocation-only; no file, IPC or network APIs.
    allowed = {'calloc', 'free', '_ITM_deregisterTMCloneTable', '_ITM_registerTMCloneTable',
               '__cxa_finalize', '__gmon_start__'}
    actual = {line.split()[-1].split('@')[0] for line in symbols.splitlines() if line.split()}
    if actual - allowed:
        raise ValueError(f'Disabled SDK has unexpected external calls: {sorted(actual - allowed)}')
    if 'libkysdk-diagnostics' in installed:
        legacy = list((root / 'usr/lib').glob('*/libkydiagnostics.so.3.0.1'))
        if len(legacy) != 1:
            raise ValueError('Unexpected legacy diagnostics library layout')
        imports = subprocess.check_output(['nm', '-D', '--undefined-only', str(legacy[0])], text=True)
        names = {line.split()[-1].split('@')[0] for line in imports.splitlines() if line.split()}
        if names - allowed:
            raise ValueError(f'Legacy diagnostics still has external operations: {sorted(names-allowed)}')
        exports = subprocess.check_output(['nm', '-D', '--defined-only', str(legacy[0])], text=True)
        if {line.split()[-1] for line in exports.splitlines() if line.split()} != {'kdk_buried_point'}:
            raise ValueError('Unexpected legacy diagnostics ABI')
    print('Telemetry and SSO packages/activation hooks absent; SDK has allocation-only imports.')


if __name__ == '__main__':
    audit(Path(sys.argv[1]))
