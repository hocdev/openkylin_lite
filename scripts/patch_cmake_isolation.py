"""Honor and record isolation options in every independent source CMake project."""
import os
from pathlib import Path
import re
import sys


def patch(root):
    helper = root / 'debian/lite-isolation.cmake'
    for path in root.rglob('CMakeLists.txt'):
        if any(part in ('.git', '.pc') for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding='utf-8')
        if 'lite-isolation.cmake' in text:
            continue
        project = re.search(r'(?mi)^[ \t]*project\([^\n]*\)[ \t]*$', text)
        if not project:
            continue
        relative = os.path.relpath(helper, path.parent).replace(os.sep, '/')
        include = '\ninclude("${CMAKE_CURRENT_LIST_DIR}/' + relative + '")\n'
        text = text[:project.end()] + include + text[project.end():]
        path.write_text(text, encoding='utf-8')
        print(f'Applied build isolation compatibility: {path.relative_to(root)}')


if __name__ == '__main__':
    patch(Path(sys.argv[1]).resolve())
