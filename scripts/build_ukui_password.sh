#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

# Use the signed archive snapshot recorded in the original ISO. The moving
# huanghe archive now builds the greeter against OpenCV 4.10 instead of 4.6.
cat > "$work/iso.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/openkylin-archive-keyring.gpg] http://archive-proxy.factory.openkylin.top/kif/archive/proxy/build/3171/archive.build.openkylin.top_openkylin huanghe main cross pty
EOF
apt_options=(-o "Dir::Etc::sourcelist=$work/iso.list" -o Dir::Etc::sourceparts=- -o Acquire::Retries=3)
apt-get "${apt_options[@]}" update
apt-get "${apt_options[@]}" install -y --no-install-recommends ca-certificates git build-essential devscripts equivs

git init "$work/source"
cd "$work/source"
git fetch --depth=1 "https://gitee.com/openkylin/$SOURCE_PACKAGE.git" "refs/tags/$SOURCE_TAG"
git checkout --detach FETCH_HEAD
[[ $(git rev-parse HEAD) == "$SOURCE_COMMIT" ]]
# Materialize the vendor's quilt patches before changing overlapping code.
dpkg-source --before-build .
git apply --check "$workspace/patches/ukui-password/$PACKAGE.patch"
git apply "$workspace/patches/ukui-password/$PACKAGE.patch"
if [[ $PACKAGE == ukui-screensaver ]]; then
  backend=src/lock-backend/dbusupperinterface.cpp
  grep -Fxq '    m_bioAuth = QSharedPointer<BioAuthenticate>(new BioAuthenticate(this));' "$backend"
  sed -i '/^    m_bioAuth = QSharedPointer<BioAuthenticate>(new BioAuthenticate(this));$/d' "$backend"
fi

# Keep the regular LightDM/PAM dependencies. Only remove the biometric backend.
sed -Ei '
  /^[[:blank:]]+libpam-biometric[[:blank:]]*\([^)]*\),[[:blank:]]*$/d
  s/libpam-biometric[[:blank:]]*\([^)]*\),[[:blank:]]*//
  /^Suggests: biometric-auth$/d
  / supports biometric /,+1d
  / The ukui-polkit package supports general authentication and/,+2c\ This authentication agent uses passwords.
' debian/control
if grep -Eq 'libpam-biometric[[:blank:]]*\(' debian/control; then
  echo "Could not remove the biometric dependency from $PACKAGE"
  exit 1
fi
dch --local +lite --distribution huanghe 'Disable biometric authentication in this candidate.'
apt-get "${apt_options[@]}" build-dep -y --no-install-recommends ./
CMAKE_POLICY_VERSION_MINIMUM=3.5 dpkg-buildpackage -b -uc -us

deb=( "$work/${PACKAGE}_"*_amd64.deb )
[[ ${#deb[@]} == 1 && -f ${deb[0]} ]]
dependencies=$(dpkg-deb -f "${deb[0]}" Depends Pre-Depends Recommends Suggests)
if grep -Eq 'libpam-biometric|biometric-auth' <<< "$dependencies"; then
  echo "Biometric package dependency remains in $PACKAGE"
  exit 1
fi
if [[ $PACKAGE == ukui-greeter ]] && ! grep -q 'libopencv-core406' <<< "$dependencies"; then
  echo 'The greeter was not built against the ISO OpenCV ABI'
  exit 1
fi
mkdir -p "$workspace/ukui-output"
cp -- "${deb[0]}" "$workspace/ukui-output/"
dpkg-deb -I "${deb[0]}"
