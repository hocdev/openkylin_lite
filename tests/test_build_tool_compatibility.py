from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from patch_build_tools import changelog_options, qch_target_properties, qt_future_constructors
from patch_cmake_isolation import patch as patch_isolation
import tempfile


class BuildToolCompatibilityTests(unittest.TestCase):
    def test_qt_constructor_syntax_keeps_template_return_values_and_layout(self):
        text = ('class QFutureInterface : public Base {\n'
                '    QFutureInterface<T>() : Base() {}\n'
                '    explicit QFutureInterface<T>(int state) : Base(state) {}\n'
                '    int member;\n'
                '    static QFutureInterface<T> create() { return QFutureInterface<T>(); }\n};\n')
        updated = qt_future_constructors(text)
        self.assertIn('QFutureInterface() : Base()', updated)
        self.assertIn('explicit QFutureInterface(int state)', updated)
        self.assertIn('static QFutureInterface<T> create() { return QFutureInterface<T>(); }', updated)
        self.assertIn('    int member;', updated)
        self.assertEqual(qt_future_constructors(updated), updated)

    def test_only_invalid_custom_target_property_is_removed(self):
        text = ('add_custom_target(KF5Config_QCH)\n'
                'set_target_properties(KF5Config_QCH PROPERTIES\n'
                '    IMPORTED TRUE\n'
                '    DOXYGEN_QCH_FILES "config.qch"\n)\n')
        updated = qch_target_properties(text)
        self.assertNotIn('IMPORTED TRUE', updated)
        self.assertIn('DOXYGEN_QCH_FILES "config.qch"', updated)
        library = text.replace('add_custom_target(KF5Config_QCH)',
                               'add_library(KF5Config_QCH UNKNOWN IMPORTED)')
        self.assertEqual(qch_target_properties(library), library)

    def test_only_deprecated_changelog_keyword_is_changed(self):
        text = "changelog_parse(file => 'debian/changelog'); print $file;\n"
        self.assertEqual(changelog_options(text),
                         "changelog_parse(filename => 'debian/changelog'); print $file;\n")

    def test_cmake_projects_are_updated_once_without_touching_quilt_backups(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'debian').mkdir()
            (root / 'nested').mkdir()
            (root / '.pc/vendor').mkdir(parents=True)
            text = 'cmake_minimum_required(VERSION 3.14)\nproject(sample LANGUAGES CXX)\n'
            main = root / 'CMakeLists.txt'
            child = root / 'nested/CMakeLists.txt'
            backup = root / '.pc/vendor/CMakeLists.txt'
            for path in (main, child, backup):
                path.write_text(text, encoding='utf-8')
            patch_isolation(root)
            patch_isolation(root)
            self.assertEqual(main.read_text(encoding='utf-8').count('lite-isolation.cmake'), 1)
            self.assertIn('../debian/lite-isolation.cmake', child.read_text(encoding='utf-8'))
            self.assertEqual(backup.read_text(encoding='utf-8'), text)
