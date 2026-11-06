#!/usr/bin/env bash
set -Eeuo pipefail
part=$1
[[ $part =~ ^lite\.iso\.part-[0-9]{3}$ ]] || exit 1
trap 'rm -f -- "output/$part"' EXIT
cat > "output/$part"
digest=$(sha256sum "output/$part")
gh release upload "$RELEASE_TAG" "output/$part"
printf '%s  %s\n' "${digest%% *}" "$part" >> output/PARTS-SHA256SUMS
