#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'
export LANG=C.UTF-8 LC_ALL=C.UTF-8
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates curl git build-essential devscripts python3 xz-utils
curl -fL --retry 4 --retry-delay 5 \
  -o "$work/source.tar.xz" \
  https://archive.build.openkylin.top/openkylin/pool/main/u/ukui-control-center/ukui-control-center_4.24.0.0-ok2.8.tar.xz
echo "6810d2ec5f4b186b6473206566270c5537605f1adc912b5a7199a91b2f0ed508  $work/source.tar.xz" | sha256sum -c -
mkdir "$work/source"
tar -xJf "$work/source.tar.xz" --strip-components=1 -C "$work/source"
cd "$work/source"
dpkg-source --before-build .
git apply --check "$workspace/patches/control-center/about-network.patch"
git apply "$workspace/patches/control-center/about-network.patch"
cp "$workspace/patches/control-center/ntpdateprovider.h" registeredSession/plugins/about/
dch --local +lite --distribution huanghe 'Keep About network date lookups off the D-Bus event loop.'
apt-get build-dep -y --no-install-recommends ./
mkdir "$work/network-test"
(
  cd "$work/network-test"
  qmake "$workspace/tests/qt/about-network.pro"
  make -j2
  ./test-about-network
)
CMAKE_POLICY_VERSION_MINIMUM=3.5 dpkg-buildpackage -b -uc -us
deb=( "$work/ukui-control-center_"*_amd64.deb )
[[ ${#deb[@]} == 1 && -f ${deb[0]} ]]
dpkg-deb -x "${deb[0]}" "$work/verify"
find "$work/verify" -name '*ukccSession*.so' -print -quit | grep -q .
mkdir -p "$workspace/control-center-output"
cp -- "${deb[0]}" "$workspace/control-center-output/"
