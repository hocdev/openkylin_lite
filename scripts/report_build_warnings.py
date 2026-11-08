"""Inventory diagnostics without suppressing them or changing build success."""
import collections
import json
from pathlib import Path
import re
import sys


DIAGNOSTIC = re.compile(r'\bwarning:|\bWARNING:|\bWarning:|^CMake (?:Deprecation )?Warning\b')


def collect(text):
    counts = collections.Counter()
    for line in text.splitlines():
        # Tool invocations can contain options such as --warning, but are not diagnostics.
        if not DIAGNOSTIC.search(line):
            continue
        normalized = re.sub(r'/tmp/tmp\.[^/\s]+/source/', '<source>/', line.strip())
        counts[normalized] += 1
    return [{'message': message, 'occurrences': count}
            for message, count in sorted(counts.items())]


def report(log, status):
    diagnostics = collect(log.read_text(encoding='utf-8', errors='replace'))
    result = {'exit_code': status, 'unique_diagnostics': len(diagnostics),
              'diagnostics': diagnostics}
    log.with_name('warnings.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Build exit: {status}; unique warning diagnostics: {len(diagnostics)}. '
          'Full context is retained in build.log.')


if __name__ == '__main__':
    report(Path(sys.argv[1]), int(sys.argv[2]))
