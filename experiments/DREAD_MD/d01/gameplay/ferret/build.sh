#!/usr/bin/env bash
# Manual entrypoint; never invoked on push. Regenerate all nine maps from WAD.
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: build.sh SHAREWARE_WAD OUTPUT'; exit 2; }
export DREAD_COMBAT=1 DREAD_GAMEPLAY=1 DREAD_SKILL=easy
export DREAD_FERRET_RENDERER=1 DREAD_FERRET_COLUMN_RLE=1 DREAD_SOURCE_PIXELS=1 DREAD_TEXTURE_FACTOR=1
export DREAD_RENDER_GEOMETRY=control DREAD_SIMPLIFY_STEPS=0
export DREAD_MERGE_STEPS=0 DREAD_SSF=0 DREAD_OPT_REPORTS=1
export DREAD_WEAPON_DITHER=1 DREAD_GREEN_ACCENT=1
export DREAD_EXTRA_FLAGS="-DDREAD_JOY_VBLANK -DDREAD_COMBAT_12_20 -DDREAD_EASY_MODE -DDREAD_FERRET_RENDERER -DDREAD_FERRET_COLUMN_RLE -DDREAD_SOURCE_PIXELS ${DREAD_FERRET_FLAGS:-}"
# Source-width pixels and collision/PVS caches must never be mixed with old data.
unset DREAD_PREPARED_MAPS
root=$(cd "$(dirname "$0")/../.." && pwd)
bash "$root/tools/build_map.sh" "$1" EPISODE "$2" 'DREAD C7 FERRET WAD PIXELS'
