import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_apps import check_app


class AppPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fields = {'Version': '1.2', 'Priority': 'optional', 'Section': 'utils'}
        self.review = {'version': '1.2', 'reason': 'Unwanted bundled chat app',
                       'desktop': '/usr/share/applications/chat.desktop'}
        self.files = [self.review['desktop']]

    def test_reviewed_optional_application(self):
        check_app('chat', self.fields, self.review, self.files)

    def test_missing_review_and_changed_version(self):
        for review in (None, {}, {**self.review, 'version': '2.0'}):
            with self.subTest(review=review), self.assertRaises(ValueError):
                check_app('chat', self.fields, review, self.files)

    def test_system_metadata_overrides_review(self):
        for field, value in [('Essential', 'yes'), ('Protected', 'yes'),
                             ('Priority', 'required'), ('Priority', 'important'),
                             ('Priority', 'standard'), ('Section', 'libs')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                check_app('chat', {**self.fields, field: value}, self.review, self.files)

    def test_launcher_must_be_owned(self):
        with self.assertRaises(ValueError):
            check_app('chat', self.fields, self.review, [])

    def test_launcher_does_not_override_system_files(self):
        with self.assertRaises(ValueError):
            check_app('chat', self.fields, self.review,
                      self.files + ['/usr/lib/systemd/system/core.service'])


if __name__ == '__main__':
    unittest.main()
