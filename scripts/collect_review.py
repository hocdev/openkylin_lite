"""Collect exact metadata for the user-approved WPS/AI removal candidates."""
import json
import pathlib
import sys
from check_apps import read_status

root = pathlib.Path(sys.argv[1])
installed = read_status((root / 'var/lib/dpkg/status').read_text())
selected = [line.split('#', 1)[0].strip() for line in
            pathlib.Path('config/remove-packages.txt').read_text().splitlines()]
report = {}
for name in filter(None, selected):
    fields = installed[name]
    info = root / 'var/lib/dpkg/info'
    entries = {}
    for suffix in ('list', 'preinst', 'postinst', 'prerm', 'postrm', 'triggers'):
        paths = list(info.glob(f'{name}.{suffix}')) + list(info.glob(f'{name}:*.{suffix}'))
        entries[suffix] = {p.name: p.read_text(errors='replace') for p in paths}
    report[name] = {'metadata': fields, 'dpkg_info': entries}
pathlib.Path('reports/candidate-metadata.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2))
print(f'Collected {len(report)} candidate packages; no package was removed.')
