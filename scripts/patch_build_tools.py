"""Repair compatibility in build-container metadata without changing ISO libraries."""
from pathlib import Path
import re
import sys


def qt_future_constructors(text):
    return re.sub(r'(?m)^([ \t]*(?:explicit[ \t]+)?)QFutureInterface<(?:T|void)>[ \t]*\(',
                  r'\1QFutureInterface(', text)


def qch_target_properties(text):
    # Generated KF5 documentation targets are custom targets, not imported libraries.
    # IMPORTED is read-only; assigning it was ignored by old CMake and now warns/errors.
    if not re.search(r'\badd_custom_target\s*\(', text):
        return text
    return re.sub(r'(?m)^[ \t]*IMPORTED[ \t]+TRUE[ \t]*\n', '', text)


def changelog_options(text):
    return re.sub(r'(\bchangelog_parse\(\s*\{?\s*)file(\s*=>)',
                  r'\1filename\2', text)


def patch(root):
    count = 0
    paths = [(path, qt_future_constructors) for path in
             root.glob('usr/include/*/qt5/QtCore/qfutureinterface.h')]
    paths += [(path, qch_target_properties) for path in
              root.glob('usr/lib/*/cmake/KF5*/*QchTargets.cmake')]
    dch = root / 'usr/bin/dch'
    if dch.is_file():
        paths.append((dch, changelog_options))
    for path, transform in paths:
        text = path.read_text(encoding='utf-8')
        updated = transform(text)
        if updated == text:
            continue
        path.write_text(updated, encoding='utf-8')
        print(f'Updated build-tool compatibility: {path}')
        count += 1
    print(f'Build-container metadata/header fixes: {count}; no ELF payload changed.')


if __name__ == '__main__':
    patch(Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/'))
