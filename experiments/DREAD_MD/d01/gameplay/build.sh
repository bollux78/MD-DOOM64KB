#!/usr/bin/env bash
set -euo pipefail
: "${GDK:?Set GDK to SGDK}"
wad=$(realpath "$1")
out=$(realpath -m "$2")
root=$(cd "$(dirname "$0")/.." && pwd)
export DREAD_COMBAT=1 DREAD_GAMEPLAY=1 DREAD_SKILL=easy
DREAD_EXTRA_FLAGS='-DDREAD_JOY_VBLANK -DDREAD_NATIVE_PERSPECTIVE -DDREAD_CELLSTREAM_REPORT -DDREAD_COMBAT_12_20 -DDREAD_EASY_MODE' \
    bash "$root/tools/build_map.sh" "$wad" EPISODE "$out" 'DREAD GAMEPLAY C7 EASY'
