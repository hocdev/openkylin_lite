#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'
export LANG=C.UTF-8 LC_ALL=C.UTF-8
workspace=$PWD
bash "$workspace/scripts/prepare_build_environment.sh"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates curl git build-essential devscripts python3 xz-utils
bash scripts/build_default_settings_candidate.sh
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
git apply --check "$workspace/patches/control-center/about-startup.patch"
git apply "$workspace/patches/control-center/about-startup.patch"
git apply --check "$workspace/patches/control-center/privacy.patch"
git apply "$workspace/patches/control-center/privacy.patch"
git apply --check "$workspace/patches/control-center/shell-startup.patch"
git apply "$workspace/patches/control-center/shell-startup.patch"
git apply --check "$workspace/patches/control-center/no-activation.patch"
git apply "$workspace/patches/control-center/no-activation.patch"
bash "$workspace/scripts/apply_build_warning_patch.sh" ukui-control-center "$workspace"
cp "$workspace/patches/control-center/ntpdateprovider.h" registeredSession/plugins/about/
cp "$workspace/patches/control-center/aboutasync.h" plugins/system/about/
cp "$workspace/patches/control-center/aboutasync.h" shell/
cp "$workspace/patches/control-center/securitypathprovider.h" registeredSession/
if grep -R -n -E '(^|[[:space:]])kysdk-datacollect([[:space:]\\]|$)' \
    --include='*.pro' --include='*.pri' .; then
  echo 'Stale telemetry SDK link in a qmake project/include file'; exit 1
fi
dch --local +lite --distribution huanghe 'Keep Settings startup and policy lookups off the GUI event loop.'
# Match the SDK to the original ISO, rather than the moving archive's latest
# version. Otherwise shlibdeps raises the runtime minimum beyond the Live root.
mkdir "$work/build-deps"
while read -r digest file; do
  [[ $digest =~ ^[0-9a-f]{64}$ && $file == libukui-quick-*_4.25.0.0-ok0.2_amd64.deb ]]
  curl -fL --retry 4 --retry-delay 5 -o "$work/build-deps/$file" \
    "https://archive.build.openkylin.top/openkylin/pool/main/u/ukui-quick/$file"
  echo "$digest  $work/build-deps/$file" | sha256sum -c -
done < "$workspace/config/control-center-build-deps.sha256"
cat > /etc/apt/preferences.d/openkylin-lite-quick <<'PIN'
Package: libukui-quick-core1 libukui-quick-dev libukui-quick-framework1 libukui-quick-platform1
Pin: version 4.25.0.0-ok0.2
Pin-Priority: 1001
PIN
apt-get install -y --allow-downgrades --no-install-recommends "$work/build-deps/"*.deb
apt-get build-dep -y --no-install-recommends ./
for package in libukui-quick-core1 libukui-quick-dev libukui-quick-framework1 libukui-quick-platform1; do
  [[ $(dpkg-query -W '-f=${Version}' "$package") == 4.25.0.0-ok0.2 ]]
done
mkdir "$work/network-test"
(
  cd "$work/network-test"
  qmake "$workspace/tests/qt/about-network.pro"
  make -j2
  ./test-about-network
)
mkdir "$work/startup-test"
(
  cd "$work/startup-test"
  qmake "$workspace/tests/qt/about-startup.pro"
  make -j2
  dbus-run-session -- ./test-about-startup
)
mkdir "$work/security-path-test"
(
  cd "$work/security-path-test"
  qmake "$workspace/tests/qt/security-path.pro"
  make -j2
  dbus-run-session -- ./test-security-path
)
CMAKE_POLICY_VERSION_MINIMUM=3.5 dpkg-buildpackage -b -uc -us
deb=( "$work/ukui-control-center_"*_amd64.deb )
[[ ${#deb[@]} == 1 && -f ${deb[0]} ]]
# Validate generated dependency constraints against the ISO's runtime versions.
python3 "$workspace/scripts/check_control_center_dependencies.py" "${deb[0]}" \
  "$workspace/config/control-center-runtime-versions.json"
dpkg-deb -x "${deb[0]}" "$work/verify"
find "$work/verify" -name '*ukccSession*.so' -print -quit | grep -q .
mkdir -p "$workspace/control-center-output"
cp -- "${deb[0]}" "$workspace/control-center-output/"
library_deb=( "$work/libukcc3_"*_amd64.deb )
[[ ${#library_deb[@]} == 1 && -f ${library_deb[0]} ]]
python3 "$workspace/scripts/check_control_center_dependencies.py" "${library_deb[0]}" \
  "$workspace/config/control-center-runtime-versions.json"
cp -- "${library_deb[0]}" "$workspace/control-center-output/"
cd "$workspace"
bash scripts/build_privacy_sdk.sh
