import hashlib
import pathlib
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from update_iso_metadata import configure_live_boot, filter_remove_manifest, update_checksums


class IsoMetadataTests(unittest.TestCase):
    def test_english_boot_keeps_explicit_install_and_live_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            iso, meta = root / 'iso', root / 'meta'
            (iso / 'boot/grub').mkdir(parents=True)
            (iso / 'isolinux').mkdir()
            files = {
                'boot/grub/grub.cfg': 'set timeout=3\nlinux /casper/vmlinuz boot=casper locale=zh_CN live\n'
                                     'linux /casper/vmlinuz boot=casper only-ubiquity locale=zh_CN\n',
                'isolinux/isolinux.cfg': 'timeout 50\n',
                'isolinux/txt.cfg': '  append boot=casper live --\n  append boot=casper only-ubiquity --\n',
                'isolinux/lang': 'zh_CN\n',
            }
            for relative, content in files.items():
                (iso / relative).write_text(content, encoding='utf-8')
            def cpio_entry(name, payload):
                header = struct.pack('<13H', 0o70707, *([0] * 9), len(name), 0, len(payload))
                return header + name + bytes(len(name) % 2) + payload + bytes(len(payload) % 2)

            trailer = cpio_entry(b'TRAILER!!!\0', b'')
            (iso / 'isolinux/bootlogo').write_bytes(cpio_entry(b'lang\0', b'zh_CN\n') + trailer)
            updates = configure_live_boot(iso, meta)
            self.assertEqual(updates['isolinux/lang'].read_text(), 'en\n')
            self.assertEqual(updates['isolinux/bootlogo'].read_bytes(),
                             cpio_entry(b'lang\0', b'en\n') + trailer)
            self.assertEqual(updates['isolinux/isolinux.cfg'].read_text(), 'timeout 20\n')
            self.assertIn('set timeout=2', updates['boot/grub/grub.cfg'].read_text())
            for relative in ('boot/grub/grub.cfg', 'isolinux/txt.cfg'):
                text = updates[relative].read_text()
                self.assertEqual(text.count('locale=en_US.UTF-8'), 2)
                self.assertIn('only-ubiquity', text)
                self.assertNotIn('zh_CN', text)

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
