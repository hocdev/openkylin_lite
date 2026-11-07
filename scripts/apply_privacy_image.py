"""Apply the legacy ABI patch inside the image's chroot, preserving package metadata."""
import hashlib
from pathlib import Path
import shutil
import subprocess

from_status = subprocess.run(['dpkg-query', '-W', '-f=${Status}\n${Version}',
                              'libkysdk-diagnostics'], capture_output=True, text=True)
if from_status.stdout.startswith('install ok installed\n'):
    version = from_status.stdout.splitlines()[1]
    if version != '3.0.1.0-ok0.1':
        raise SystemExit(f'Unreviewed legacy diagnostics version: {version}')
    owned = subprocess.check_output(['dpkg-query', '-L', 'libkysdk-diagnostics'], text=True).splitlines()
    targets = [Path(p) for p in owned if p.startswith('/usr/lib/') and p.endswith('/libkydiagnostics.so.3.0.1')]
    if len(targets) != 1 or not targets[0].is_file() or targets[0].is_symlink():
        raise SystemExit('Unexpected legacy diagnostics library layout')
    # This is a local source-built file patch, not a dependency metadata edit.
    shutil.copyfile('/tmp/legacy-diagnostics-disabled.so', targets[0])
    print(f'Patched {targets[0]} SHA256={hashlib.sha256(targets[0].read_bytes()).hexdigest()}')

for home in [Path('/etc/skel'), Path('/root'), *Path('/home').glob('*')]:
    cache = home / '.config/buriedpoint'
    if cache.is_symlink():
        cache.unlink()
    elif cache.is_dir():
        shutil.rmtree(cache)

preferences = Path('/etc/apt/preferences.d/openkylin-lite-privacy')
preferences.parent.mkdir(parents=True, exist_ok=True)
preferences.write_text('''Package: kylin-daq kylin-sso-client kylin-cloud-sync libsync-plugin
Pin: version *
Pin-Priority: -1

Package: libkysdk-datacollect libkysdk-datacollect-dev libkysdk-diagnosetest libkysdk-diagnosetest-dev libkysdk-diagnosetest-doc libkysdk-diagnostics ukui-control-center libukcc3
Pin: version *
Pin-Priority: -1
''')
print('Blocked repository reinstalls of removed services and unpatched telemetry/Settings libraries.')
