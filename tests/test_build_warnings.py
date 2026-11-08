import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from report_build_warnings import collect, report


class BuildWarningsTests(unittest.TestCase):
    def test_repeated_diagnostics_are_counted_without_losing_locations(self):
        text = ('/tmp/tmp.one/source/main.cpp:7: warning: missing return [-Wreturn-type]\n'
                '/tmp/tmp.two/source/main.cpp:7: warning: missing return [-Wreturn-type]\n'
                'CMake Deprecation Warning at CMakeLists.txt:1 (cmake_minimum_required):\n'
                'meson.build:3: WARNING: missing native\n'
                'g++ -DQT_DEPRECATED_WARNINGS -c main.cpp\n')
        warnings = collect(text)
        self.assertEqual(len(warnings), 3)
        repeated = next(w for w in warnings if 'main.cpp:7' in w['message'])
        self.assertEqual(repeated['occurrences'], 2)

    def test_failed_build_status_and_complete_log_are_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / 'build.log'
            text = 'main.cpp:1: warning: bad type\ncompiler context\nerror: build failed\n'
            log.write_text(text, encoding='utf-8')
            report(log, 17)
            result = json.loads(log.with_name('warnings.json').read_text(encoding='utf-8'))
            self.assertEqual(result['exit_code'], 17)
            self.assertEqual(result['unique_diagnostics'], 1)
            self.assertEqual(log.read_text(encoding='utf-8'), text)
