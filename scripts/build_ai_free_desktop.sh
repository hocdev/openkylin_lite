#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
export DEBFULLNAME='openKylin Lite' DEBEMAIL='openkylin-lite@users.noreply.github.com'
export DEB_BUILD_OPTIONS=parallel=2
workspace=$PWD
source_package=${SOURCE_PACKAGE:?SOURCE_PACKAGE is required}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates git build-essential devscripts python3 curl binutils
mapfile -t lock < <(python3 - "$source_package" <<'PY'
import json, sys
policy = json.load(open('config/ai-free-desktop.json'))
assert sys.argv[1] in policy['sources']
entry = next(p for p in json.load(open('config/rebuild-sources.json'))['packages'] if p['source'] == sys.argv[1])
print(entry['repository']); print(entry['tag']); print(entry['commit']); print(entry['version'])
PY
)
[[ ${#lock[@]} == 4 ]]
git init "$work/source"
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
git apply --check "$workspace/patches/ai-free/$source_package.patch"
git apply "$workspace/patches/ai-free/$source_package.patch"
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
apt-get build-dep -y --no-install-recommends ./
for pc in /usr/lib/*/pkgconfig/poppler.pc /usr/lib/pkgconfig/poppler.pc; do
  [[ -f "$pc" ]] && sed -Ei 's/libcurl >= [0-9.]+/libcurl/g' "$pc"
done
CMAKE_POLICY_VERSION_MINIMUM=3.5 dpkg-buildpackage -b -uc -us
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
