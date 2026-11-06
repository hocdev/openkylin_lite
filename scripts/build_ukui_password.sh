#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export DEBFULLNAME='openKylin Lite'
export DEBEMAIL='openkylin-lite@users.noreply.github.com'
workspace=$PWD
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

apt-get -o Acquire::Retries=3 update
apt-get install -y --no-install-recommends ca-certificates git build-essential devscripts

git init "$work/source"
cd "$work/source"
for attempt in 1 2 3 4; do
  if git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=60 fetch --depth=1 \
    "https://gitee.com/openkylin/$SOURCE_PACKAGE.git" "refs/tags/$SOURCE_TAG"; then
    break
  fi
  if (( attempt == 4 )); then
    echo "Gitee source fetch failed after four attempts"
    exit 1
  fi
  sleep "$((attempt * 5))"
done
git checkout --detach FETCH_HEAD
[[ $(git rev-parse HEAD) == "$SOURCE_COMMIT" ]]
# Materialize the vendor's quilt patches before changing overlapping code.
dpkg-source --before-build .
git apply --check "$workspace/patches/ukui-password/$PACKAGE.patch"
git apply "$workspace/patches/ukui-password/$PACKAGE.patch"
if [[ $PACKAGE == ukui-greeter ]]; then
  # OpenCV was used only to decode facial authentication video frames.
  python3 - <<'PYTHON'
import pathlib
import re

for path in (
    'ukui-greeter/BiometricAuth/biometricauthwidget.cpp',
    'ukui-greeter/greeter/loginoptionswidget.cpp',
):
    file = pathlib.Path(path)
    text = file.read_text()
    if text.count('#include <opencv2/opencv.hpp>') != 1:
        raise SystemExit(f'Unexpected OpenCV include in {path}')
    text = text.replace('#include <opencv2/opencv.hpp>\n', '')
    text, count = re.subn(
        r'(void \w+::onFrameWritten\(int drvid\)\n\{)\n.*?\n\}',
        r'\1\n    Q_UNUSED(drvid);\n}',
        text,
        count=1,
        flags=re.S,
    )
    if count != 1 or 'cv::' in text:
        raise SystemExit(f'Unexpected facial frame handler in {path}')
    file.write_text(text)

project = pathlib.Path('ukui-greeter/ukui-greeter.pro')
text, count = re.subn(r' \\\n[ \t]+/usr/include/opencv4\n', '\n', project.read_text())
if count != 1:
    raise SystemExit('Unexpected OpenCV include path in the greeter project')
project.write_text(re.sub(r' -lopencv_\w+', '', text))
PYTHON
  sed -Ei '/^[[:blank:]]+libopencv-dev,[[:blank:]]*$/d' debian/control
fi
if [[ $PACKAGE == ukui-polkit ]]; then
  # Keep password-dialog translations under the package that loads them.
  sed -i "s|\${UKUI_BIOMETRIC_DIR}/i18n_qm/polkit|/usr/share/ukui-polkit/translations|" polkit-agent/CMakeLists.txt
  sed -i '
    s|%1/i18n_qm/polkit/%2.qm").arg(GET_STR(UKUI_BIOMETRIC)).arg(locale)|/usr/share/ukui-polkit/translations/%1.qm").arg(locale)|
    s/QTranslator translator_main, translator_bio;/QTranslator translator_main;/
    /qmfile_bio/d
    /translator_bio/d
    /#include "biodevices.h"/d
    /    BioDevices devices;/,+2d
  ' polkit-agent/src/PolkitAgent.cpp
  sed -i 's|/usr/share/ukui-biometric/i18n_qm/polkit/|/usr/share/ukui-polkit/translations/|' debian/ukui-polkit.install
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
if grep -Eq 'biometric|fprint|bio-(app|drv)-api' <<< "$dependencies"; then
  echo "Biometric package dependency remains in $PACKAGE"
  exit 1
fi
if [[ $PACKAGE == ukui-greeter ]] && grep -q 'libopencv' <<< "$dependencies"; then
  echo 'The greeter still depends on OpenCV'
  exit 1
fi
mkdir -p "$workspace/ukui-output"
cp -- "${deb[0]}" "$workspace/ukui-output/"
dpkg-deb -I "${deb[0]}"
