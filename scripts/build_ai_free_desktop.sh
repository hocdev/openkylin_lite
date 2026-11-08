#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
export DEBFULLNAME='openKylin Lite' DEBEMAIL='openkylin-lite@users.noreply.github.com'
export DEB_BUILD_OPTIONS=parallel=2
workspace=$PWD
export CMAKE_POLICY_VERSION_MINIMUM=3.10
bash "$workspace/scripts/prepare_build_environment.sh"
source_package=${SOURCE_PACKAGE:?SOURCE_PACKAGE is required}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates git build-essential devscripts libdistro-info-perl python3 curl binutils
mapfile -t lock < <(python3 - "$source_package" <<'PY'
import json, sys
policy = json.load(open('config/ai-free-desktop.json'))
assert sys.argv[1] in policy['sources']
entry = next(p for p in json.load(open('config/rebuild-sources.json'))['packages'] if p['source'] == sys.argv[1])
print(entry['repository']); print(entry['tag']); print(entry['commit']); print(entry['version'])
PY
)
[[ ${#lock[@]} == 4 ]]
git init --initial-branch=upstream "$work/source"
cd "$work/source"
for attempt in 1 2 3 4; do
  if git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=120 -c http.postBuffer=524288000 fetch --depth=1 \
    "${lock[0]}" "refs/tags/${lock[1]}"; then
    break
  fi
  if (( attempt == 4 )); then
    echo "Gitee source fetch failed after four attempts"
    exit 1
  fi
  sleep "$((attempt * 5))"
done
git checkout --detach FETCH_HEAD
[[ $(git rev-parse HEAD) == "${lock[2]}" ]]
[[ $(dpkg-parsechangelog -S Version) == "${lock[3]}" ]]
dpkg-source --before-build .
git apply --check --ignore-space-change "$workspace/patches/ai-free/$source_package.patch"
git apply --ignore-space-change "$workspace/patches/ai-free/$source_package.patch"
bash "$workspace/scripts/apply_build_warning_patch.sh" "$source_package" "$workspace"
if [[ $source_package == orca ]]; then
  python3 "$workspace/scripts/patch_orca_translations.py" "$PWD"
  export GETTEXTDATADIRS="$workspace/patches/gettext${GETTEXTDATADIRS:+:$GETTEXTDATADIRS}"
fi
dch --newversion "${lock[3]}+liteai1" --distribution huanghe 'Build desktop without AI inference, OCR or AI service integration.'
# Keep the quick SDK ABI aligned with the pinned ISO, as for Control Center.
mkdir "$work/quick"
while read -r digest file; do
  [[ $digest =~ ^[0-9a-f]{64}$ && $file == libukui-quick-*_4.25.0.0-ok0.2_amd64.deb ]]
  curl -fL --retry 4 -o "$work/quick/$file" "https://archive.build.openkylin.top/openkylin/pool/main/u/ukui-quick/$file"
  echo "$digest  $work/quick/$file" | sha256sum -c -
done < "$workspace/config/control-center-build-deps.sha256"
cat > /etc/apt/preferences.d/openkylin-lite-quick <<'PIN'
Package: libukui-quick-core1 libukui-quick-dev libukui-quick-framework1 libukui-quick-platform1
Pin: version 4.25.0.0-ok0.2
Pin-Priority: 1001
PIN
apt-get install -y --allow-downgrades --no-install-recommends "$work/quick/"*.deb
if [[ $source_package == ukui-search ]]; then
  # Keep file-metadata aligned with the pinned ISO so shlibdeps doesn't bump dependencies beyond the Live root.
  mkdir "$work/metadata-deps"
  while read -r digest file; do
    [[ $digest =~ ^[0-9a-f]{64}$ && $file == libukui-file-metadata*4.25.0.0-ok0.1_amd64.deb ]]
    curl -fL --retry 4 -o "$work/metadata-deps/$file" "https://archive.build.openkylin.top/openkylin/pool/main/u/ukui-file-metadata/$file"
    echo "$digest  $work/metadata-deps/$file" | sha256sum -c -
  done < "$workspace/config/metadata-build-deps.sha256"
  cat > /etc/apt/preferences.d/openkylin-lite-metadata <<'PIN'
Package: libukui-file-metadata-bin libukui-file-metadata-dev libukui-file-metadata1
Pin: version 4.25.0.0-ok0.1
Pin-Priority: 1001
PIN
  apt-get install -y --allow-downgrades --no-install-recommends "$work/metadata-deps/"*.deb
fi
if [[ $source_package == kylin-scanner || $source_package == kylin-photo-viewer ]]; then
  # Keep libkysdk-base aligned with the pinned ISO so shlibdeps doesn't bump dependencies beyond the Live root.
  mkdir "$work/kysdk-base-deps"
  while read -r digest file; do
    [[ $digest =~ ^[0-9a-f]{64}$ && $file == libkysdk-*3.0.1.0-ok0.1*.deb ]]
    curl -fL --retry 4 -o "$work/kysdk-base-deps/$file" "https://archive.build.openkylin.top/openkylin/pool/main/libk/libkysdk-base/$file"
    echo "$digest  $work/kysdk-base-deps/$file" | sha256sum -c -
  done < "$workspace/config/kysdk-base-build-deps.sha256"
  cat > /etc/apt/preferences.d/openkylin-lite-kysdk-base <<'PIN'
Package: libkysdk-base libkysdk-base-dev libkysdk-basecommon libkysdk-conf2 libkysdk-conf2-dev libkysdk-conf2-tools libkysdk-config libkysdk-config-dev libkysdk-diagnostics libkysdk-diagnostics-dev libkysdk-gsetting libkysdk-gsetting-dev libkysdk-log libkysdk-log-dev libkysdk-timer libkysdk-timer-dev libkysdk-utils libkysdk-utils-dev
Pin: version 3.0.1.0-ok0.1*
Pin-Priority: 1001
PIN
  apt-get install -y --allow-downgrades --no-install-recommends "$work/kysdk-base-deps/"*.deb
fi
if [[ $source_package == kylin-scanner ]]; then
  # Keep libkysdk-system (powermanagement) aligned with the pinned ISO.
  mkdir "$work/kysdk-system-deps"
  while read -r digest file; do
    [[ $digest =~ ^[0-9a-f]{64}$ && $file == libkysdk-powermanagement*3.0.1.0-ok0.21*.deb ]]
    curl -fL --retry 4 -o "$work/kysdk-system-deps/$file" "https://archive.build.openkylin.top/openkylin/pool/main/libk/libkysdk-system/$file"
    echo "$digest  $work/kysdk-system-deps/$file" | sha256sum -c -
  done < "$workspace/config/powermanagement-build-deps.sha256"
  cat > /etc/apt/preferences.d/openkylin-lite-powermanagement <<'PIN'
Package: libkysdk-powermanagement libkysdk-powermanagement-dev
Pin: version 3.0.1.0-ok0.21*
Pin-Priority: 1001
PIN
  apt-get install -y --allow-downgrades --no-install-recommends "$work/kysdk-system-deps/"*.deb
fi
apt-get build-dep -y --no-install-recommends ./
for pc in /usr/lib/*/pkgconfig/poppler.pc /usr/lib/pkgconfig/poppler.pc; do
  [[ -f "$pc" ]] && sed -Ei 's/libcurl >= [0-9.]+/libcurl/g' "$pc"
done
python3 "$workspace/scripts/patch_build_tools.py"
if [[ $source_package == ukui-search ]]; then
  WARNING_SOURCE_DIR=$PWD WARNING_SOURCE_PACKAGE=$source_package python3 -m unittest discover -s "$workspace/tests" -p test_build_warning_runtime.py -v
fi
CMAKE_POLICY_VERSION_MINIMUM=3.10 dpkg-buildpackage -b -uc -us
output="$workspace/desktop-output/$source_package"
mkdir -p "$output"
mapfile -t selected < <(python3 - "$workspace/config/ai-free-desktop.json" "$source_package" <<'PY'
import json, sys
print('\n'.join(json.load(open(sys.argv[1]))['sources'][sys.argv[2]]['binaries']))
PY
)
for package in "${selected[@]}"; do
  deb=( "$work/${package}_"*.deb )
  [[ ${#deb[@]} == 1 && -f ${deb[0]} ]]
  cp -- "${deb[0]}" "$output/"
done
if [[ $source_package == orca ]]; then
  # Offline remaster needs the conventional, non-neural TTS backend as well.
  cd "$output"
  apt-get download speech-dispatcher-espeak-ng libespeak-ng1 espeak-ng-data libpcaudio0 libsonic0
fi
python3 "$workspace/scripts/check_desktop_candidates.py" "$output" "$source_package"
