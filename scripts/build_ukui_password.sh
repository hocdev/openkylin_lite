#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates git build-essential devscripts equivs

git init "$work/source"
cd "$work/source"
git fetch --depth=1 "https://gitee.com/openkylin/$PACKAGE.git" "refs/tags/$SOURCE_TAG"
git checkout --detach FETCH_HEAD
[[ $(git rev-parse HEAD) == "$SOURCE_COMMIT" ]]
git apply --check "$workspace/patches/ukui-password/$PACKAGE.patch"
git apply "$workspace/patches/ukui-password/$PACKAGE.patch"

# Keep the regular LightDM/PAM dependencies. Only remove the biometric backend.
grep -q 'libpam-biometric' debian/control
sed -Ei '
  /^[[:blank:]]+libpam-biometric[[:blank:]]*\([^)]*\),[[:blank:]]*$/d
  s/libpam-biometric[[:blank:]]*\([^)]*\),[[:blank:]]*//
  /^Suggests: biometric-auth$/d
  / supports biometric /,+1d
' debian/control
if grep -q 'libpam-biometric' debian/control; then
  echo "Could not remove the biometric dependency from $PACKAGE"
  exit 1
fi
dch --local +lite --distribution huanghe 'Disable biometric authentication in this candidate.'
apt-get build-dep -y --no-install-recommends ./
dpkg-buildpackage -b -uc -us

deb=( "$work/${PACKAGE}_"*_amd64.deb )
[[ ${#deb[@]} == 1 && -f ${deb[0]} ]]
dependencies=$(dpkg-deb -f "${deb[0]}" Depends Pre-Depends Recommends Suggests)
if grep -Eq 'libpam-biometric|biometric-auth' <<< "$dependencies"; then
  echo "Biometric package dependency remains in $PACKAGE"
  exit 1
fi
mkdir -p "$workspace/ukui-output"
cp -- "${deb[0]}" "$workspace/ukui-output/"
dpkg-deb -I "${deb[0]}"
