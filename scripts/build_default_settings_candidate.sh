#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
export DEBFULLNAME='openKylin Lite' DEBEMAIL='openkylin-lite@users.noreply.github.com'
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
curl -fL --retry 4 --retry-delay 5 -o "$work/source.tar.xz" \
  https://archive.build.openkylin.top/openkylin/pool/main/o/openkylin-default-settings/openkylin-default-settings_3.0.2.tar.xz
echo "6514332f233e43135eb07c3b6d4931bdd99d88a7c5efedbe19192bbcee86695c  $work/source.tar.xz" | sha256sum -c -
mkdir "$work/source"
tar -xJf "$work/source.tar.xz" --strip-components=1 -C "$work/source"
cd "$work/source"
[[ $(dpkg-parsechangelog -S Version) == 1:3.0.2 ]]
python3 -m unittest discover -s "$workspace/tests" -p test_default_settings.py -v
apt-get build-dep -y --no-install-recommends ./
# Build both variants so every configuration asset can be compared, rather
# than assuming this metapackage has no desktop settings of its own.
dpkg-buildpackage -b -uc -us
original=( "$work/openkylin-default-settings_"*_all.deb )
[[ ${#original[@]} == 1 && -f ${original[0]} ]]
cp "${original[0]}" "$work/original.deb"
python3 "$workspace/scripts/patch_default_settings.py" debian/control
dch --local +lite --distribution huanghe 'Retain desktop defaults without requiring telemetry.'
dpkg-buildpackage -b -uc -us
patched=( "$work/openkylin-default-settings_"*+lite*_all.deb )
[[ ${#patched[@]} == 1 && -f ${patched[0]} ]]
python3 "$workspace/scripts/check_default_settings_candidate.py" "$work/original.deb" "${patched[0]}"
mkdir -p "$workspace/control-center-output"
cp "${patched[0]}" "$workspace/control-center-output/"
