import os
from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_ai_free import check_payload, dynamic_headers


class ElfAuditErrorsTests(unittest.TestCase):
    def test_audit_failure_identifies_the_file_and_tool_diagnostic(self):
        result = subprocess.CompletedProcess([], 0, '', 'malformed program header')
        with patch('check_ai_free.subprocess.run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'bad-file.*malformed program header'):
                dynamic_headers(Path('/image/bad-file'))

    def test_only_the_known_interpreter_diagnostic_uses_a_verified_fallback(self):
        legacy = subprocess.CompletedProcess([], 0, '',
                    'readelf: Error: Unable to find program interpreter name\n')
        fallback = subprocess.CompletedProcess([], 0, 'NEEDED libc.so.6\n', '')
        output = io.StringIO()
        with patch('check_ai_free.subprocess.run', side_effect=[legacy, fallback]) as run, \
             redirect_stdout(output):
            self.assertIn('NEEDED libc.so.6', dynamic_headers(Path('/image/program.debug')))
        self.assertIn('program.debug', output.getvalue())
        self.assertEqual(run.call_args_list[0].args[0][0], 'readelf')
        self.assertEqual(run.call_args_list[1].args[0][0], 'objdump')

    def test_fallback_failure_cannot_be_silently_ignored(self):
        legacy = subprocess.CompletedProcess([], 0, '',
                    'readelf: Error: Unable to find program interpreter name\n')
        failure = subprocess.CompletedProcess([], 1, '', 'unreadable ELF metadata')
        with patch('check_ai_free.subprocess.run', side_effect=[legacy, failure]):
            with self.assertRaisesRegex(ValueError, 'bad-file.*unreadable ELF metadata'):
                dynamic_headers(Path('/image/bad-file'))


@unittest.skipUnless(os.name == 'posix' and all(shutil.which(tool) for tool in
                      ('gcc', 'objcopy', 'objdump', 'strings')), 'requires Linux GNU ELF tools')
class NativeElfAuditTests(unittest.TestCase):
    def test_detached_debug_and_executable_are_both_inspected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'main.c'
            source.write_text('int main(void) { return 0; }\n', encoding='utf-8')
            image = root / 'image'
            image.mkdir()
            executable = image / 'program'
            debug = image / 'program.debug'
            subprocess.run(['gcc', '-g', str(source), '-o', str(executable)], check=True)
            subprocess.run(['objcopy', '--only-keep-debug', str(executable), str(debug)], check=True)
            self.assertIn('NEEDED', dynamic_headers(executable))
            dynamic_headers(debug)
            check_payload(image)

    def test_needed_ai_library_still_blocks_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            library_source = root / 'library.c'
            library_source.write_text('int ai_marker(void) { return 0; }\n', encoding='utf-8')
            library = root / 'libonnxruntime.so'
            subprocess.run(['gcc', '-shared', '-fPIC', str(library_source),
                            '-Wl,-soname,libonnxruntime.so', '-o', str(library)], check=True)
            source = root / 'main.c'
            source.write_text('int ai_marker(void); int main(void) { return ai_marker(); }\n', encoding='utf-8')
            image = root / 'image'
            image.mkdir()
            subprocess.run(['gcc', str(source), '-L' + str(root), '-lonnxruntime',
                            '-o', str(image / 'program')], check=True)
            with self.assertRaisesRegex(ValueError, 'ELF still links an AI runtime'):
                check_payload(image)
