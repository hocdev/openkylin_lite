"""Migrate vendor Chinese XDG folders for English sessions without overwrites."""
import os
from pathlib import Path
import re

DIRECTORIES = (
    ('DESKTOP', '桌面', 'Desktop'), ('DOWNLOAD', '下载', 'Downloads'),
    ('TEMPLATES', '模板', 'Templates'), ('PUBLICSHARE', '公共', 'Public'),
    ('DOCUMENTS', '文档', 'Documents'), ('MUSIC', '音乐', 'Music'),
    ('PICTURES', '图片', 'Pictures'), ('VIDEOS', '视频', 'Videos'),
)


def merge_directory(source, target):
    if source.is_symlink() or target.is_symlink() or not source.is_dir():
        return
    if target.exists() and not target.is_dir():
        return
    target.mkdir(exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if not destination.exists() and not destination.is_symlink():
            child.rename(destination)
        elif child.is_dir() and not child.is_symlink():
            merge_directory(child, destination)
    # Conflicting files stay in their original directory; never overwrite them.
    if not any(source.iterdir()):
        source.rmdir()


def normalize(home, locale, config_home=None):
    if not locale.lower().startswith(('en_', 'en.')) and locale.lower() != 'en':
        return
    home = Path(home)
    config = Path(config_home) if config_home else home / '.config'
    path = config / 'user-dirs.dirs'
    if config.is_symlink() or path.is_symlink():
        return
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    for key, chinese, english in DIRECTORIES:
        pattern = rf'^XDG_{key}_DIR="([^"]*)"$'
        match = re.search(pattern, text, re.MULTILINE)
        # Preserve custom paths, including a deliberately disabled XDG folder.
        if match and match[1] not in (f'$HOME/{chinese}', f'$HOME/{english}',
                                     str(home / chinese), str(home / english)):
            continue
        target = home / english
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            continue
        merge_directory(home / chinese, target)
        target.mkdir(exist_ok=True)
        setting = f'XDG_{key}_DIR="$HOME/{english}"'
        if match:
            text = text[:match.start()] + setting + text[match.end():]
        else:
            text = text.rstrip('\n') + '\n' + setting + '\n'
    config.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    locale = os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', '')
    normalize(Path.home(), locale, os.environ.get('XDG_CONFIG_HOME') or None)
