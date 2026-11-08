import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_dwz_for_debug import has_debug_info, optimize


class DwzInputTests(unittest.TestCase):
    def test_only_actual_debug_sections_count(self):
        self.assertTrue(has_debug_info(' [28] .debug_info PROGBITS 00000000\n'))
        self.assertTrue(has_debug_info(' [28] .zdebug_info PROGBITS 00000000\n'))
        self.assertFalse(has_debug_info(' [28] .debug_info.dwo PROGBITS 00000000\n'))
        self.assertFalse(has_debug_info(' [28] .dynsym DYNSYM 00000000\n'))

    def test_missing_debug_input_is_skipped_and_real_input_is_optimized(self):
        with tempfile.TemporaryDirectory() as temporary:
            previous = Path.cwd()
            try:
                os.chdir(temporary)
                root = Path('debian/app/usr/bin')
                root.mkdir(parents=True)
                plain = root / 'plain'
                debug = root / 'debug'
                plain.write_bytes(b'\x7fELFplain')
                debug.write_bytes(b'\x7fELFdebug')

                def output(command, **kwargs):
                    if command[0] == 'dh_listpackages':
                        return 'app\n'
                    return ' [28] .debug_info PROGBITS 00000000\n' if command[-1] == str(debug) else ''

                with patch('run_dwz_for_debug.subprocess.check_output', side_effect=output), \
                     patch('run_dwz_for_debug.subprocess.run') as run:
                    optimize()
                    run.assert_any_call(['objcopy', '--decompress-debug-sections', str(debug)], check=True)
                    run.assert_any_call(['dh_dwz', '-X' + str(plain)], check=True)
                debug.unlink()
                with patch('run_dwz_for_debug.subprocess.check_output', side_effect=output), \
                     patch('run_dwz_for_debug.subprocess.run') as run:
                    optimize()
                    run.assert_not_called()
            finally:
                os.chdir(previous)
