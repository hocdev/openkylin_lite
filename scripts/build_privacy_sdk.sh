#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
export DEBFULLNAME='openKylin Lite' DEBEMAIL='openkylin-lite@users.noreply.github.com'
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
apt-get install -y --no-install-recommends build-essential cmake debhelper devscripts pkgconf curl python3
base=https://archive.build.openkylin.top/openkylin/pool/main/libk/libkysdk-diagnosetest
curl -fL --retry 4 -o "$work/orig.tar.gz" "$base/libkysdk-diagnosetest_3.0.1.0.orig.tar.gz"
curl -fL --retry 4 -o "$work/debian.tar.xz" "$base/libkysdk-diagnosetest_3.0.1.0-0k0.1update1.debian.tar.xz"
echo "df32695ccd9d91b3fc509653a6c8ffee4c60902231c71efb048181a94a107a0b  $work/orig.tar.gz" | sha256sum -c -
echo "f56cfa4191c37ebb4bf3ad9cb976d94812779d7c11ad9526ca5656827c8c00e3  $work/debian.tar.xz" | sha256sum -c -
mkdir "$work/source"
tar -xzf "$work/orig.tar.gz" --strip-components=1 -C "$work/source"
tar -xJf "$work/debian.tar.xz" -C "$work/source"
cd "$work/source"
dpkg-source --before-build .
# Match the ISO's actual SDK header, including registerNumber added by Debian.
python3 - "$workspace/patches/privacy/libkydatacollect.h" <<'PY'
from pathlib import Path
import sys
if Path('kysdk-datacollect/src/libkydatacollect.h').read_text() != Path(sys.argv[1]).read_text():
    raise SystemExit('SDK header differs from the reviewed ABI')
PY
cp "$workspace/patches/privacy/datacollect-disabled.c" kysdk-datacollect/src/libkydatacollect.c
cat > CMakeLists.txt <<'CMAKE'
cmake_minimum_required(VERSION 3.16)
project(kysdk-diagnosetest C)
include(GNUInstallDirs)
add_library(kysdk-datacollect SHARED kysdk-datacollect/src/libkydatacollect.c)
set_target_properties(kysdk-datacollect PROPERTIES VERSION 3.0.0 SOVERSION 1)
install(TARGETS kysdk-datacollect LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES kysdk-datacollect/src/libkydatacollect.h DESTINATION include/kysdk/diagnosetest)
CMAKE
# Remove build dependencies for the implementation that is no longer compiled.
python3 - <<'PY'
from pathlib import Path
import re
p = Path('debian/control')
p.write_text(re.sub(r'Build-Depends:.*?\nStandards-Version:',
    'Build-Depends: debhelper, pkgconf, cmake, libc6-dev\nStandards-Version:',
    p.read_text(), count=1, flags=re.S))
PY
dch --local +lite --distribution huanghe 'Replace telemetry with an inert ABI compatibility implementation.'
cc -Wall -Wextra -Werror -I kysdk-datacollect/src \
  -I "$workspace/patches/privacy" "$workspace/tests/privacy_sdk.c" \
  kysdk-datacollect/src/libkydatacollect.c "$workspace/patches/privacy/diagnostics-disabled.c" -o "$work/test-sdk"
"$work/test-sdk"
dpkg-buildpackage -b -uc -us
deb=( "$work/libkysdk-datacollect_"*_amd64.deb )
[[ ${#deb[@]} == 1 ]]
dpkg-deb -x "${deb[0]}" "$work/verify"
library=$(find "$work/verify" -type f -name 'libkysdk-datacollect.so.*')
[[ -n $library ]]
# A dormant SDK must have no D-Bus, HTTP, crypto, logging or identity dependencies.
readelf -d "$library" > "$work/dynamic.txt"
grep -q 'Library soname: \[libkysdk-datacollect.so.1\]' "$work/dynamic.txt"
if grep NEEDED "$work/dynamic.txt" | grep -v 'Shared library: \[libc.so.6\]'; then
  echo 'Unexpected dependency in disabled telemetry SDK'; exit 1
fi
nm -D --defined-only "$library" | awk '{print $3}' | sort > "$work/exports"
python3 - "$workspace/patches/privacy/libkydatacollect.h" "$work/exports" <<'PY'
from pathlib import Path
import re, sys
expected = set(re.findall(r'\b(kdk_dia_\w+)\(', Path(sys.argv[1]).read_text()))
actual = set(Path(sys.argv[2]).read_text().splitlines())
if actual != expected:
    raise SystemExit(f'SDK public ABI mismatch: missing={expected-actual}, extra={actual-expected}')
PY
mkdir -p "$workspace/control-center-output"
cc -shared -fPIC -Wall -Wextra -Werror -Wl,-soname,libkydiagnostics.so.1 \
  "$workspace/patches/privacy/diagnostics-disabled.c" \
  -o "$workspace/control-center-output/legacy-diagnostics-disabled.so"
for package in libkysdk-datacollect libkysdk-datacollect-dev libkysdk-diagnosetest libkysdk-diagnosetest-dev libkysdk-diagnosetest-doc; do
  deb=( "$work/${package}_"*.deb )
  [[ ${#deb[@]} == 1 && -f ${deb[0]} ]]
  cp "${deb[0]}" "$workspace/control-center-output/"
done
