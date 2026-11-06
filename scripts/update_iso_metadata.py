"""Update Casper package metadata and checksums without dropping install rules."""
import hashlib
import pathlib
import re
import sys


def filter_remove_manifest(text, removed):
    return ''.join(line for line in text.splitlines(keepends=True)
                   if not line.strip() or line.lstrip().startswith('#')
                   or line.split()[0] not in removed)


def update_checksums(text, updates, algorithm):
    result = []
    for line in text.splitlines():
        if not line.strip():
            result.append(line)
            continue
        digest, path = line.split(maxsplit=1)
        key = path.lstrip('*')
        key = key[2:] if key.startswith('./') else key
        if key in updates:
            with updates[key].open('rb') as stream:
                digest = hashlib.file_digest(stream, algorithm).hexdigest()
        result.append(f'{digest}  {path}')
    return '\n'.join(result) + '\n'


def configure_live_boot(iso, meta):
    updates = {}
    for relative in ('boot/grub/grub.cfg', 'isolinux/isolinux.cfg',
                     'isolinux/txt.cfg', 'isolinux/lang'):
        source = iso / relative
        text = source.read_text(encoding='utf-8')
        if relative == 'isolinux/lang':
            text = 'en\n'
        elif relative == 'boot/grub/grub.cfg':
            text = re.sub(r'^set timeout=\d+$', 'set timeout=2', text, flags=re.M)
            text = text.replace('locale=zh_CN', 'locale=en_US.UTF-8')
        elif relative == 'isolinux/isolinux.cfg':
            text = re.sub(r'^timeout \d+$', 'timeout 20', text, flags=re.M)
        else:
            text = re.sub(r'(^\s*append\s+boot=casper\b)',
                          r'\1 locale=en_US.UTF-8', text, flags=re.M)
        destination = meta / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding='utf-8')
        updates[relative] = destination
    return updates


def main():
    iso, meta = map(pathlib.Path, sys.argv[1:3])
    relative, squash, removed_file = sys.argv[3:]
    parent = pathlib.PurePosixPath(relative).parent
    updates = {relative: pathlib.Path(squash)}
    updates.update(configure_live_boot(iso, meta))
    known = {'filesystem.manifest', 'filesystem.manifest-remove'}
    unknown = [p for p in iso.rglob('filesystem.manifest*') if p.name not in known]
    if unknown:
        raise ValueError(f'Unsupported installer manifests: {unknown}')
    for name in ('filesystem.manifest', 'filesystem.size'):
        path = str(parent / name)
        if (iso / path).is_file():
            updates[path] = meta / name
    remove_path = str(parent / 'filesystem.manifest-remove')
    if (iso / remove_path).is_file():
        removed = set(pathlib.Path(removed_file).read_text().splitlines())
        (meta / 'filesystem.manifest-remove').write_text(
            filter_remove_manifest((iso / remove_path).read_text(), removed))
        updates[remove_path] = meta / 'filesystem.manifest-remove'
    # Common ISO checksum lists; generate after all changed payloads are ready.
    for name, algorithm in (('md5sum.txt', 'md5'), ('SHA256SUMS', 'sha256')):
        if (iso / name).is_file():
            (meta / name).write_text(update_checksums((iso / name).read_text(), updates, algorithm))
            updates[name] = meta / name
    # NUL-delimited pairs let Bash pass paths to xorriso without shell parsing.
    for path, local in updates.items():
        sys.stdout.buffer.write(str(local).encode() + b'\0' + ('/' + path).encode() + b'\0')


if __name__ == '__main__':
    main()
