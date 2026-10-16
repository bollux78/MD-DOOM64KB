#!/usr/bin/env python3
"""R17 arithmetic equivalence and source preflight (not 68000 execution)."""
from pathlib import Path
from random import Random

video = Path("src/i_genesisv.c").read_text()
build = Path("scripts/build_silent.fish").read_text()
matrix = Path("scripts/lab/build_r17_pixel_loop.fish").read_text()
assert "DOOM_R17_PIXEL_DBRA" in video
assert "DOOM_R17_FRAC_MULU" in video
assert '"dbra %[n],1b"' in video
assert '"move.b (%[s],%[i].w),%[i]\\n\\t"' in video
assert '"move.w (%[m],%[i].w),(%[d])\\n\\t"' in video
assert "uint16_t loopcount = (uint16_t)count" in video
assert "return;\n#elif defined(DOOM_R8_LUT_UNROLL)" in video
assert "DOOM_R17_PIXEL_DBRA requires DOOM_CELL_LUT=1" in build
assert "DOOM_R17_FRAC_MULU" in build
assert "DOOM_R16_HUD_UP2 1" in matrix
assert "DOOM_R16_WEAPON_LIFT 1" in matrix
assert "DOOM_R15_SETUPMUL 1" in matrix
assert "for variant in control fracmul dbra combined" in matrix
assert "DOOM_R13_MUL_DECOMP" not in video
assert "DOOM_R14_CLIPSCAN" not in video

rng = Random(0x6800017)
steps = [0,1,2,7,127,255,256,511,512,1023,4095,16383,32767,32768,65534,65535]
deltas = [-128,-65,-32,-16,-11,-1,0,1,11,16,32,65,127]
for delta in deltas:
    for step in range(65536):
        original = (delta * step) & 0xffff
        mulu_word = ((delta & 0xffff) * step) & 0xffff
        assert original == mulu_word, (delta,step)
print(f"PASS: {len(deltas)*65536:,} initial-frac MULU.W products match low16")

for k in range(20000):
    step = rng.choice(steps) if k % 2 else rng.randrange(65536)
    texturemid = rng.randrange(-(1<<31),1<<31)
    yl = rng.randrange(1,22)
    centery = 11
    count = rng.randrange(1,23-yl)
    source = [rng.randrange(256) for _ in range(128)]
    cellmap = [rng.randrange(65536) for _ in range(256)]
    base = (texturemid >> 7) + (yl-centery)*step
    frac_c = base & 0xffff
    frac_asm = ((texturemid >> 7) + ((yl-centery)&0xffff)*step) & 0xffff
    pixels_c = []
    pixels_asm = []
    for _ in range(count):
        pixels_c.append(cellmap[source[frac_c >> 9]])
        index = frac_asm >> 9
        texel = source[index]
        byte_offset = (texel & 255) * 2
        pixels_asm.append(cellmap[byte_offset//2])
        frac_c = (frac_c + step) & 0xffff
        frac_asm = (frac_asm + step) & 0xffff
    assert pixels_c == pixels_asm, k
    assert frac_c == frac_asm, k
print("PASS: 20,000 randomized 1..22-row pixel columns; C and DBRA arithmetic match")
print("PASS: R17 source/flags preflight; R16 hand1 base preserved")
