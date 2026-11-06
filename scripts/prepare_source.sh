#!/usr/bin/env bash
set -Eeuo pipefail
source_dir=${ISO_SOURCE_DIR:?ISO_SOURCE_DIR is required}
expected=${SOURCE_SHA256:?SOURCE_SHA256 is required}
[[ $expected =~ ^[[:xdigit:]]{64}$ ]] || exit 1
mkdir -p "$source_dir"
iso=$source_dir/source.iso
valid_source() {
  [[ -f "$iso" ]] && [[ $(stat -c %s "$iso") == 7647188992 ]] &&
    echo "$expected  $iso" | sha256sum -c -
}
if valid_source; then
  echo 'Reusing verified original ISO; no upstream download.'
  exit 0
fi
url=https://releases.openkylin.top/3.0/openKylin-Desktop-V3.0-20260918-x86_64.iso
rm -f -- "$iso" "$source_dir/source.iso.aria2"
if command -v aria2c >/dev/null; then
  aria2c --max-connection-per-server=8 --split=8 --min-split-size=4M --max-tries=5 --timeout=60 --file-allocation=none --summary-interval=60 --console-log-level=warn --dir="$source_dir" --out=source.iso "$url"
else
  curl --fail --location --retry 5 --connect-timeout 30 --max-time 3600 "$url" -o "$iso"
fi
valid_source
