"""Validate exact AI-free binary outputs and dependencies before remastering."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from ai_policy import CONFIG, REBUILT, ADDITIONS
from check_ai_free import check_packages, check_payload
from check_control_center_dependencies import unsatisfied_dependencies


def field(deb, name):
    return subprocess.check_output(['dpkg-deb', '-f', str(deb), name], text=True).strip()


def check(directory, source):
    expected = set(CONFIG['sources'][source]['binaries'])
    if source == 'orca':
        expected |= ADDITIONS
    found = {}
    versions = json.loads((Path(__file__).resolve().parents[1] / 'config/iso-runtime-versions.json').read_text())['packages']
    versions.update({name: version + '+liteai1' for name, version in REBUILT.items()})
    for deb in directory.glob('*.deb'):
        name = field(deb, 'Package')
        if name not in expected or name in found:
            raise ValueError(f'Unexpected/duplicate candidate: {name}')
        version = field(deb, 'Version')
        if name in REBUILT and version != REBUILT[name] + '+liteai1':
            raise ValueError(f'Wrong candidate version: {name} {version}')
        found[name] = deb
        versions[name] = version
    if set(found) != expected:
        raise ValueError(f'Missing candidates: {expected - set(found)}')
    report = {}
    for name, deb in found.items():
        metadata = {key: field(deb, key) for key in
                    ('Version', 'Depends', 'Pre-Depends', 'Recommends', 'Suggests')}
        check_packages({name: metadata})
        for key in ('Depends', 'Pre-Depends'):
            if metadata[key]:
                missing = unsatisfied_dependencies(metadata[key], versions)
                if missing:
                    raise ValueError(f'{name} is incompatible with source ISO: {missing}')
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(['dpkg-deb', '-x', str(deb), temporary], check=True)
            check_payload(Path(temporary))
        report[name] = metadata
    (directory / 'candidate-audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Validated {len(found)} {source} candidates.')


if __name__ == '__main__':
    check(Path(sys.argv[1]), sys.argv[2])
