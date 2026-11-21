#!/usr/bin/env bash
set -euo pipefail
: "${GDK:?Set GDK to the SGDK directory}"
wad=$(realpath "$1")
out=$(realpath -m "$2")
export DREAD_COMBAT=1
for variant in exact exact-fast exact-vblank; do
    case "$variant" in
        exact) flags='-DDREAD_VALIDATION_TEST -DDREAD_EXACT_SPAN_REFERENCE'; name='DREAD D01 EXATO CONTROLE' ;;
        exact-fast) flags='-DDREAD_VALIDATION_TEST'; name='DREAD D01 EXATO RAPIDO' ;;
        exact-vblank) flags='-DDREAD_VALIDATION_TEST -DDREAD_JOY_VBLANK'; name='DREAD D01 INPUT VBLANK' ;;
    esac
    DREAD_EXTRA_FLAGS="$flags" bash experiments/DREAD_MD/d01/tools/build_map.sh \
        "$wad" EPISODE "$out/$variant" "$name"
done
