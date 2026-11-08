import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('lightweight', Path(__file__).resolve().parents[1] / 'scripts/apply_lightweight_desktop.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LightweightDesktopTests(unittest.TestCase):
    def test_static_fallback_and_existing_config_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backgrounds = root / 'usr/share/backgrounds'
            backgrounds.mkdir(parents=True)
            (backgrounds / 'default.pag').write_bytes(b'animation')
            (backgrounds / 'default.jpg').write_bytes(b'static')
            schemas = root / 'usr/share/glib-2.0/schemas'
            schemas.mkdir(parents=True)
            (schemas / 'personalise.gschema.xml').write_text('''<schemalist>
              <schema id="org.ukui.control-center.personalise">
                <key name="effect" type="b"/><key name="transparency" type="d"/>
                <key name="blurry" type="i"/>
              </schema></schemalist>''')
            config = root / 'etc/skel/.config/kwinrc'
            config.parent.mkdir(parents=True)
            config.write_text('[Windows]\nFocusPolicy=ClickToFocus\n')
            module.apply(root)
            module.apply(root)
            self.assertFalse((backgrounds / 'default.pag').exists())
            self.assertEqual((backgrounds / 'default.jpg').read_bytes(), b'static')
            self.assertIn('FocusPolicy=ClickToFocus', config.read_text())
            self.assertIn('blurEnabled=false', config.read_text())
            self.assertIn('effect=false', (schemas / 'zz-openkylin-lite.gschema.override').read_text())

    def test_missing_static_fallback_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            animation = Path(tmp) / 'usr/share/backgrounds/lone.pag'
            animation.parent.mkdir(parents=True)
            animation.write_bytes(b'animation')
            with self.assertRaisesRegex(ValueError, 'static fallback'):
                module.apply(tmp)
            self.assertTrue(animation.exists())
