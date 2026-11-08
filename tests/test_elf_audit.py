from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_ai_free import read_dynamic, is_split_debug

ERROR = 'readelf: Error: Unable to find program interpreter name\n'


def debug_fixture(bits, endian, interp_kind):
    header_format = endian + ('HHIIIIIHHHHHH' if bits == 32 else 'HHIQQQIHHHHHH')
    section_format = endian + ('IIIIIIIIII' if bits == 32 else 'IIQQQQIIQQ')
    header_size = 16 + struct.calcsize(header_format)
    section_size = struct.calcsize(section_format)
    names = b'\0.interp\0.dynamic\0.shstrtab\0'
    ident = b'\x7fELF' + bytes([1 if bits == 32 else 2, 1 if endian == '<' else 2, 1]) + bytes(9)
    header = struct.pack(header_format, 3, 62, 1, 0, 0, header_size, 0,
                         header_size, 0, 0, section_size, 4, 3)
    sections = [struct.pack(section_format, *([0] * 10)),
                struct.pack(section_format, 1, interp_kind, 2, 0, 0, 0, 0, 0, 1, 0),
                struct.pack(section_format, 9, 8, 2, 0, 0, 0, 0, 0, 1, 0),
                struct.pack(section_format, 18, 3, 0, 0, header_size + 4 * section_size,
                            len(names), 0, 0, 1, 0)]
    return ident + header + b''.join(sections) + names


class ElfAuditTests(unittest.TestCase):
    def test_debug_companion_requires_nobits_sections(self):
        for bits in (32, 64):
            for endian in ('<', '>'):
                for kind, allowed in ((8, True), (1, False)):
                    with self.subTest(bits=bits, endian=endian, kind=kind), tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / 'companion.debug'
                        path.write_bytes(debug_fixture(bits, endian, kind))
                        self.assertEqual(is_split_debug(path), allowed)
                        with patch('check_ai_free.subprocess.run', return_value=
                                   subprocess.CompletedProcess([], 1, 'dynamic output', ERROR)) as tool:
                            if allowed:
                                self.assertEqual(read_dynamic(path), 'dynamic output')
                            else:
                                with self.assertRaisesRegex(ValueError, 'companion.debug'):
                                    read_dynamic(path)
                            self.assertEqual(tool.call_count, 1)
                        path.write_bytes(path.read_bytes()[:70])
                        self.assertFalse(is_split_debug(path))

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
