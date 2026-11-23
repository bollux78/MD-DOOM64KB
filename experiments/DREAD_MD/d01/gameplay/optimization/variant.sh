#!/usr/bin/env bash
# Eight A/B variants; called only from dedicated experimental workflow.
set -euo pipefail
if [[ $# != 3 ]]; then
  echo 'Usage: variant.sh CONTROL|AI6|AI4|TEX2|TEX4|GEO_SAFE|GEO_STEPS|ALL WAD OUTPUT' >&2
  exit 2
fi
variant="$1"
export DREAD_OPT_FLAGS='' DREAD_TEXTURE_FACTOR=1 DREAD_RENDER_GEOMETRY=control
export DREAD_SIMPLIFY_STEPS=0 DREAD_OPT_REPORTS=1 DREAD_GREEN_ACCENT=1
case "$variant" in
  CONTROL) ;;
  AI6) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=10" ;;
  AI4) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=15" ;;
  TEX2) export DREAD_TEXTURE_FACTOR=2 ;;
  TEX4) export DREAD_TEXTURE_FACTOR=4 ;;
  GEO_SAFE) export DREAD_RENDER_GEOMETRY=merge ;;
  GEO_STEPS) export DREAD_RENDER_GEOMETRY=merge DREAD_SIMPLIFY_STEPS=1 ;;
  ALL) export DREAD_OPT_FLAGS="-DDREAD_AI_PERIOD=10" DREAD_TEXTURE_FACTOR=2 DREAD_RENDER_GEOMETRY=merge ;;
  *) echo "Unknown experimental variant: $variant" >&2;exit 2 ;;
esac
echo "DREAD OPT $variant: AI_FLAGS=${DREAD_OPT_FLAGS:-12Hz} TEX_FACTOR=$DREAD_TEXTURE_FACTOR GEOMETRY=$DREAD_RENDER_GEOMETRY STEPS=$DREAD_SIMPLIFY_STEPS"
bash "$(dirname "$0")/../build.sh" "$2" "$3"
