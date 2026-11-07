"""Verify that public Gitee build tags still resolve to the locked commits."""
import concurrent.futures
import json
import os
import pathlib
import subprocess
import time


def verify(entry):
    tag = 'refs/tags/' + entry['tag']
    command = ['git', '-c', 'credential.helper=', '-c', 'http.lowSpeedLimit=1000',
               '-c', 'http.lowSpeedTime=30', 'ls-remote', '--exit-code', '--tags',
               entry['repository'], tag, tag + '^{}']
    result = {'source': entry['source'], 'version': entry['version'],
              'tag': entry['tag'], 'expected_commit': entry['commit']}
    try:
        for attempt in range(4):
            try:
                output = subprocess.check_output(command, text=True, stderr=subprocess.PIPE,
                                                 timeout=90,
                                                 env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        refs = dict(line.split()[::-1] for line in output.splitlines())
        actual = refs.get(tag + '^{}', refs.get(tag))
        result.update(actual_commit=actual, passed=actual == entry['commit'])
    except (subprocess.SubprocessError, OSError) as error:
        result.update(passed=False, error=str(error))
    return result


def main():
    entries = json.loads(pathlib.Path('config/rebuild-sources.json').read_text())['packages']
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(verify, entries))
    pathlib.Path('reports').mkdir(exist_ok=True)
    pathlib.Path('reports/source-tag-verification.json').write_text(json.dumps(results, indent=2) + '\n')
    for result in results:
        print(('PASS' if result['passed'] else 'FAIL'), result['source'], result['version'], flush=True)
    if not all(item['passed'] for item in results):
        raise SystemExit('One or more Gitee source tags could not be verified; see report.')
    print('Source tags verified. Patched builds and runtime compatibility remain unverified.')


if __name__ == '__main__':
    main()
