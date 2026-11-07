"""Drop the reviewed telemetry dependency from the original defaults source."""
from pathlib import Path
import sys


def patch_control(text):
    if not text.startswith('Source: openkylin-default-settings\n'):
        raise ValueError('Unexpected defaults source package')
    expected = '         kylin-daq,\n'
    if text.count(expected) != 1:
        raise ValueError('Expected exactly one reviewed kylin-daq dependency')
    result = text.replace(expected, '', 1)
    if 'kylin-daq' in result:
        raise ValueError('Additional telemetry reference in defaults control')
    return result


if __name__ == '__main__':
    path = Path(sys.argv[1])
    path.write_text(patch_control(path.read_text(encoding='utf-8')), encoding='utf-8')
