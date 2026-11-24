#!/usr/bin/env bash
# Eight A/B variants; called only from dedicated experimental workflow.
set -euo pipefail
if [[ $# != 3 ]]; then
  echo 'Usage: variant.sh CONTROL|AI6|AI6S|GEO_SAFE|ALL|AI4|TEX2|TEX4|GEO_STEPS|GEO_AGGR WAD OUTPUT' >&2
  exit 2
fi
variant="$1"
export DREAD_OPT_FLAGS='' DREAD_TEXTURE_FACTOR=1 DREAD_RENDER_GEOMETRY=control
export DREAD_SIMPLIFY_STEPS=0 DREAD_OPT_REPORTS=1 DREAD_GREEN_ACCENT=1
case "$variant" in
  CONTROL) ;;
  AI6) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=10" ;;
  # AI at 6 Hz with each kind's step lengthened so its average walking speed matches CONTROL (capped at 16 units)
  AI6S) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=10 -DDREAD_AI_SPEED_COMP" ;;
  AI4) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=15" ;;
  TEX2) export DREAD_TEXTURE_FACTOR=2 ;;
  TEX4) export DREAD_TEXTURE_FACTOR=4 ;;
  GEO_SAFE) export DREAD_RENDER_GEOMETRY=merge ;;
  GEO_STEPS) export DREAD_RENDER_GEOMETRY=merge DREAD_SIMPLIFY_STEPS=1 ;;
  # aggressive map simplification (changes collision and looks): loose step merge, narrow door protection, near-collinear walls
  GEO_AGGR) export DREAD_RENDER_GEOMETRY=merge DREAD_MERGE_STEPS=24 DREAD_MERGE_FLATS=1 DREAD_MERGE_LOOSE=1 DREAD_MERGE_CEIL=64 DREAD_NARROW_PROTECT=1 DREAD_JOIN_TOL=16 ;;
  # conservative combination: speed-compensated 6 Hz AI + verified geometry reduction. TEX2/TEX4/GEO_STEPS are not in
  # the default round (see README): TEX does not shrink the data the scalers read, GEO_STEPS changes collisions.
  ALL) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=10 -DDREAD_AI_SPEED_COMP" DREAD_RENDER_GEOMETRY=merge ;;
  *) echo "Unknown experimental variant: $variant" >&2;exit 2 ;;
esac
# Every experimental ROM must identify its optimization in the game's ROM
# field, the Sega header, and the DEMO3 results screen.
case "$variant" in
  CONTROL) export DREAD_ROM_LABEL="DREAD C7 CONTROL AI 12HZ" ;;
  AI6)     export DREAD_ROM_LABEL="DREAD C7 AI6 AI 6HZ" ;;
  AI6S)    export DREAD_ROM_LABEL="DREAD C7 AI6S AI 6HZ COMP" ;;
  *)       export DREAD_ROM_LABEL="DREAD C7 $variant EXPERIMENT" ;;
esac
export DREAD_OPT_FLAGS="$DREAD_OPT_FLAGS -DDREAD_BENCH_$variant"
echo "DREAD OPT $variant ROM_NAME=$DREAD_ROM_LABEL: AI_FLAGS=${DREAD_OPT_FLAGS:-12Hz} TEX_FACTOR=$DREAD_TEXTURE_FACTOR GEOMETRY=$DREAD_RENDER_GEOMETRY STEPS=$DREAD_SIMPLIFY_STEPS"
bash "$(dirname "$0")/../build.sh" "$2" "$3"
