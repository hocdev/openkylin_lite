"""Add only installed, explicitly reviewed telemetry/SSO packages to the purge."""
import json
from pathlib import Path
import sys
from check_apps import PRIVACY_COMPONENTS, read_status
from ai_policy import REMOVALS


def prepare(root, list_file, review_file, output):
    installed = read_status((root / 'var/lib/dpkg/status').read_text())
    selected = [line.split('#', 1)[0].strip() for line in list_file.read_text().splitlines()]
    selected = list(filter(None, selected))
    reviews = json.loads(review_file.read_text())
    for name, review in REMOVALS.items():
        if name not in installed:
            continue
        if (installed[name]['Version'], installed[name]['Section']) != (review['version'], review['section']):
            raise ValueError(f'{name}: AI removal metadata differs from the pinned ISO inventory')
        selected.append(name)
        reviews[name] = review
    for name, (version, section) in PRIVACY_COMPONENTS.items():
        if name not in installed:
            continue
        if (installed[name]['Version'], installed[name]['Section']) != (version, section):
            raise ValueError(f'{name}: unreviewed version or section; inspect the ISO package first')
        selected.append(name)
        reviews[name] = {'version': version, 'section': section, 'kind': 'privacy-component',
                         'reason': 'User-requested complete removal of telemetry and cloud SSO'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'remove-packages.txt').write_text('\n'.join(dict.fromkeys(selected)) + '\n')
    (output / 'reviewed-apps.json').write_text(json.dumps(reviews, indent=2) + '\n')


if __name__ == '__main__':
    prepare(*map(Path, sys.argv[1:]))
