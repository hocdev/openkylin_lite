from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ai_policy import REMOVALS, REBUILT, is_ai_package
from check_ai_free import check_packages, check_payload, check_image
from check_apps import check_app


class AiPolicyTests(unittest.TestCase):
    def test_ai_cannot_return_as_dependency_or_optional_feature(self):
        for field in ('Depends', 'Pre-Depends', 'Recommends', 'Suggests'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'AI reference'):
                check_packages({'ordinary-app': {field: 'libc6, libkysdk-coreai-vision0 (>= 1.0)'}})
        check_packages({'ukui-search': {'Depends': 'libukui-search2, libc6'}})

    def test_shared_desktop_and_audio_libraries_are_not_ai(self):
        for name in ('libukui-search2', 'libukui-file-metadata1', 'libopencv-core406',
                     'libespeak-ng1', 'speech-dispatcher-espeak-ng', 'libkysdk-qtwidgets', 'libsonic0'):
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

    def test_firefox_exception_is_limited_to_image_application_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fx_dir = root / 'opt/apps/net.mozilla.firefox'
            fx_dir.mkdir(parents=True)
            (fx_dir / 'model.onnx').write_bytes(b'model')
            (fx_dir / 'libonnxruntime.so').write_bytes(b'\x7fELF')
            check_image(root)
            with self.assertRaisesRegex(ValueError, 'model payload|runtime payload'):
                check_payload(root)

    def test_var_application_payload_is_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / 'var/opt/apps/ordinary-app'
            app.mkdir(parents=True)
            (app / 'model.onnx').write_bytes(b'model')
            with self.assertRaisesRegex(ValueError, 'model payload'):
                check_image(root)

    def test_same_firefox_directory_name_elsewhere_is_not_exempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / 'usr/share/net.mozilla.firefox'
            app.mkdir(parents=True)
            (app / 'model.onnx').write_bytes(b'model')
            with self.assertRaisesRegex(ValueError, 'model payload'):
                check_image(root)

    def test_firmware_exception_is_limited_to_image_application_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fw_dir = root / 'usr/lib/firmware/qcom/apq8096'
            fw_dir.mkdir(parents=True)
            (fw_dir / 'model.onnx').write_bytes(b'model')
            (fw_dir / 'libonnxruntime.so').write_bytes(b'\x7fELF')
            check_image(root)
            with self.assertRaisesRegex(ValueError, 'model payload|runtime payload'):
                check_payload(root)

    def test_same_firmware_directory_name_elsewhere_is_not_exempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / 'usr/share/firmware'
            app.mkdir(parents=True)
            (app / 'model.onnx').write_bytes(b'model')
            with self.assertRaisesRegex(ValueError, 'model payload'):
                check_image(root)

    def test_standalone_runtime_is_rejected_without_elf_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'libonnxruntime.so').write_bytes(b'runtime')
            with self.assertRaisesRegex(ValueError, 'runtime payload'):
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
