"""Reject a rebuilt control center that requires libraries newer than the ISO."""
import json
import pathlib
import re
import subprocess
import sys


def compare_versions(installed, operator, required):
    return subprocess.run(['dpkg', '--compare-versions', installed, operator, required],
                          check=False).returncode == 0


def unsatisfied_dependencies(depends, versions, compare=compare_versions):
    missing = []
    for group in depends.split(','):
        satisfied = False
        for alternative in group.split('|'):
            match = re.fullmatch(r'\s*([a-z0-9+.-]+)(?::[a-z0-9-]+)?'
                                 r'(?:\s*\((<<|<=|=|>=|>>)\s*([^()\s]+)\))?\s*', alternative)
            if not match:
                raise ValueError(f'Unsupported binary dependency: {alternative!r}')
            package, operator, required = match.groups()
            installed = versions.get(package)
            if installed is not None and (operator is None or compare(installed, operator, required)):
                satisfied = True
        if not satisfied:
            missing.append(group.strip())
    return missing


def main():
    deb, baseline = sys.argv[1:]
    versions = json.loads(pathlib.Path(baseline).read_text())['packages']
    for field in ('Pre-Depends', 'Depends'):
        depends = subprocess.check_output(['dpkg-deb', '-f', deb, field], text=True).strip()
        if not depends:
            continue
        missing = unsatisfied_dependencies(depends, versions)
        if missing:
            raise SystemExit('Control center is incompatible with the source ISO: ' + '; '.join(missing))
    print('Control center runtime dependencies match the source ISO.')


if __name__ == '__main__':
    main()
