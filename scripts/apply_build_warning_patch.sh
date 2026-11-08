#!/usr/bin/env bash
set -Eeuo pipefail
source_package=${1:?source package is required}
workspace=${2:?workspace is required}
[[ $source_package =~ ^[a-z0-9.+-]+$ ]] || exit 2
patch="$workspace/patches/build-warnings/$source_package.patch"
if [[ -f $patch ]]; then
  git apply --check "$patch"
  git apply "$patch"
fi
if [[ $source_package == ukui-search ]]; then
  cp "$workspace/patches/build-warnings/cache-write.h" libchinese-segmentation/cache-write.h
fi
