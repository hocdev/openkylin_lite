import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def simulate_systemdatasize(real_size_mib, ram_kib, is_vm, is_efi=True, is_swapfile=False):
    efi = 512 if is_efi else 0
    boot = 2048
    if is_vm:
        backup_size = 0
    elif real_size_mib < 65536:
        backup_size = 1024
    else:
        backup_size = real_size_mib // 9
        if backup_size < 16384:
            backup_size = 16384
        elif backup_size > 102400:
            backup_size = 102400

    swap = ram_kib * 12 // 1024 // 10
    if swap > 64000:
        swap = 64000
    if real_size_mib < 51200 and swap > 2048:
        swap = 2048
    elif swap > real_size_mib // 5:
        swap = real_size_mib // 5

    swapfile = 0
    if is_swapfile:
        swapfile = swap
        swap = 0

    free_size = real_size_mib - efi - boot - backup_size - swap
    root_size = free_size * 6 // 10
    if root_size < 20480:
        root_size = 20480
        if free_size < 0:
            raise ValueError('negative free_size')
    elif root_size > 102400:
        root_size = 102400
        if free_size < 204800:
            root_size = free_size * 5 // 10
    root_size += swapfile

    data_min_size = 1024 if real_size_mib < 51200 else real_size_mib * 2 // 10
    data_max_size = free_size - 20480 - swapfile
    if data_max_size < 0:
        raise ValueError('negative data_max_size')

    data_default_size = free_size - root_size
    if data_min_size > data_default_size:
        data_min_size = data_default_size // 2
    if data_min_size > data_max_size:
        data_min_size = data_max_size
    system_default_size = real_size_mib - data_default_size

    return {
        'efi': efi,
        'boot': boot,
        'backup_size': backup_size,
        'swap': swap,
        'swapfile': swapfile,
        'root_size': root_size,
        'data_default_size': data_default_size,
        'system_default_size': system_default_size,
        'data_min_size': data_min_size,
        'data_max_size': data_max_size,
    }


class InstallerPatchTests(unittest.TestCase):
    def test_patch_covers_all_50gb_and_root_limits(self):
        patch_file = REPO_ROOT / 'patches/installer/kylin-os-installer.patch'
        raw = patch_file.read_bytes()
        self.assertNotIn(b'\r\n', raw)
        text = raw.decode('utf-8')
        patched_files = {
            line.split()[2][2:]
            for line in text.splitlines()
            if line.startswith('diff --git ')
        }
        expected_files = {
            'data/systemdatasize.sh',
            'scripts/autopart-custom.sh',
            'scripts/autopart-efi-custom.sh',
            'scripts/autopart-efi.sh',
            'scripts/autopart.sh',
            'scripts/utils',
            'src/plugins/KPartition/createpartitionframe.cpp',
            'src/plugins/KPartition/createpartitionframe.h',
            'src/plugins/KPartition/delegate/custom_partition_delegate.cpp',
            'src/plugins/KPartition/delegate/full_partition_delegate.cpp',
            'src/plugins/KPartition/frames/levelscrolldiskview.cpp',
            'src/plugins/KPartition/mainpartframe.cpp',
            'src/plugins/KPartition/quickpartitionframe.cpp',
        }
        self.assertEqual(patched_files, expected_files)
        self.assertIn('+#define DISKMINSIZE 30', text)
        self.assertIn('+        int r = t - 30;//30G', text)
        self.assertIn('disk size less than 30G!', text)
        self.assertIn('Root partition size is greater than 20GB.', text)
        self.assertIn('+        root_required = 20;', text)

    def test_source_lock_and_workflow_invariants(self):
        locks = json.loads((REPO_ROOT / 'config/rebuild-sources.json').read_text(encoding='utf-8'))
        by_source = {entry['source']: entry for entry in locks['packages']}
        self.assertIn('kylin-os-installer', by_source)
        self.assertEqual(by_source['kylin-os-installer']['version'], '0.2.2-0k1.16')
        self.assertEqual(by_source['kylin-os-installer']['tag'], 'build/0.2.2-0k1.16')
        self.assertEqual(
            by_source['kylin-os-installer']['commit'],
            '15008beb5f39ccf33f920e03e6bcef24c2826b22',
        )

        workflow = (REPO_ROOT / '.github/workflows/lite.yml').read_text(encoding='utf-8')
        self.assertIn('group: openkylin-lite', workflow)
        self.assertIn('cancel-in-progress: true', workflow)
        self.assertIn('key: openkylin-source-v1-${{ env.SOURCE_SHA256 }}', workflow)
        self.assertIn('needs: [verify-sources, ukui-password-candidates, installer-candidate, control-center-candidate, ai-free-desktop]', workflow)

    def test_30gb_to_500gb_partition_sizing_invariants(self):
        for disk_gib in (30, 32, 40, 50, 64, 100, 500):
            real_size_mib = disk_gib * 1024
            for ram_gib in (2, 4, 8, 16, 32, 64):
                ram_kib = ram_gib * 1024 * 1024
                for is_vm in (True, False):
                    for is_efi in (True, False):
                        for is_swapfile in (False, True):
                            res = simulate_systemdatasize(
                                real_size_mib, ram_kib, is_vm, is_efi=is_efi, is_swapfile=is_swapfile
                            )
                            if not is_vm:
                                self.assertGreater(res['backup_size'], 0)
                            self.assertGreaterEqual(res['root_size'] - res['swapfile'], 20480)
                            self.assertGreater(res['data_default_size'], 0)
                            self.assertGreater(res['data_min_size'], 0)
                            self.assertLessEqual(res['data_min_size'], res['data_default_size'])
                            self.assertLessEqual(res['data_default_size'], res['data_max_size'])
                            self.assertLess(res['data_default_size'], real_size_mib)
                            total_used = (
                                res['efi']
                                + res['boot']
                                + res['backup_size']
                                + res['swap']
                                + res['root_size']
                                + res['data_default_size']
                            )
                            self.assertEqual(total_used, real_size_mib)


if __name__ == '__main__':
    unittest.main()
