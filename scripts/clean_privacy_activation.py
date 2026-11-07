"""Remove stale systemd enablement links left by purged privacy services."""
import os
from pathlib import Path
import sys


def clean(root):
    services = {'kylin-daq.service', 'kylin-sso-client.service',
                'kylin-cloud-sync.service'}
    directory = root / 'etc/systemd/system'
    for path in directory.rglob('*'):
        if not path.is_symlink() or path.name not in services:
            continue
        if not path.parent.name.endswith(('.wants', '.requires')):
            continue
        target = path.readlink()
        # Accept only the reviewed vendor unit locations. Resolve absolute
        # image paths against root, never against the build host filesystem.
        if target not in {Path(prefix) / path.name for prefix in
                          ('/lib/systemd/system', '/usr/lib/systemd/system')}:
            continue
        image_target = root / target.relative_to('/')
        if not os.path.lexists(image_target):
            path.unlink()
            print(f'Removed stale privacy activation link: {path.relative_to(root)}')


if __name__ == '__main__':
    clean(Path(sys.argv[1]))
