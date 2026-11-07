"""Exercise the actual offline cleanup snippets without running a remaster."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = (Path(__file__).resolve().parents[1] / 'scripts/remaster.sh').read_text(encoding='utf-8')
BEFORE = SCRIPT.split('chroot "$root" python3 - "$(cat "$work/planned")" <<\'PY\'\n', 1)[1].split('\nPY', 1)[0]
AFTER = SCRIPT.split('chroot "$root" python3 - <<\'PY\'\n', 1)[1].split('\nPY', 1)[0]


class RemovalCleanupTests(unittest.TestCase):
    def test_preserves_owned_files_and_rejects_nonempty_leftovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'etc/biometric-auth'
            directory.mkdir(parents=True)
            owned = directory / 'shared.conf'
            owned.write_text('retained package data')
            generated = directory / 'generated.db'
            generated.touch()
            info = root / 'var/lib/dpkg/info'
            info.mkdir(parents=True)
            (info / 'retained.list').write_text('/etc/biometric-auth/shared.conf\n')
            with patch.object(sys, 'argv', ['cleanup', 'biometric-auth']):
                exec(BEFORE.replace("root = Path('/')", 'root = test_root'), {'test_root': root})
            self.assertEqual(owned.read_text(), 'retained package data')
            self.assertFalse(generated.exists())
            code = AFTER.replace("Path('/etc/biometric-auth')", 'test_directory')
            with self.assertRaises(OSError):
                exec(code, {'test_directory': directory})
            self.assertTrue(owned.exists())
            owned.unlink()
            exec(code, {'test_directory': directory})
            self.assertFalse(directory.exists())

    def test_refuses_symlink_before_traversing_generated_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'etc/biometric-auth'
            with patch.object(Path, 'is_symlink', lambda path: path == directory), \
                    patch.object(sys, 'argv', ['cleanup', 'biometric-auth']):
                with self.assertRaisesRegex(SystemExit, 'symlink'):
                    exec(BEFORE.replace("root = Path('/')", 'root = test_root'), {'test_root': root})


if __name__ == '__main__':
    unittest.main()
