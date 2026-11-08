"""Apply Lite desktop defaults to a Live root or an unpacked OSTree tree."""
import configparser
from pathlib import Path
import sys
import shutil
import xml.etree.ElementTree as ET


def apply(root):
    root = Path(root)
    # Run after the Live locale hook, and also on the installed system.
    helper = root / 'usr/lib/openkylin-lite/normalize-user-dirs.py'
    helper.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).with_name('normalize_user_dirs.py'), helper)
    shutil.copyfile(Path(__file__).with_name('live_session_guard.py'),
                    helper.with_name('live-session-guard.py'))
    hook = root / 'etc/X11/Xsession.d/46openkylin-lite-user-dirs'
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        'python3 /usr/lib/openkylin-lite/normalize-user-dirs.py || '
        'echo "openKylin Lite: user directory migration failed" >&2\n', encoding='utf-8')
    autostart = root / 'etc/xdg/autostart/openkylin-lite-user-dirs.desktop'
    autostart.parent.mkdir(parents=True, exist_ok=True)
    autostart.write_text(
        '[Desktop Entry]\nType=Application\nName=User directory language\n'
        'Exec=python3 /usr/lib/openkylin-lite/normalize-user-dirs.py\n'
        'NoDisplay=true\n', encoding='utf-8')
    autostart.with_name('openkylin-lite-live-guard.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Live session stability\n'
        'Exec=python3 /usr/lib/openkylin-lite/live-session-guard.py\n'
        'OnlyShowIn=UKUI;\nNoDisplay=true\n', encoding='utf-8')
    # Peony 4.24 automatically plays a same-stem PAG beside a static wallpaper.
    # Remove only animation assets with a verified static fallback.
    for directory in ('usr/share/backgrounds', 'usr/share/wallpapers'):
        for animation in (root / directory).rglob('*.pag'):
            if not any(animation.with_suffix(ext).is_file()
                       for ext in ('.jpg', '.jpeg', '.png', '.webp')):
                raise ValueError(f'Animated wallpaper lacks static fallback: {animation}')
            animation.unlink()

    schemas = root / 'usr/share/glib-2.0/schemas'
    schema_id = 'org.ukui.control-center.personalise'
    keys = {}
    for path in schemas.glob('*.gschema.xml'):
        for schema in ET.parse(path).getroot().findall('schema'):
            if schema.get('id') == schema_id:
                keys = {key.get('name'): key.get('type') for key in schema.findall('key')}
    if any(keys.get(key) != kind for key, kind in
           (('effect', 'b'), ('transparency', 'd'), ('blurry', 'i'))):
        raise ValueError('Unexpected UKUI personalisation schema')
    (schemas / 'zz-openkylin-lite.gschema.override').write_text(
        f'[{schema_id}]\neffect=false\ntransparency=1.0\nblurry=1\n', encoding='utf-8')

    # Keep compositing available for Wayland; disable costly optional effects.
    for directory in ('etc/xdg', 'etc/skel/.config'):
        for name in ('kwinrc', 'ukui-kwinrc'):
            path = root / directory / name
            config = configparser.ConfigParser(interpolation=None, strict=False)
            config.optionxform = str
            if path.exists():
                config.read(path, encoding='utf-8')
            if not config.has_section('Plugins'):
                config.add_section('Plugins')
            for effect in ('blur', 'contrast', 'wobblywindows', 'magiclamp',
                           'kwin4_effect_maximize', 'kwin4_effect_fade',
                           'kwin4_effect_scale', 'slidingpopups', 'slide'):
                config['Plugins'][effect + 'Enabled'] = 'false'
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('w', encoding='utf-8', newline='\n') as stream:
                config.write(stream, space_around_delimiters=False)


if __name__ == '__main__':
    apply(sys.argv[1])
