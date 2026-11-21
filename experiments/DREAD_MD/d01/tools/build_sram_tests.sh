#!/usr/bin/env bash
set -euo pipefail
: "${GDK:?Set GDK to an absolute SGDK path}"
if [[ $# != 2 ]]; then
    echo "Uso: $0 DOOM1.WAD DIRETORIO_SAIDA" >&2
    exit 2
fi
source_dir=$(cd "$(dirname "$0")" && pwd)
wad=$(realpath "$1")
out=$(realpath -m "$2")
mkdir -p "$out"
export DREAD_SRAM_TEST=1 DREAD_COMBAT=1 DREAD_EP_MAPS="1 2 8"
export DREAD_CACHE_MAPS="$out/converted"
unset DREAD_PREPARED_MAPS
for variant in auto-lines control-lines auto-columns control-columns; do
    extra=
    case "$variant" in
        control-lines) extra=-DDREAD_SRAM_CONTROL ;;
        auto-columns) extra=-DSTART_MODE=1 ;;
        control-columns) extra="-DDREAD_SRAM_CONTROL -DSTART_MODE=1" ;;
    esac
    DREAD_EXTRA_FLAGS="$extra" bash "$source_dir/build_map.sh" \
        "$wad" EPISODE "$out/$variant" "D01 SRAM $variant E1M1 E1M2 E1M8" \
        >"$out/$variant.log" 2>&1 || { tail -40 "$out/$variant.log"; exit 1; }
    cp "$out/$variant/EPISODE.bin" "$out/d01-sram-$variant.bin"
    export DREAD_PREPARED_MAPS="$DREAD_CACHE_MAPS"
done
python3 - "$out" <<'ZIP'
from pathlib import Path
import sys, zipfile
out = Path(sys.argv[1])
with zipfile.ZipFile(out / "D01-SRAM-E1M1-E1M2-E1M8.zip", "w", zipfile.ZIP_DEFLATED) as package:
    for path in sorted(out.glob("d01-sram-*.bin")):
        package.write(path, path.name)
ZIP
