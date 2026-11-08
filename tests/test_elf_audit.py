from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_ai_free import read_dynamic

ERROR = 'readelf: Error: Unable to find program interpreter name\n'


class ElfAuditTests(unittest.TestCase):
    def test_debug_companion_requires_nobits_sections(self):
        for sections, allowed in (
            ('[ 1] .interp NOBITS 00\n[ 2] .dynamic NOBITS 00\n', True),
            ('[ 1] .interp PROGBITS 00\n[ 2] .dynamic DYNAMIC 00\n', False),
            ('[ 1] .interp NOBITS 00\n', False),
        ):
            responses = [subprocess.CompletedProcess([], 1, 'dynamic output', ERROR),
                         subprocess.CompletedProcess([], 0, sections, '')]
            with patch('check_ai_free.subprocess.run', side_effect=responses):
                if allowed:
                    self.assertEqual(read_dynamic(Path('companion.debug')), 'dynamic output')
                else:
                    with self.assertRaisesRegex(ValueError, 'companion.debug'):
                        read_dynamic(Path('companion.debug'))

    def test_other_errors_are_not_hidden(self):
        for error in ('corrupt ELF', ERROR + 'another error\n'):
            with patch('check_ai_free.subprocess.run', return_value=
                       subprocess.CompletedProcess([], 1, '', error)):
                with self.assertRaisesRegex(ValueError, 'Cannot audit ELF'):
                    read_dynamic(Path('bad-elf'))

    @unittest.skipUnless(sys.platform == 'linux' and shutil.which('objcopy') and shutil.which('readelf'),
                         'requires Linux binutils; exercised by ISO workflow')
    def test_real_runtime_and_split_debug_companion(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(shutil.which('true'))
            companion = Path(tmp) / 'true.debug'
            subprocess.run(['objcopy', '--only-keep-debug', str(runtime), str(companion)], check=True)
            self.assertIn('NEEDED', read_dynamic(runtime))
            read_dynamic(companion)
