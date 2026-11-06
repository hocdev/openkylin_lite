#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

# The snapshot retains the OpenCV 4.6 runtime used by the ISO, but its
# development index already selects 4.10 and omits some build tools.
if [[ $PACKAGE == ukui-greeter ]]; then
  cat > /etc/apt/sources.list.d/openkylin-iso.list <<'EOF'
deb [signed-by=/usr/share/keyrings/openkylin-archive-keyring.gpg] http://archive-proxy.factory.openkylin.top/kif/archive/proxy/build/3171/archive.build.openkylin.top_openkylin huanghe main cross pty
EOF
fi
apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates curl git build-essential devscripts

git init "$work/source"
cd "$work/source"
git fetch --depth=1 "https://gitee.com/openkylin/$SOURCE_PACKAGE.git" "refs/tags/$SOURCE_TAG"
git checkout --detach FETCH_HEAD
[[ $(git rev-parse HEAD) == "$SOURCE_COMMIT" ]]
# Materialize the vendor's quilt patches before changing overlapping code.
dpkg-source --before-build .
git apply --check "$workspace/patches/ukui-password/$PACKAGE.patch"
git apply "$workspace/patches/ukui-password/$PACKAGE.patch"
if [[ $PACKAGE == ukui-greeter ]]; then
  opencv_debs=()
  while read -r checksum file; do
    curl --fail --location --retry 3 \
      "https://archive.openkylin.top/openkylin/pool/main/o/opencv/$file" -o "$work/$file"
    printf '%s  %s\n' "$checksum" "$work/$file" | sha256sum --check
    opencv_debs+=("$work/$file")
  done <<'EOF'
cef70f6b911e3a6056168feaaa0b005e9900416d1baa9763785b421ffb911b75 libopencv-core-dev_4.6.0+dfsg-ok9_amd64.deb
638842f26ca9bac04fed7f7f9466ab00ac20247a43a460f566e8071aaa58f046 libopencv-imgcodecs-dev_4.6.0+dfsg-ok9_amd64.deb
90dd58ad7a9225f2a2635e0dc0b4ee09248b94b7f1a60b7ae4e4165b2f6356dc libopencv-imgproc-dev_4.6.0+dfsg-ok9_amd64.deb
EOF
  apt-get install -y --no-install-recommends "${opencv_debs[@]}"
  sed -i 's/libopencv-dev,/libopencv-imgcodecs-dev (= 4.6.0+dfsg-ok9),/' debian/control
fi
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
apt-get build-dep -y --no-install-recommends ./
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
