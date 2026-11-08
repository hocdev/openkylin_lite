from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from patch_orca_translations import migrate_catalog, named_format


class OrcaTranslationsTests(unittest.TestCase):
    def test_named_formats_preserve_values_and_allow_reordering(self):
        self.assertEqual(named_format('CPU: %d%%. Memory: %d%%', ('cpu', 'memory')) %
                         {'cpu': 12, 'memory': 34}, 'CPU: 12%. Memory: 34%')
        self.assertEqual('%(last)s through %(first)s' % {'first': 'A1', 'last': 'A2'},
                         'A2 through A1')
        self.assertEqual(named_format('CPU: %%%d. Memory: %%%d', ('cpu', 'memory')) %
                         {'cpu': 12, 'memory': 34}, 'CPU: %12. Memory: %34')

    def test_catalog_context_multiline_and_other_messages_are_preserved(self):
        text = ('# Translator note\nmsgctxt "cell"\nmsgid ""\n'
                '"%s through "\n"%s selected"\n'
                'msgstr "%s đến %s đã chọn"\n\n'
                'msgid "unrelated"\nmsgstr "unchanged"\n')
        updated, count = migrate_catalog(text, {('cell', '%s through %s selected'):
                                               ('first', 'last')})
        self.assertEqual(count, 1)
        self.assertIn('msgstr "%(first)s đến %(last)s đã chọn"', updated)
        self.assertIn('# Translator note\nmsgctxt "cell"', updated)
        self.assertTrue(updated.endswith('msgid "unrelated"\nmsgstr "unchanged"\n'))

    def test_malformed_translation_requires_review(self):
        text = 'msgid "%s to %s"\nmsgstr "only %s"\n'
        with self.assertRaises(ValueError):
            migrate_catalog(text, {('', '%s to %s'): ('first', 'last')})

    def test_inactive_fuzzy_translation_is_retained_for_translators(self):
        text = '#, fuzzy, python-format\nmsgid "%s to %s"\nmsgstr "old %s"\n'
        updated, count = migrate_catalog(text, {('', '%s to %s'): ('first', 'last')})
        self.assertEqual(count, 1)
        self.assertIn('#, fuzzy, python-format', updated)
        self.assertIn('msgstr "old %s"', updated)
        self.assertIn('msgid "%(first)s to %(last)s"', updated)
