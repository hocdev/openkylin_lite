"""Exercise the patched vendor shell script, rather than only its Python model."""
import os
import pathlib
import subprocess
import tempfile
import unittest

from test_installer_patch import simulate_systemdatasize


@unittest.skipUnless(os.environ.get('INSTALLER_SOURCE_DIR'), 'requires patched installer source')
class InstallerRuntimeTests(unittest.TestCase):
    def test_diagnostic_copy_logs_are_english(self):
        root = pathlib.Path(os.environ['INSTALLER_SOURCE_DIR'])
        script = (root / 'scripts/prepare/16copy-basic-filesystem').read_text(encoding='utf-8')
        for message in ('Copying basic filesystem...', 'Processing squashfs...',
                        'Squashfs processing complete', 'Filesystem copy complete'):
            self.assertIn('msg "' + message + '"', script)
        for path in (root / 'scripts').rglob('*'):
            if path.is_file() and path.suffix != '.orig':
                self.assertNotRegex(path.read_text(encoding='utf-8'), r'msg "[^"\n]*[\u4e00-\u9fff]')

    def test_language_suffix_is_normalized(self):
        source = pathlib.Path(os.environ['INSTALLER_SOURCE_DIR']) / 'scripts/utils'
        script = source.read_text(encoding='utf-8')
        block = script[script.index('installer_language=$(get_value language)'):script.index('\nset_backup()')]
        for value, expected in (('en_US.UTF-8', 'en_US'), ('en_US@variant', 'en_US'), ('zh_CN', 'zh_CN')):
            result = subprocess.run(['bash', '-c',
                'get_value() { echo "$TEST_VALUE"; };\n' + block + '\necho "$LANGUAGES"'],
                env={**os.environ, 'TEST_VALUE': value}, text=True, capture_output=True, check=True)
            self.assertEqual(result.stdout.strip(), expected)

    def test_optional_data_size_accepts_false_but_rejects_invalid_input(self):
        root = pathlib.Path(os.environ['INSTALLER_SOURCE_DIR'])
        for name in ('autopart.sh', 'autopart-efi.sh'):
            script = (root / 'scripts' / name).read_text(encoding='utf-8')
            block = script[script.index('data_customize_size=0'):script.index('data_device=$(get_value data-device)')]
            for value, expected in (('false', '1000'), ('', '1000'), ('0', '1000'), ('250', '250')):
                result = subprocess.run(['bash', '-c',
                    'get_value() { printf "%s" "$TEST_VALUE"; }\n'
                    + 'data_size=1000; free_size=30000\n' + block + '\necho "$data_size"',
                    ], env={**os.environ, 'TEST_VALUE': value}, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), expected)
                self.assertEqual(result.stderr, '')
            result = subprocess.run(['bash', '-c', 'get_value() { echo invalid; };\n' + block],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Invalid data-customize-size', result.stderr)

    def test_optional_dpms_and_mount_are_not_called_when_absent(self):
        source = pathlib.Path(os.environ['INSTALLER_SOURCE_DIR']) / 'scripts/prepare/01set-dpms'
        script = source.read_text(encoding='utf-8').split('case ${LANGUAGES}')[0]
        mocks = '''
xset() { if [[ "$*" == q ]]; then echo 'DPMS extension not supported'; else echo "xset $*"; fi; }
mountpoint() { return 1; }
umount() { echo unexpected-unmount >&2; return 1; }
sync() { :; }
sleep() { :; }
'''
        result = subprocess.run(['bash', '-c', mocks + script],
                                env={**os.environ, 'DISPLAY': ':0'}, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'xset s off')
        self.assertEqual(result.stderr, '')

    def test_real_partition_script_matches_validated_budgets(self):
        source = pathlib.Path(os.environ['INSTALLER_SOURCE_DIR']) / 'data/systemdatasize.sh'
        script = source.read_text()
        mocks = r'''
fdisk() { echo "$TEST_DISK_KIB"; }
systemd-detect-virt() { return "$TEST_PHYSICAL"; }
cat() { echo "MemTotal: $TEST_RAM_KIB kB"; }
grep() {
    if [[ "$1" == -q && "$2" == kyswapfile ]]; then
        return "$TEST_NO_SWAPFILE"
    fi
    command grep "$@"
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            script = script.replace('/var/log/installer/data-system-size.log', (pathlib.Path(tmp) / 'size.log').as_posix())
            for disk_mib in (28610, 30 * 1024, 50 * 1024, 64 * 1024, 500 * 1024):
                for ram_gib in (4, 64):
                    for physical in (False, True):
                        for efi in (False, True):
                            for swapfile in (False, True):
                                with self.subTest(disk=disk_mib, ram=ram_gib, physical=physical,
                                                  efi=efi, swapfile=swapfile):
                                    env = {**os.environ, 'TEST_DISK_KIB': str(disk_mib * 1024),
                                           'TEST_RAM_KIB': str(ram_gib * 1024 * 1024),
                                           'TEST_PHYSICAL': str(int(physical)),
                                           'TEST_NO_SWAPFILE': str(int(not swapfile)),
                                           'is_efi': str(efi).lower()}
                                    result = subprocess.run(['bash', '-c', mocks + '\n' + script,
                                                             'test', '/dev/mock'], env=env,
                                                            text=True, capture_output=True, check=True)
                                    sizes = dict(line.split(': ', 1) for line in result.stdout.splitlines()
                                                 if ': ' in line)
                                    expected = simulate_systemdatasize(disk_mib, ram_gib * 1024 * 1024,
                                                                       not physical, efi, swapfile)
                                    for shell_key, model_key in (
                                        ('root_default_size', 'root_size'),
                                        ('swap_default_size', 'swap'),
                                        ('backup_default_size', 'backup_size'),
                                        ('data_default_size', 'data_default_size'),
                                        ('data_min_size', 'data_min_size'),
                                        ('data_max_size', 'data_max_size'),
                                    ):
                                        self.assertEqual(int(sizes[shell_key]), expected[model_key])
                                    self.assertGreater(int(sizes['data_default_size']), 0)


if __name__ == '__main__':
    unittest.main()
