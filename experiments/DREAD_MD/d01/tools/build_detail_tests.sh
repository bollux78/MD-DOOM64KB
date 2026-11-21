#!/usr/bin/env bash
set -euo pipefail
# Run from the repository root. Set GDK and pass the shareware WAD and output directory.
: "${GDK:?Set GDK to the SGDK directory}"
wad=$(realpath "$1")
out=$(realpath -m "$2")
export DREAD_COMBAT=1 DREAD_CACHE_MAPS="$out/cache"
for variant in minimal robust table packed full columns; do
    case "$variant" in
        minimal) flags=-DDREAD_HINT_MINIMAL ;;
        robust) flags=-DDREAD_HINT_ROBUST ;;
        table) flags= ;;
        packed) flags=-DDREAD_PACKED_ROWS ;;
        full) flags=-DSTART_MODE=4 ;;
        columns) flags=-DSTART_MODE=1 ;;
    esac
    if [[ -d "$out/cache/E1M9" ]]; then export DREAD_PREPARED_MAPS="$out/cache"; fi
    DREAD_EXTRA_FLAGS="$flags" bash experiments/DREAD_MD/d01/tools/build_map.sh \
        "$wad" EPISODE "$out/$variant" "D01 TEST $variant"
done
