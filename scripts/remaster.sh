#!/usr/bin/env bash
# dpkg-query templates intentionally use literal dollar expressions.
# shellcheck disable=SC2016
set -Eeuo pipefail
export LC_ALL=C
[[ $EUID == 0 ]] || { echo 'Run with sudo'; exit 1; }
MODE=${MODE:-inspect}
[[ $MODE == inspect || $MODE == profile || $MODE == build ]] || exit 1
cd "${GITHUB_WORKSPACE:-$PWD}"
repo=$PWD
mkdir -p reports output
work=$(mktemp -d "${RUNNER_TEMP:-/tmp}/openkylin.XXXXXX")
cleanup() {
  mountpoint -q "$work/ostree-tree/proc" && umount "$work/ostree-tree/proc"
  mountpoint -q "$work/ostree-tree/dev" && umount "$work/ostree-tree/dev"
  mountpoint -q "$work/root/proc" && umount "$work/root/proc"
  mountpoint -q "$work/root/dev" && umount "$work/root/dev"
  mountpoint -q "$work/root" && umount "$work/root"
  mountpoint -q "$work/lower" && umount "$work/lower"
  mountpoint -q "$work/iso" && umount "$work/iso"
  if ! mountpoint -q "$work/ostree-tree/proc" && ! mountpoint -q "$work/ostree-tree/dev" && ! mountpoint -q "$work/iso" && ! mountpoint -q "$work/root" && ! mountpoint -q "$work/lower"; then
    rm -rf -- "$work"
  fi
  return 0
}
trap cleanup EXIT
disk_stage() {
  { printf '\nStage: %s\n' "$1"; df -h "$work"; } | tee -a "$repo/reports/disk-stages.txt"
}
mkdir "$work/iso"
if [[ $MODE != inspect && ! ${SOURCE_SHA256:-} =~ ^[[:xdigit:]]{64}$ ]]; then
  echo 'Build requires a pinned source SHA256.'; exit 1
fi
df -h . "$work" | tee reports/disk-before.txt
free_bytes=$(df -B1 --output=avail "$work" | tail -1)
if [[ -n ${ISO_SOURCE_DIR:-} ]]; then
  [[ -f "$ISO_SOURCE_DIR/source.iso" ]] || { echo 'Prepare original ISO first'; exit 1; }
  ln -s "$ISO_SOURCE_DIR/source.iso" "$work/source.iso"
else
  (( free_bytes > 10 * 1024**3 )) || { echo 'Need at least 10 GiB free to download ISO.'; exit 1; }
  ISO_SOURCE_DIR="$work" bash scripts/prepare_source.sh
fi
[[ $(stat -Lc %s "$work/source.iso") == 7647188992 ]] || { echo 'Unexpected ISO size'; exit 1; }
sha256sum "$work/source.iso" | tee reports/source-sha256.txt
if [[ -n ${SOURCE_SHA256:-} ]]; then
  [[ ${SOURCE_SHA256} =~ ^[[:xdigit:]]{64}$ ]] || exit 1
  echo "$SOURCE_SHA256  $work/source.iso" | sha256sum -c -
fi
mount -o loop,ro "$work/source.iso" "$work/iso"
xorriso -indev "$work/source.iso" -report_el_torito plain > reports/boot-source.txt 2>&1
find "$work/iso" -type f -printf '%s\t%P\n' | sort -nr > reports/iso-files.tsv
mapfile -d '' squash < <(find "$work/iso" -type f -name '*.squashfs' -print0)
[[ ${#squash[@]} == 1 ]] || { echo 'Expected one squashfs. Review iso-files.tsv; layered ISOs need a custom build.'; exit 1; }
sq=${squash[0]}
relative=${sq#"$work/iso/"}
unsquashfs -s "$sq" > reports/squashfs-info.txt
python3 - "$work/source.iso" "$sq" "$work/iso" > reports/size-budget.txt <<'PY'
import json,pathlib,sys
target=json.loads(pathlib.Path('config/size-target.json').read_text())
source,squash,tree=map(pathlib.Path,sys.argv[1:])
other=sum(p.stat().st_size for p in tree.rglob('*') if p.is_file() and p != squash)
print('Target: 3-4 decimal GB; below 3 GB is acceptable without padding.')
print(f'Source bytes: {source.stat().st_size}')
print(f'Original squashfs bytes: {squash.stat().st_size}')
print(f'Other ISO files, logical bytes: {other}')
print(f'Approximate squashfs budget: {target["max_bytes"]-other} bytes BEFORE ISO metadata/boot overhead')
print('This is a planning estimate, not a compressed-size prediction or proof of feasibility.')
PY
unsquashfs -cat "$sq" var/lib/dpkg/status > "$work/status"
python3 - "$work/status" > reports/packages.tsv <<'PY'
import sys
rows=[]
for paragraph in open(sys.argv[1]).read().split('\n\n'):
    fields={}
    for line in paragraph.splitlines():
        if line and not line[0].isspace() and ': ' in line:
            k,v=line.split(': ',1); fields[k]=v
    if fields.get('Status') == 'install ok installed':
        rows.append((int(fields.get('Installed-Size','0')),fields['Package'],fields.get('Description','')))
print('Installed-KiB\tPackage\tDescription')
for size,name,description in sorted(rows,reverse=True):
    print(f'{size}\t{name}\t{description}')
PY
unsquashfs -ll "$sq" 'usr/share/applications/*' > reports/desktop-files.txt
cp "$work/status" reports/dpkg-status.txt
if [[ -f "$work/iso/$(dirname "$relative")/filesystem.manifest-remove" ]]; then
  cp "$work/iso/$(dirname "$relative")/filesystem.manifest-remove" reports/filesystem.manifest-remove
fi
if [[ $MODE == inspect ]]; then
  mkdir "$work/lower"
  mount -t squashfs -o loop,ro "$sq" "$work/lower"
  python3 scripts/collect_review.py "$work/lower"
  umount "$work/lower"
fi
{
  echo '### openKylin ISO inspection'
  echo 'Source: 7,647,188,992 bytes (7.12 GiB).'
  echo 'See packages.tsv for exact installed packages, largest first.'
  echo 'Disk capacity below is measured, not guaranteed for future runners.'
  echo '```'
  df -h "$work"
  echo '```'
} >> "${GITHUB_STEP_SUMMARY:-$repo/reports/summary.md}"
[[ $MODE != inspect ]] || exit 0
mapfile -t packages < <(sed 's/#.*//;s/^[[:space:]]*//;s/[[:space:]]*$//;/^$/d' config/remove-packages.txt)
(( ${#packages[@]} )) || { echo 'No packages selected. Edit config/remove-packages.txt.'; exit 1; }
for p in "${packages[@]}"; do
  [[ $p =~ ^[a-z0-9][a-z0-9+.-]+$ ]] || { echo "Invalid exact package: $p"; exit 1; }
done
# OverlayFS reads unchanged files from the compressed original. Only changed
# files consume upper-layer space; deletions are whiteouts, not copied files.
root=$work/root
mkdir "$root" "$work/lower" "$work/upper" "$work/overlay-work"
mount -t squashfs -o loop,ro "$sq" "$work/lower"
mount -t overlay overlay -o "lowerdir=$work/lower,upperdir=$work/upper,workdir=$work/overlay-work" "$root"
disk_stage overlay-mounted
purge_packages() (
local root=$1 baseline=$2 report_dir=$3
mkdir -p "$report_dir"
python3 scripts/check_apps.py "$root" config/remove-packages.txt config/reviewed-apps.json > "$report_dir/reviewed-apps.txt"
mount --bind /dev "$root/dev"
mount -t proc proc "$root/proc"
chroot "$root" apt-get check
chroot "$root" dpkg --audit > "$report_dir/dpkg-audit-before.txt"
[[ ! -s "$report_dir/dpkg-audit-before.txt" ]] || { echo 'Original package database is unhealthy'; exit 1; }
chroot "$root" dpkg-query -W '-f=${Package} ${Version}\n' > "$report_dir/manifest-before.txt"
for p in "${packages[@]}"; do
  chroot "$root" dpkg-query -W '-f=${Status}\n' "$p" | grep -qx 'install ok installed'
done
# Do not autoremove: only the explicit package set is allowed to disappear.
chroot "$root" apt-get -o APT::Get::AutomaticRemove=false -s purge "${packages[@]}" > "$report_dir/purge-plan.txt"
awk '/^(Remv|Purg) / {print $2}' "$report_dir/purge-plan.txt" | sort -u > "$work/planned"
printf '%s\n' "${packages[@]}" | sort -u > "$work/allowed"
comm -23 "$work/planned" "$work/allowed" > "$report_dir/unexpected-removals.txt"
[[ ! -s "$report_dir/unexpected-removals.txt" ]] || { echo 'Dependencies would remove additional packages; review unexpected-removals.txt'; exit 1; }
while read -r p; do
  case "$p" in
    linux-*|grub*|shim*|systemd*|udev*|apt*|dpkg*|*ukui*|*installer*|calamares*|live-*|network*|lightdm*|sddm*|xserver-*|dbus*|*firmware*|*driver*|*desktop*|*session*|*settings*|*control-center*|*security*|*keyring*|*polkit*|*pam*|*sudo*|*initramfs*|*cryptsetup*|*lvm*|kylin-core*|*font*|*locale*|*language*|*input*|*ibus*|*fcitx*|*pipewire*|*pulseaudio*|*alsa*|*cups*|*bluetooth*|*bluez*|*mesa*|*wayland*|*xorg*)
      echo "Protected system package: $p"; exit 1 ;;
  esac
  essential=$(chroot "$root" dpkg-query -W '-f=${Essential}' "$p")
  [[ $essential != yes ]] || { echo "Essential package: $p"; exit 1; }
done < "$work/planned"
if [[ -e "$root/usr/sbin/policy-rc.d" || -L "$root/usr/sbin/policy-rc.d" ]]; then
  mv "$root/usr/sbin/policy-rc.d" "$work/policy-rc.d.original"
fi
printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"
chmod +x "$root/usr/sbin/policy-rc.d"
DEBIAN_FRONTEND=noninteractive chroot "$root" apt-get -o APT::Get::AutomaticRemove=false --no-download -y purge "${packages[@]}"
rm "$root/usr/sbin/policy-rc.d"
if [[ -e "$work/policy-rc.d.original" || -L "$work/policy-rc.d.original" ]]; then
  mv "$work/policy-rc.d.original" "$root/usr/sbin/policy-rc.d"
fi
chroot "$root" apt-get check
chroot "$root" dpkg --audit > "$report_dir/dpkg-audit.txt"
[[ ! -s "$report_dir/dpkg-audit.txt" ]] || { echo 'dpkg audit failed'; exit 1; }
chroot "$root" apt-get clean
find "$root/var/cache/apt/archives" -type f -name '*.deb' -delete
find "$root/var/lib/apt/lists" -type f -delete
chroot "$root" dpkg-query -W '-f=${Package} ${Version}\n' > "$report_dir/manifest-after.txt"
python3 - "$baseline" "$root/var/lib/dpkg/status" "$work/allowed" > "$report_dir/package-diff.txt" <<'PY'
import pathlib,sys
sys.path.insert(0, 'scripts')
from check_apps import read_status
before,after=[read_status(pathlib.Path(p).read_text()) for p in sys.argv[1:3]]
allowed=set(pathlib.Path(sys.argv[3]).read_text().splitlines())
removed=set(before)-set(after)
added=set(after)-set(before)
changed={p for p in before.keys() & after.keys() if before[p]['Version'] != after[p]['Version']}
print('Removed:', ', '.join(sorted(removed)))
print('Added:', ', '.join(sorted(added)))
print('Version changes:', ', '.join(sorted(changed)))
if removed != allowed or added or changed:
    raise SystemExit('Package changes differ from the reviewed removal list')
PY
umount "$root/proc"
umount "$root/dev"
)
python3 scripts/collect_review.py "$root"
purge_packages "$root" "$work/lower/var/lib/dpkg/status" reports
du -x --apparent-size -B1 --max-depth=3 "$root" | sort -nr | sed -n '1,100p' > reports/rootfs-largest-dirs.tsv
find "$root" -xdev -type f -size +10M -printf '%s\t%P\n' | sort -nr > reports/rootfs-largest-files.tsv
if [[ $MODE == profile ]]; then
  ostree_repo="$root/sysroot/ostree/repo"
  if [[ -f "$ostree_repo/config" ]]; then
    {
      echo '### OSTree refs and their commits'
      if refs=$(ostree --repo="$ostree_repo" refs); then
        while IFS= read -r ref; do
          [[ -n $ref ]] || continue
          printf '%s\t' "$ref"
          ostree --repo="$ostree_repo" rev-parse "$ref" || true
          ostree --repo="$ostree_repo" show --raw "$ref" || true
          ostree --repo="$ostree_repo" ls "$ref" / || true
          for path in /etc /usr/etc /usr/lib/modules /var/lib/dpkg/status /usr/share/dpkg/status; do
            ostree --repo="$ostree_repo" ls "$ref" "$path" || true
          done
          for path in /var/lib/dpkg/status /usr/share/dpkg/status; do
            report_name=${path//\//-}
            if ! ostree --repo="$ostree_repo" cat "$ref" "$path" > "reports/ostree${report_name}.txt"; then
              rm -f "reports/ostree${report_name}.txt"
            fi
          done
        done <<< "$refs"
      fi
      echo '### Unreachable objects (dry run)'
      ostree --repo="$ostree_repo" prune --no-prune || true
      echo '### Deployment directories'
      if [[ -d "$root/sysroot/ostree/deploy" ]]; then
        find "$root/sysroot/ostree/deploy" -mindepth 1 -maxdepth 3 -type d -printf '%P\n'
      fi
    } > reports/ostree-profile.txt 2>&1
  fi
  { echo '### Largest files after package removal'; echo '```'; sed -n '1,25p' reports/rootfs-largest-files.tsv; echo '```'; } >> "${GITHUB_STEP_SUMMARY:-$repo/reports/summary.md}"
  exit 0
fi
# Rebuild the install snapshot independently from the live filesystem.
ostree_repo="$root/sysroot/ostree/repo"
branch=openkylin/desktop/v3.0/community/general/all/release/amd64
source_ref="openkylin:$branch"
expected_commit=7abfcb4c781409a4e4adf4f4b5faf90011926151faa5285bb9ffd97038f2e3c2
[[ $(ostree --repo="$ostree_repo" refs) == "$source_ref" ]]
[[ $(ostree --repo="$ostree_repo" rev-parse "$source_ref") == "$expected_commit" ]]
snapshot="$work/ostree-tree"
ostree --repo="$ostree_repo" checkout --force-copy "$expected_commit" "$snapshot"
[[ -d "$snapshot/usr/etc" && ! -e "$snapshot/etc" && ! -L "$snapshot/etc" ]]
mv "$snapshot/usr/etc" "$snapshot/etc"
cp "$snapshot/var/lib/dpkg/status" "$work/ostree-status-before"
purge_packages "$snapshot" "$work/ostree-status-before" reports/ostree
mv "$snapshot/etc" "$snapshot/usr/etc"

# Create a parentless commit so the original package payload is not retained
# through history. Retain the layout and release metadata required by openKylin.
new_repo="$work/ostree-repo"
mode=$(ostree --repo="$ostree_repo" config get core.mode)
ostree --repo="$new_repo" init --mode="$mode"
metadata=()
for key in install-size os_version changelog update-name os_BuildID version update-type description download-size; do
  value=$(ostree --repo="$ostree_repo" show --print-metadata-key="$key" "$expected_commit")
  metadata+=(--add-metadata="$key=$value")
done
new_commit=$(ostree --repo="$new_repo" commit --parent=none --branch="$branch" \
  --subject="$source_ref" --tree="dir=$snapshot" "${metadata[@]}")
# The installer image exposes a remote-tracking ref. Reproduce the same ref
# namespace in the fresh repository, without copying old commits or summaries.
mkdir -p "$new_repo/refs/remotes/openkylin/$(dirname "$branch")"
printf '%s\n' "$new_commit" > "$new_repo/refs/remotes/openkylin/$branch"
ostree --repo="$new_repo" refs --delete "$branch"
[[ $(ostree --repo="$new_repo" rev-parse "$source_ref") == "$new_commit" ]]
ostree --repo="$new_repo" fsck > reports/ostree/fsck.txt
printf '%s\n' "$new_commit" > reports/ostree/commit.txt
du -sx --apparent-size -B1 "$ostree_repo" "$new_repo" > reports/ostree/repo-size.tsv
rm -rf -- "$snapshot" "$ostree_repo"
mkdir "$ostree_repo"
cp -a "$new_repo/." "$ostree_repo/"
rm -rf -- "$new_repo"
disk_stage ostree-rebuilt
size=$(du -sx --block-size=1 "$root" | cut -f1)
mksquashfs "$root" "$work/filesystem.squashfs" -noappend -comp xz -b 1M -processors 2 -mem 2G
# Release writable overlay changes as soon as the new filesystem is complete.
umount "$root"
umount "$work/lower"
rm -rf -- "$work/upper" "$work/overlay-work"
disk_stage squashfs-complete
mkdir "$work/meta"
cp reports/manifest-after.txt "$work/meta/filesystem.manifest"
printf '%s\n' "$size" > "$work/meta/filesystem.size"
python3 scripts/update_iso_metadata.py "$work/iso" "$work/meta" "$relative" "$work/filesystem.squashfs" "$work/allowed" > "$work/maps"
mapfile -d '' mappings < "$work/maps"
args=()
for ((i=0; i<${#mappings[@]}; i+=2)); do
  args+=(-map "${mappings[i]}" "${mappings[i+1]}")
done
xorriso -indev "$work/source.iso" -outdev "$work/lite.iso" "${args[@]}" -boot_image any replay -commit -end
source_bytes=$(stat -Lc %s "$work/source.iso")
umount "$work/iso"
rm "$work/source.iso"
disk_stage source-unmounted-original-retained-in-cache
xorriso -indev "$work/lite.iso" -report_el_torito plain > reports/boot-output.txt 2>&1
# Mount and compare directly: no second extracted squashfs on disk.
mount -o loop,ro "$work/lite.iso" "$work/iso"
cmp "$work/filesystem.squashfs" "$work/iso/$relative"
umount "$work/iso"
rm "$work/filesystem.squashfs"
disk_stage squashfs-released
stat -c '%s' "$work/lite.iso" > reports/output-bytes.txt
(( $(stat -c %s "$work/lite.iso") < source_bytes )) || { echo 'Output did not shrink'; exit 1; }
python3 - "$work/lite.iso" <<'PY'
import json,pathlib,sys
target=json.loads(pathlib.Path('config/size-target.json').read_text())
size=pathlib.Path(sys.argv[1]).stat().st_size
message = f'ISO size: {size} bytes ({size/1e9:.3f} GB); maximum: {target["max_bytes"]} bytes'
pathlib.Path('reports/size-result.txt').write_text(message + '\n')
print(message, flush=True)
if size > target['max_bytes']:
    raise SystemExit('Size target not met. Review optional apps; do not remove protected components to force the target.')
PY
(cd "$work" && sha256sum lite.iso) > output/SHA256SUMS
# Move on the same filesystem; do not duplicate the ISO in the workspace.
# The following workflow step uploads one part at a time, then deletes it.
printf '%s\n' "$work/lite.iso" > output/iso-path.txt
cp reports/manifest-after.txt output/
chmod 755 "$work"
chmod 644 "$work/lite.iso"
# Keep only the completed ISO for the upload step. Cleanup still runs on failure.
trap - EXIT
