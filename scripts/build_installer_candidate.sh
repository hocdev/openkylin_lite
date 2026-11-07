#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'

PACKAGE=${PACKAGE:-kylin-os-installer}
SOURCE_PACKAGE=${SOURCE_PACKAGE:-$PACKAGE}
SOURCE_TAG=${SOURCE_TAG:-build/0.2.2-0k1.16}
SOURCE_COMMIT=${SOURCE_COMMIT:-15008beb5f39ccf33f920e03e6bcef24c2826b22}
SOURCE_TARBALL_URL=${SOURCE_TARBALL_URL:-http://archive.build.openkylin.top/openkylin/pool/main/k/kylin-os-installer/kylin-os-installer_0.2.2-0k1.16.tar.xz}
SOURCE_TARBALL_SHA256=${SOURCE_TARBALL_SHA256:-189349021171f31d19539d41bed9955288104427ce35474beddb0a42cbac0042}

workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends \
  ca-certificates curl git build-essential devscripts python3 qttools5-dev-tools xz-utils

git init "$work/source"
cd "$work/source"
fetched=0
for attempt in 1 2 3 4; do
  if git -c http.postBuffer=524288000 -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=120 \
    fetch --depth=1 "https://gitee.com/openkylin/$SOURCE_PACKAGE.git" "refs/tags/$SOURCE_TAG"; then
    fetched=1
    break
  fi
  sleep "$((attempt * 5))"
done

if (( fetched == 1 )); then
  git checkout --detach FETCH_HEAD
  [[ $(git rev-parse HEAD) == "$SOURCE_COMMIT" ]]
else
  echo "Gitee fetch failed after four attempts; falling back to SHA256-pinned archive tarball"
  curl -fL --retry 4 --retry-delay 5 -o "$work/source.tar.xz" "$SOURCE_TARBALL_URL"
  echo "$SOURCE_TARBALL_SHA256  $work/source.tar.xz" | sha256sum -c -
  tar -xJf "$work/source.tar.xz" --strip-components=1 -C "$work/source"
fi

dpkg-source --before-build .
git apply --check "$workspace/patches/installer/kylin-os-installer.patch"
git apply "$workspace/patches/installer/kylin-os-installer.patch"

python3 - <<'PYTHON'
import pathlib
import shutil
import subprocess
import xml.etree.ElementTree as ET

lang_dir = pathlib.Path('language')
for ts_file in sorted(lang_dir.glob('*.ts')):
    tree = ET.parse(ts_file)
    root = tree.getroot()
    changed = False
    for msg in root.iter('message'):
        src_el = msg.find('source')
        trn_el = msg.find('translation')
        if src_el is None or not src_el.text:
            continue
        src = src_el.text
        if src.startswith(('Please choose custom way to install, disk size less than 50G',
                           'Disk must be greater than 50G')):
            src_el.text = src.replace('50', '30')
            if trn_el is not None and trn_el.text:
                trn_el.text = trn_el.text.replace('50', '30')
            changed = True
        elif src.startswith('Root partition size is greater than 40G'):
            src_el.text = src.replace('40', '20').replace('50', '30')
            if trn_el is not None and trn_el.text:
                trn_el.text = trn_el.text.replace('40', '20').replace('50', '30')
            changed = True
    if changed:
        content = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + ET.tostring(root, encoding='unicode') + '\n'
        ts_file.write_text(content, encoding='utf-8')

lrelease = None
for candidate in (
    '/usr/lib/qt5/bin/lrelease',
    '/usr/lib/x86_64-linux-gnu/qt5/bin/lrelease',
    shutil.which('lrelease'),
):
    if candidate and pathlib.Path(candidate).is_file():
        lrelease = candidate
        break
if not lrelease:
    raise SystemExit('Could not locate Qt5 lrelease binary')

skip_prefixes = ('qt_', 'assistant_', 'designer_', 'linguist_', 'transmission_')
for qm_file in sorted(lang_dir.glob('*.qm')):
    if qm_file.name.startswith(skip_prefixes):
        continue
    stem = qm_file.stem
    lang = stem.split('_')[0]
    ts_candidate = lang_dir / f'{stem}.ts'
    if not ts_candidate.is_file():
        ts_candidate = lang_dir / f'{lang}.ts'
    if not ts_candidate.is_file():
        raise SystemExit(f'Missing TS source for {qm_file}')
    subprocess.check_call([lrelease, str(ts_candidate), '-qm', str(qm_file)])
PYTHON

dch --local +lite --distribution huanghe 'Lower minimum installation disk size from 50 GB to 30 GB.'
apt-get build-dep -y --no-install-recommends ./
dpkg-buildpackage -b -uc -us

deb=( "$work/${PACKAGE}_"*_amd64.deb )
[[ ${#deb[@]} == 1 && -f ${deb[0]} ]]

dpkg-deb -x "${deb[0]}" "$work/verify"
test -x "$work/verify/usr/bin/kylin-os-installer"
shopt -s nullglob
kpart_libs=( "$work/verify"/usr/lib/libKPartition.so* )
(( ${#kpart_libs[@]} > 0 )) || { echo 'Missing libKPartition.so in built package'; exit 1; }
if grep -Fq 'disk size less than 50G!' "${kpart_libs[@]}"; then
  echo 'Old 50G limit string remains in libKPartition.so'
  exit 1
fi
grep -Fq 'disk size less than 30G!' "${kpart_libs[@]}"
if grep -Fq '40960' "$work/verify/usr/share/kylin-os-installer/data/systemdatasize.sh"; then
  echo 'Old 40960 MiB root minimum remains in systemdatasize.sh'
  exit 1
fi
grep -Fq '20480' "$work/verify/usr/share/kylin-os-installer/data/systemdatasize.sh"
grep -Fq '20480' "$work/verify/usr/share/kylin-os-installer/scripts/autopart-efi.sh"

mkdir -p "$workspace/installer-output"
cp -- "${deb[0]}" "$workspace/installer-output/"
dpkg-deb -I "${deb[0]}"
