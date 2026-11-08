"""Live-only idle policy and bounded recovery for an exited UKUI panel."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import time


def run(*args):
    return subprocess.run(args, text=True, capture_output=True, timeout=10)


def configure():
    settings = {
        'org.ukui.panel.settings': {'hidepanel': 'false'},
        'org.ukui.screensaver': {'idle-activation-enabled': 'false', 'idle-lock-enabled': 'false'},
        'org.ukui.power-manager': {
            **{f'sleep-{target}-{power}': '0'
               for target in ('computer', 'display') for power in ('ac', 'battery', 'ups')},
            'idle-dim-ac': 'false', 'idle-dim-battery': 'false',
        },
    }
    for schema, values in settings.items():
        keys = run('gsettings', 'list-keys', schema)
        if keys.returncode:
            logging.warning('Cannot read schema %s: %s', schema, keys.stderr.strip())
            continue
        for key, value in values.items():
            if key not in keys.stdout.split():
                logging.warning('Missing Live setting %s %s', schema, key)
                continue
            result = run('gsettings', 'set', schema, key, value)
            if result.returncode:
                logging.warning('Cannot set %s %s: %s', schema, key, result.stderr.strip())
    if os.environ.get('DISPLAY') and os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        run('xset', 's', 'off')
        if 'DPMS is' in run('xset', 'q').stdout:
            run('xset', '-dpms')


def running(name):
    result = run('pgrep', '-u', str(os.getuid()), '-x', name)
    if result.returncode not in (0, 1):
        raise RuntimeError(f'Cannot query {name}: {result.stderr}')
    return result.returncode == 0


def watch_panel():
    recoveries = 0
    missing = 0
    # Let the session manager perform normal startup and its own recovery first.
    time.sleep(30)
    while running('ukui-session'):
        if running('ukui-panel'):
            missing = 0
        else:
            missing += 1
            if missing >= 3:
                logging.warning('Panel absent for 30 seconds; recovery %d/3', recoveries + 1)
                journal = run('journalctl', '--user', '-b', '-n', '60', '--no-pager')
                logging.warning('Session journal:\n%s', journal.stdout[-16000:])
                # Recheck after collecting diagnostics to avoid racing native recovery.
                if not running('ukui-session'):
                    return
                if not running('ukui-panel'):
                    subprocess.Popen(['ukui-panel'], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                    recoveries += 1
                missing = 0
                if recoveries >= 3:
                    logging.error('Recovery limit reached; stopping guard')
                    return
        time.sleep(10)


def main():
    if 'boot=casper' not in Path('/proc/cmdline').read_text().split():
        return
    import fcntl
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    with (runtime / 'openkylin-lite-live-guard.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        state = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'openkylin-lite'
        state.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                            handlers=[RotatingFileHandler(state / 'live-session.log', maxBytes=262144, backupCount=1)])
        logging.info('Applying Live idle policy')
        configure()
        watch_panel()


if __name__ == '__main__':
    main()
