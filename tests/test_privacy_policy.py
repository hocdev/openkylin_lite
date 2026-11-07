import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_apps import check_app
from prepare_privacy_removals import prepare
from check_privacy_image import audit


class PrivacyPolicyTests(unittest.TestCase):
    def test_only_reviewed_daq_service_is_allowed(self):
        fields = {'Version': '1.2.9.2-ok2.2', 'Section': 'universe/admin', 'Priority': 'optional'}
        review = {'version': fields['Version'], 'section': fields['Section'],
                  'kind': 'privacy-component', 'reason': 'User requested removal'}
        check_app('kylin-daq', fields, review, ['/usr/lib/systemd/system/kylin-daq.service'])
        for files in (['/usr/lib/systemd/system/core.service'], ['/etc/pam.d/common-auth']):
            with self.assertRaises(ValueError):
                check_app('kylin-daq', fields, review, files)
        with self.assertRaises(ValueError):
            check_app('kylin-daq', {**fields, 'Version': '9.0'}, review, [])

    def test_absent_optional_packages_do_not_enter_purge_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = root / 'var/lib/dpkg/status'
            status.parent.mkdir(parents=True)
            status.write_text('Package: kylin-sso-client\nStatus: install ok installed\n'
                              'Version: 2.2.11.2-0k1.18\nSection: misc\nPriority: optional\n')
            selected, reviewed, output = root / 'list', root / 'reviews', root / 'output'
            selected.write_text('# Base plan\nwps-office\n')
            reviewed.write_text('{}')
            prepare(root, selected, reviewed, output)
            self.assertEqual((output / 'remove-packages.txt').read_text().splitlines(),
                             ['wps-office', 'kylin-sso-client'])
            self.assertEqual(json.loads((output / 'reviewed-apps.json').read_text())
                             ['kylin-sso-client']['kind'], 'privacy-component')
            status.write_text(status.read_text().replace('2.2.11.2-0k1.18', '9.0'))
            with self.assertRaises(ValueError):
                prepare(root, selected, reviewed, output)

    def test_image_audit_rejects_activation_and_noninert_sdk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = root / 'var/lib/dpkg/status'
            status.parent.mkdir(parents=True)
            status.write_text('Package: libkysdk-datacollect\nStatus: install ok installed\n'
                              'Version: 3.0.1.0-0k0.1update1+lite1\n')
            library = root / 'usr/lib/x86_64-linux-gnu/libkysdk-datacollect.so.3.0.0'
            library.parent.mkdir(parents=True)
            library.touch()
            with patch('check_privacy_image.subprocess.check_output', return_value=' U calloc@GLIBC_2.2.5\n U free@GLIBC_2.2.5\n'):
                audit(root)
            with patch('check_privacy_image.subprocess.check_output', return_value=' U connect@GLIBC_2.2.5\n'):
                with self.assertRaises(ValueError):
                    audit(root)
            hook = root / 'usr/share/dbus-1/services/cloud.service'
            hook.parent.mkdir(parents=True)
            hook.write_text('Exec=/usr/bin/kylin-cloud-sync')
            with self.assertRaises(ValueError):
                audit(root)
            hook.unlink()
            status.write_text(status.read_text() + '\nPackage: openkylin-default-settings\n'
                              'Status: install ok installed\nVersion: 1:3.0.2\nDepends: kylin-daq\n')
            with self.assertRaisesRegex(ValueError, 'hard dependency'):
                audit(root)


if __name__ == '__main__':
    unittest.main()
