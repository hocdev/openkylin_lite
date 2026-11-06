#!/usr/bin/env bash
set -Eeuo pipefail
iso=$(cat output/iso-path.txt)
work=$(dirname "$iso")
[[ $work == "${RUNNER_TEMP}/openkylin."* && $iso == "$work/lite.iso" ]] || exit 1
cleanup() { sudo rm -rf -- "$work"; }
trap cleanup EXIT
gh release create "$RELEASE_TAG" --draft --title "openKylin Lite $RELEASE_TAG" --notes 'Experimental remaster; boot and installation are unverified. Join parts in numeric order and verify SHA256SUMS. An incomplete upload leaves a draft; rerun the workflow to retry.'
: > output/PARTS-SHA256SUMS
# split buffers one part on disk, uploads it, then removes it before continuing.
export RELEASE_TAG
# FILE is provided by split to each filter subprocess.
# shellcheck disable=SC2016
split -b 1900M -d -a 3 --filter='bash scripts/upload-part.sh "$FILE"' "$iso" lite.iso.part-
gh release upload "$RELEASE_TAG" output/SHA256SUMS output/PARTS-SHA256SUMS output/manifest-after.txt
rm output/iso-path.txt
