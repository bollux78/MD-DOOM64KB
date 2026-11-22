#!/usr/bin/env bash
set -euo pipefail
: "${GDK:?Set GDK to your SGDK directory}"
wad=$(realpath "$1")
out=$(realpath -m "$2")
root=$(cd "$(dirname "$0")/.." && pwd)
export DREAD_COMBAT=1
for variant in control native; do
    flags='-DDREAD_VALIDATION_TEST -DDREAD_JOY_VBLANK -DDREAD_CELLSTREAM_REPORT'
    [[ "$variant" != native ]] || flags+=' -DDREAD_NATIVE_PERSPECTIVE'
    DREAD_EXTRA_FLAGS="$flags" bash "$root/tools/build_map.sh" "$wad" EPISODE "$out/$variant" "DREAD PERSPECTIVE $variant"
done
