from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ai_policy import REMOVALS, REBUILT, is_ai_package
from check_ai_free import check_packages, check_payload
from check_apps import check_app


class AiPolicyTests(unittest.TestCase):
    def test_ai_cannot_return_as_dependency_or_optional_feature(self):
        for field in ('Depends', 'Pre-Depends', 'Recommends', 'Suggests'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'AI reference'):
                check_packages({'ordinary-app': {field: 'libc6, libkysdk-coreai-vision0 (>= 1.0)'}})
        check_packages({'ukui-search': {'Depends': 'libukui-search2, libc6'}})

    def test_shared_desktop_and_audio_libraries_are_not_ai(self):
        for name in ('libukui-search2', 'libukui-file-metadata1', 'libopencv-core406',
                     'libespeak-ng1', 'speech-dispatcher-espeak-ng', 'libkysdk-qtwidgets'):
            self.assertFalse(is_ai_package(name), name)
        for name in REMOVALS:
            self.assertTrue(is_ai_package(name), name)
        self.assertFalse(set(REBUILT) & set(REMOVALS))

    def test_models_block_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'model.onnx').write_bytes(b'model')
            with self.assertRaisesRegex(ValueError, 'model payload'):
                check_payload(root)

    def test_ai_removal_does_not_allow_unrelated_system_units(self):
        name = 'peony-intelligent-data-management-service'
        review = REMOVALS[name]
        fields = {'Version': review['version'], 'Section': review['section'], 'Priority': 'optional'}
        check_app(name, fields, review, ['/usr/lib/systemd/user/' + name + '.service'])
        with self.assertRaises(ValueError):
            check_app(name, fields, review, ['/usr/lib/systemd/user/network.service'])


if __name__ == '__main__':
    unittest.main()
