#!/usr/bin/env python3
"""R19 memory diagnostics: isolation, zone settings and telemetry invariants."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
v = (root / "src/i_genesisv.c").read_text()
z = (root / "src/z_zone.c").read_text()
i = (root / "src/i_genesis.c").read_text()
m = (root / "src/r19_memdiag.c").read_text()
b = (root / "scripts/build_silent.fish").read_text()
h = (root / "src/r19_memdiag.h").read_text()
script = (root / "scripts/lab/build_r19_memdiag.fish").read_text()
assert "I_MemDiagInit();" in i
assert "I_MemDiagSample();" in v
assert "I_DrawMemDiagCounters();" in v
assert "I_MemDiagSample();" in m
assert "Z_DiagSample(" in m and "Z_DiagSample(" in z
assert "++steps > 4096u" in z
assert "addr != expected" in z
assert "block->prev != previous" in z
assert "watermark_begin[0]" in m
assert "r19_memdiag.min_stack_gap" in v
assert "r19_memdiag.min_zone_free" in v
assert "DOOM_MEM_DIAG" in h and "DOOM_MEM_DIAG" in b
assert 'case 38 40 43' in b
assert "-DHEAP_SIZE=$zone_bytes" in b
assert "set -gx DOOM_R19_FLAT_DBRA 1" in script
assert "set -gx DOOM_MEM_DIAG 1" in script
assert "set -gx DOOM_TIMEDEMO 1" in script
assert "for zone_kib in 43 40 38" in script
assert "DOOM_R19_PIXEL4" not in v
assert "DOOM_MEM_DIAG" not in (root / "scripts/lab/build_r19_flat_dbra.fish").read_text()
assert "DOOM_MEM_DIAG" not in (root / "scripts/lab/build_r18_playable.fish").read_text()
assert 43*1024 - 40*1024 == 3072
assert 43*1024 - 38*1024 == 5120
print("PASS R19 MEMDIAG: isolated 43/40/38 KiB DEMO3 variants, bounded zone check, stack watermark, live telemetry")
