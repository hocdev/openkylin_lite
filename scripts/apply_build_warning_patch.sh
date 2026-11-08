#!/usr/bin/env bash
set -Eeuo pipefail
source_package=${1:?source package is required}
workspace=${2:?workspace is required}
[[ $source_package =~ ^[a-z0-9.+-]+$ ]] || exit 2
patch="$workspace/patches/build-warnings/$source_package.patch"
if [[ -f $patch ]]; then
  git apply --check --ignore-space-change "$patch"
  git apply --ignore-space-change "$patch"
fi
if [[ $source_package == ukui-search ]]; then
  cp "$workspace/patches/build-warnings/cache-write.h" libchinese-segmentation/cache-write.h
fi
# Do not send stripped release binaries to a tool that optimizes debug information.
# Keep optimization enabled for any genuine DWARF input and retain all tool errors.
if grep -Eq '^override_dh_dwz([:-]|$)' debian/rules; then
  echo 'An existing DWARF optimization override needs review'
  exit 1
fi
cp "$workspace/scripts/run_dwz_for_debug.py" debian/lite-dwz.py
cp "$workspace/patches/build-warnings/isolation.cmake" debian/lite-isolation.cmake
python3 "$workspace/scripts/patch_cmake_isolation.py" "$PWD"
cat >> debian/rules <<'RULES'

override_dh_dwz:
	python3 debian/lite-dwz.py
RULES
