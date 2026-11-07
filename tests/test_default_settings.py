from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from patch_default_settings import patch_control
from check_default_settings_candidate import check_dependencies, check_payload


class DefaultSettingsTests(unittest.TestCase):
    def test_rebuild_retains_every_other_dependency(self):
        before = ('Source: openkylin-default-settings\n\nPackage: openkylin-default-settings\n'
                  'Depends: gnome-keyring,\n         kylin-daq,\n         ${misc:Depends}\n')
        after = patch_control(before)
        self.assertIn('gnome-keyring', after)
        self.assertIn('${misc:Depends}', after)
        self.assertNotIn('kylin-daq', after)
        original = 'gnome-keyring, kylin-daq, dconf-gsettings-backend | gsettings-backend'
        patched = 'gnome-keyring, dconf-gsettings-backend | gsettings-backend'
        check_dependencies(original, patched)
        for unexpected in ('gnome-keyring', original, 'dconf-gsettings-backend | gsettings-backend'):
            with self.subTest(unexpected=unexpected), self.assertRaises(ValueError):
                check_dependencies(original, unexpected)
        with self.assertRaises(ValueError):
            patch_control(before.replace('kylin-daq,', 'kylin-daq (>= 2),'))

    def test_configuration_assets_cannot_disappear_or_change(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = Path(directory) / 'before', Path(directory) / 'after'
            config = 'etc/apt/sources.list.d/openkylin-software.sources'
            changelog = 'usr/share/doc/openkylin-default-settings/changelog.gz'
            for root in (before, after):
                for path in (config, changelog):
                    (root / path).parent.mkdir(parents=True, exist_ok=True)
                    (root / path).write_bytes(b'original')
            (after / changelog).write_bytes(b'updated changelog')
            check_payload(before, after)
            (after / config).write_bytes(b'changed store source')
            with self.assertRaises(ValueError):
                check_payload(before, after)
            (after / config).unlink()
            with self.assertRaises(ValueError):
                check_payload(before, after)

    @unittest.skipUnless(shutil.which('apt-get') and shutil.which('dpkg'), 'requires Linux APT solver')
    def test_apt_purge_keeps_desktop_defaults_after_dependency_removal(self):
        # Reproduce #51 with an isolated package database; never use the host's
        # package status, sources, lists or cache, and always simulate changes.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            architecture = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
            empty = root / 'empty.list'
            empty.touch()
            (root / 'lists/partial').mkdir(parents=True)
            (root / 'cache/archives/partial').mkdir(parents=True)
            status = root / 'status'
            def planned(depends):
                records = []
                for name in ('desktop-core', 'kylin-daq', 'openkylin-default-settings'):
                    record = (f'Package: {name}\nStatus: install ok installed\nPriority: optional\n'
                              f'Section: misc\nArchitecture: {architecture}\nVersion: 1.0\n'
                              'Maintainer: Test <test@example.invalid>\nDescription: APT regression fixture\n')
                    if name == 'openkylin-default-settings':
                        record += f'Depends: {depends}\n'
                    records.append(record)
                status.write_text('\n'.join(records))
                output = subprocess.check_output(['apt-get',
                    '-o', f'Dir::State::status={status}', '-o', f'Dir::State::lists={root / "lists"}',
                    '-o', f'Dir::Cache={root / "cache"}', '-o', f'Dir::Etc::sourcelist={empty}',
                    '-o', 'Dir::Etc::sourceparts=-', '-o', 'APT::Get::AutomaticRemove=false',
                    '-o', 'Debug::NoLocking=true', '-s', 'purge', 'kylin-daq'], text=True,
                    stderr=subprocess.STDOUT, env={'PATH': str(Path(shutil.which('apt-get')).parent) + ':/usr/bin:/bin',
                                                  'LC_ALL': 'C'})
                return set(re.findall(r'^(?:Remv|Purg) (\S+)', output, re.M))
            self.assertEqual(planned('desktop-core, kylin-daq'), {'kylin-daq', 'openkylin-default-settings'})
            self.assertEqual(planned('desktop-core'), {'kylin-daq'})


if __name__ == '__main__':
    unittest.main()
