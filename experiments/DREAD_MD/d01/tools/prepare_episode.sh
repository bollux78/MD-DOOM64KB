#!/usr/bin/env bash
# Generate the complete, palette-consistent E1M1..E1M9 resource cache once.
# Usage: bash prepare_episode.sh DOOM1.WAD OUTDIR
# Only ROM-neutral map data belongs here. Never publish the source WAD.
set -euo pipefail
[[ $# == 2 ]] || { echo "usage: $0 WAD OUTDIR" >&2; exit 2; }
D=$(cd "$(dirname "$0")/.." && pwd)
wad=$(realpath "$1")
out=$(realpath -m "$2")
[[ -f "$wad" ]] || exit 2
mkdir -p "$out"
if [[ -f "$out/.complete" ]]; then
    echo "Prepared maps reused: $out"
    exit 0
fi
tmp=$(mktemp -d "${out}.tmp.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT
export OPENBLAS_NUM_THREADS=1
samples=()
for n in {1..9}; do
    python3 "$D/tools/conv.py" "$wad" "E1M$n" "$tmp" --row-only \
      --collect-items "$tmp/E1M$n.npz" >/dev/null
    samples+=("$tmp/E1M$n.npz")
done
python3 "$D/tools/conv.py" "$wad" E1M1 "$tmp" --row-only \
    --fit-from "${samples[@]}" --palette-out "$tmp/palette.json"
for n in {1..9}; do
    level="$tmp/E1M$n"
    python3 "$D/tools/conv.py" "$wad" "E1M$n" "$level" \
      --row-only --tex-pad 32 --palette "$tmp/palette.json"
    cc -O2 -DPVS_GEN -DDREAD_ROW_ONLY -I"$level" -I"$D/src" \
      -o "$level/pvsgen" "$D/tools/pvsgen.c" "$D/src/render.c" "$level/mapdata.c"
    "$level/pvsgen" "$level/pvs.c"
    rm -f "$level/pvsgen"
done
# Move into the requested cache only after ALL 9 maps have finished.
for n in {1..9}; do
    rm -rf "$out/E1M$n"
    mv "$tmp/E1M$n" "$out/E1M$n"
done
cp "$tmp/palette.json" "$out/palette.json"
printf '%s\n' "Complete episode resources; generated from local WAD; no WAD in cache." > "$out/.complete"
echo "Episode cache ready: $out"
