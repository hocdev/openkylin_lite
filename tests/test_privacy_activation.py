from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from clean_privacy_activation import clean


class PrivacyActivationTests(unittest.TestCase):
    def test_cleanup_with_simulated_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wants = root / 'etc/systemd/system/multi-user.target.wants'
            wants.mkdir(parents=True)
            stale = wants / 'kylin-daq.service'
            present = wants / 'kylin-cloud-sync.service'
            unrelated = wants / 'network.service'
            unexpected = wants / 'kylin-sso-client.service'
            links = {stale: Path('/usr/lib/systemd/system/kylin-daq.service'),
                     present: Path('/usr/lib/systemd/system/kylin-cloud-sync.service'),
                     unrelated: Path('/usr/lib/systemd/system/network.service'),
                     unexpected: Path('/custom/kylin-sso-client.service')}
            for link in links:
                link.touch()
            unit = root / 'usr/lib/systemd/system/kylin-cloud-sync.service'
            unit.parent.mkdir(parents=True)
            unit.touch()
            with patch.object(Path, 'is_symlink', lambda path: path in links), \
                    patch.object(Path, 'readlink', lambda path: links[path]):
                clean(root)
            self.assertFalse(stale.exists())
            for retained in (present, unrelated, unexpected):
                self.assertTrue(retained.exists())

    @unittest.skipUnless(os.name == 'posix', 'requires POSIX symlinks')
    def test_removes_only_stale_reviewed_enablement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wants = root / 'etc/systemd/system/multi-user.target.wants'
            wants.mkdir(parents=True)
            stale = wants / 'kylin-daq.service'
            stale.symlink_to('/usr/lib/systemd/system/kylin-daq.service')
            unrelated = wants / 'network.service'
            unrelated.symlink_to('/usr/lib/systemd/system/network.service')
            present = wants / 'kylin-cloud-sync.service'
            present.symlink_to('/usr/lib/systemd/system/kylin-cloud-sync.service')
            unit = root / 'usr/lib/systemd/system/kylin-cloud-sync.service'
            unit.parent.mkdir(parents=True)
            unit.touch()
            unexpected = wants / 'kylin-sso-client.service'
            unexpected.symlink_to('/custom/kylin-sso-client.service')
            clean(root)
            self.assertFalse(stale.is_symlink())
            for retained in (unrelated, present, unexpected):
                self.assertTrue(retained.is_symlink())
            clean(root)


if __name__ == '__main__':
    unittest.main()
