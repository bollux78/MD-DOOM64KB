#!/usr/bin/env python3
"""R107 direct (after the R105 twoface chain): pre-composed wall columns are read straight from ROM.

R84 already bakes every multi-patch column that composes to a fixed 128-byte column (r84_pixels).
On a cache HIT the renderer already returns the ROM pointer; on a MISS it still copied the baked
column into tmpCache and then into the SRAM column cache (one SRAM window, 32 MOVEP.L).
Here a baked column always returns the ROM pointer. The logical content of tmpCache is kept
exactly as before through r89_rom_pending (the R89 lazy copy), so the tail history that
non-baked partial columns depend on is unchanged: pixels must be identical (checked by the A/B).
Only cache-slot occupancy changes (baked columns no longer evict SRAM slots).
"""
from pathlib import Path

def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))

a = """#if defined(DOOM_R39C_REUSE_CACHE) && !defined(DOOM_SRAM_HOT_SLOTS)
    if(r39c_tmpValid && r39c_tmpEntry==CACHE_ENTRY(xc,texture)) {"""
rep('src/r_draw.c', a, """    {   /* R107: baked columns never go through tmpCache or the SRAM cache. */
        const uint32_t r107_baked = r84_offsets[r84_starts[texture] + ((uint16_t)xc >> 2)];
        if (r107_baked != 0xffffffffUL) {
            r89_rom_pending = r84_pixels + r107_baked;   /* logical tmpCache content, as before */
            r39c_tmpValid = 0;
            return r89_rom_pending;
        }
    }
""" + a)
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r105-'" in s and "('twoface', 1)" in s
p.write_text(s.replace("'r105-'", "'r107-'").replace("('twoface', 1)", "('direct', 1)"))
print('R107 direct baked columns')
