"""Exercise the patched vendor shell script, rather than only its Python model."""
import os
import pathlib
import subprocess
import tempfile
import unittest

from test_installer_patch import simulate_systemdatasize


@unittest.skipUnless(os.environ.get('INSTALLER_SOURCE_DIR'), 'requires patched installer source')
class InstallerRuntimeTests(unittest.TestCase):
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
