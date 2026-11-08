"""Run DWARF optimization only when the binary actually contains DWARF input."""
from pathlib import Path
import re
import subprocess


def has_debug_info(sections):
    return bool(re.search(r'\s\.(?:z)?debug_info\s', sections))


def optimize():
    packages = subprocess.check_output(['dh_listpackages'], text=True).split()
    exclusions = []
    debug_files = []
    for package in packages:
        root = Path('debian') / package
        for path in root.rglob('*'):
            if path.is_symlink() or not path.is_file():
                continue
            with path.open('rb') as stream:
                if stream.read(4) != b'\x7fELF':
                    continue
            sections = subprocess.check_output(
                ['objdump', '--section-headers', '--wide', str(path)], text=True)
            if not has_debug_info(sections):
                exclusions.append('-X' + str(path))
                continue
            # dwz requires uncompressed input; dh_strip handles the final debug package.
            subprocess.run(['objcopy', '--decompress-debug-sections', str(path)], check=True)
            debug_files.append(path)
    if not debug_files:
        print('No DWARF sections are present; there is no debug information to optimize.')
        return
    print(f'Optimizing DWARF in {len(debug_files)} ELF files; '
          f'excluding {len(exclusions)} files without DWARF.')
    subprocess.run(['dh_dwz', *exclusions], check=True)


if __name__ == '__main__':
    optimize()
