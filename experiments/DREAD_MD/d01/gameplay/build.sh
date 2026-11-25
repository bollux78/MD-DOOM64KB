#!/usr/bin/env bash
set -euo pipefail
: "${GDK:?Set GDK to SGDK}"
wad=$(realpath "$1")
out=$(realpath -m "$2")
root=$(cd "$(dirname "$0")/.." && pwd)
# Existing prepared episode caches may carry C6/medium THINGS and sprites.
# Until a skill-tagged cache format is added, regenerate the C7 easy maps.
if [[ -n ${DREAD_PREPARED_MAPS:-} ]]; then
    echo "C7 easy: unset DREAD_PREPARED_MAPS; old caches can contain medium enemies." >&2
    exit 2
fi
export DREAD_COMBAT=1 DREAD_GAMEPLAY=1 DREAD_SKILL=easy
# C7 original WAD weapons (C5), with optional colour diffusion in PAL1.
# DREAD_WEAPON_DITHER=0 restores exactly the C5 nearest-colour palette mapping.
export DREAD_WEAPON_DITHER="${DREAD_WEAPON_DITHER:-1}"
# Exact E1 SSF chromatic green 0x4C4 only in Baron ball and NUKEDGE wall trims.
# All other former gray-12 uses are remapped to the remaining grays offline.
export DREAD_GREEN_ACCENT="${DREAD_GREEN_ACCENT:-1}"
# Grates are drawn at full resolution by default (2x2 half resolution gave no measurable gain).
# DREAD_GRATE_HALF_RES=1 restores the 2x2 mode; DREAD_GRATE_OLD=1 draws grates with the old per-row coverage test
# instead of the opaque-run loop (A/B baseline).
grate_flags=""
if [[ ${DREAD_GRATE_HALF_RES:-0} == 1 ]]; then
    grate_flags="-DDREAD_GRATE_HALF_RES"
fi
if [[ ${DREAD_GRATE_OLD:-0} == 1 ]]; then
    grate_flags="$grate_flags -DDREAD_GRATE_OLD"
fi
DREAD_EXTRA_FLAGS="-DDREAD_JOY_VBLANK -DDREAD_NATIVE_PERSPECTIVE -DDREAD_CELLSTREAM_REPORT -DDREAD_COMBAT_12_20 -DDREAD_EASY_MODE $grate_flags ${DREAD_OPT_FLAGS:-}" \
    bash "$root/tools/build_map.sh" "$wad" EPISODE "$out" "${DREAD_ROM_LABEL:-DREAD GAMEPLAY C7 EASY}"
