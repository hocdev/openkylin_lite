import hashlib
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from update_iso_metadata import filter_remove_manifest, update_checksums


class IsoMetadataTests(unittest.TestCase):
    def test_preserves_installer_removal_rules(self):
        text = '# install-only cleanup\ncasper\nwps-office\nkylin-os-installer\n'
        self.assertEqual(filter_remove_manifest(text, {'wps-office'}),
                         '# install-only cleanup\ncasper\nkylin-os-installer\n')

    def test_checksum_updates_payload_preserves_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = pathlib.Path(directory) / 'payload'
            payload.write_bytes(b'new')
            for algorithm in ('md5', 'sha256'):
                expected = hashlib.new(algorithm, b'new').hexdigest()
                text = 'old  ./casper/filesystem.squashfs\nkeep  ./casper/vmlinuz\n'
                result = update_checksums(text, {'casper/filesystem.squashfs': payload}, algorithm)
                self.assertEqual(result, f'{expected}  ./casper/filesystem.squashfs\nkeep  ./casper/vmlinuz\n')


if __name__ == '__main__':
    unittest.main()
