#!/usr/bin/env bash
# Preserve the build exit status and retain every diagnostic for review.
set -uo pipefail
script=${1:?build script is required}
shift
name=${SOURCE_PACKAGE:-${PACKAGE:-$(basename "$script" .sh)}}
[[ $name =~ ^[a-zA-Z0-9_.+-]+$ ]] || exit 2
directory="$PWD/build-reports/$name"
mkdir -p "$directory"
bash "$script" "$@" 2>&1 | tee "$directory/build.log"
statuses=("${PIPESTATUS[@]}")
status=${statuses[0]}
if (( status == 0 && statuses[1] != 0 )); then
  status=${statuses[1]}
fi
python3 scripts/report_build_warnings.py "$directory/build.log" "$status" || {
  (( status != 0 )) || status=1
}
exit "$status"
