import pathlib
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from check_control_center_dependencies import unsatisfied_dependencies


class ControlCenterDependenciesTests(unittest.TestCase):
    def test_new_archive_library_requirement_is_rejected(self):
        compare = Mock(return_value=False)
        self.assertEqual(unsatisfied_dependencies(
            'libukui-quick-platform1 (>= 4.25.1.0)',
            {'libukui-quick-platform1': '4.25.0.0-ok0.2'}, compare),
            ['libukui-quick-platform1 (>= 4.25.1.0)'])
        compare.assert_called_once_with('4.25.0.0-ok0.2', '>=', '4.25.1.0')

    def test_alternatives_multiarch_and_unversioned_packages(self):
        compare = Mock(return_value=True)
        self.assertEqual(unsatisfied_dependencies(
            'missing | libqt5gui5:any (>= 5.14.1), dconf-gsettings-backend',
            {'libqt5gui5': '5.15.10', 'dconf-gsettings-backend': '0.40'}, compare), [])
        compare.assert_called_once_with('5.15.10', '>=', '5.14.1')

    def test_missing_group_and_invalid_syntax_fail_closed(self):
        self.assertEqual(unsatisfied_dependencies('missing | absent', {}), ['missing | absent'])
        with self.assertRaises(ValueError):
            unsatisfied_dependencies('libexample (not-a-version-check)', {})


if __name__ == '__main__':
    unittest.main()
