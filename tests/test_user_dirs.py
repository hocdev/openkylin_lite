import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('user_dirs', Path(__file__).resolve().parents[1] / 'scripts/normalize_user_dirs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UserDirectoriesTests(unittest.TestCase):
    def test_migrate_templates_and_preserve_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = home / '模板'
            source.mkdir()
            (source / 'example.txt').write_text('template')
            module.normalize(home, 'en_US.UTF-8')
            self.assertFalse(source.exists())
            self.assertEqual((home / 'Templates/example.txt').read_text(), 'template')
            source.mkdir()
            (source / 'example.txt').write_text('different')
            module.normalize(home, 'en_US.UTF-8')
            self.assertEqual((source / 'example.txt').read_text(), 'different')
            self.assertEqual((home / 'Templates/example.txt').read_text(), 'template')
            self.assertIn('XDG_TEMPLATES_DIR="$HOME/Templates"', (home / '.config/user-dirs.dirs').read_text())

    def test_non_english_and_custom_paths_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / '模板').mkdir()
            module.normalize(home, 'zh_CN.UTF-8')
            self.assertTrue((home / '模板').exists())
            config = home / '.config'
            config.mkdir()
            path = config / 'user-dirs.dirs'
            path.write_text('XDG_TEMPLATES_DIR="$HOME/MyTemplates"\n')
            module.normalize(home, 'en_US.UTF-8')
            self.assertTrue((home / '模板').exists())
            self.assertIn('XDG_TEMPLATES_DIR="$HOME/MyTemplates"', path.read_text())
