#!/usr/bin/env python3
"""Candidate hook, called after apply_r79.py in a disposable checkout.

R80-P1 (Claudio): ROM offset tables for the Pair-V destination byte of the
wall glue (R42_DrawPackedWall) and of R_DrawColumnFlat.

Why (R79 control ELF, doom-md-r60-r79-base-pf.elf): both setups compute
R22_PixelByte(p,x,y) = p+(y>>1)*152+(x&1)*76+(x>>1)*2+1 with two MULU.W
(#$4c and #$98) plus zero extensions, once per drawn column.  Two 16-bit ROM
lookups (column offset by x, row offset by y) give the same pointer.

Scope: only those two call sites.  Sprites and every other R22_PixelByte user
are untouched.  If the Pair-V layout macros are not active, the macro falls
back to the original R22_PixelByte, so the fallback path is the old code.
The address is identical for every valid (x,y): checked on the host by
scripts/lab/test_r80_pixofs.py (all 76x44 coordinates, both formulas compiled).
Tables: 44 + 76 uint16 = 240 bytes of ROM, 0 bytes of WRAM/BSS.

R80-F1 (Claudio): the R_DrawColumnFlat pair fill as a DBRA loop (see apply_f1).
Select with R80_EXPERIMENTS="P1", "F1" or "P1+F1" (default P1). Each experiment
has its own unique anchor and refuses to apply twice.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
W, H = 76, 44


def tables():
    row = [(y >> 1) * 152 for y in range(H)]
    col = [(x & 1) * 76 + (x >> 1) * 2 + 1 for x in range(W)]
    return row, col


def block():
    row, col = tables()
    assert max(row) + max(col) == 3343
    return (
        "/* R80-P1 (Claudio): ROM offset tables for the Pair-V destination byte.\n"
        " * Same pointer as R22_PixelByte for every 0<=x<76, 0<=y<44; removes the two\n"
        " * MULU.W of the wall/flat column setup. 240 bytes of ROM, no WRAM. */\n"
        "#define DOOM_R80_PIXOFS 1\n"
        "#if defined(DOOM_R47_PLANE_PAIR) && defined(DOOM_R48_PAIR_V)\n"
        "_Static_assert(R22_W == 76 && R22_H == 44, \"R80-P1 tables assume 76x44 Pair-V\");\n"
        "static const uint16_t r80_row_ofs[R22_H] = {" + ",".join(map(str, row)) + "};\n"
        "static const uint16_t r80_col_ofs[R22_W] = {" + ",".join(map(str, col)) + "};\n"
        "#define R80_PIXEL_BYTE(p,x,y) ((p) + r80_col_ofs[(uint16_t)(x)] + r80_row_ofs[(uint16_t)(y)])\n"
        "#else\n"
        "#define R80_PIXEL_BYTE(p,x,y) R22_PixelByte((p),(uint16_t)(x),(uint16_t)(y))\n"
        "#endif\n\n")


ANCHOR = "static void R42_DrawPackedWall(const draw_column_vars_t *v)\n"
WALL_OLD = ("    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)first);\n"
            "    int16_t remaining=(int16_t)(y1-first+1);\n")
WALL_NEW = ("    uint8_t *dst=R80_PIXEL_BYTE(r22_fb.pixels,x,first);\n"
            "    int16_t remaining=(int16_t)(y1-first+1);\n")
FLAT_OLD = "    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)y0);\n"
FLAT_NEW = "    uint8_t *dst=R80_PIXEL_BYTE(r22_fb.pixels,x,y0);\n"


FLAT_LOOP_OLD = """    while(count>=2) {
        *dst=pair;
#if defined(DOOM_R49_COLORMIX)
        dst[-1]=R49_TileAttr(gate?3u:0u);
#endif
        dst+=152; count-=2;
    }
"""
# R80-F1: GCC turns the loop above into an end-pointer compare whose limit and the
# post-loop pointer are computed with MULU.W #$98 (blocks @f1c8/@f1f0 of the R79
# control).  DBRA writes the same bytes at the same addresses and leaves dst exactly
# where the C loop leaves it (first byte after the last pair); count keeps its parity.
FLAT_LOOP_NEW = """#if !defined(DOOM_R49_COLORMIX)
    /* R80-F1 (Claudio): same writes as the C loop, counted with DBRA (no MULU). */
    {
        uint16_t pairs=(uint16_t)(count>>1);
        if(pairs){
            --pairs;
            __asm__ volatile(
                "1:\n\t"
                "move.b %[v],(%[d])\n\t"
                "lea 152(%[d]),%[d]\n\t"
                "dbra %[n],1b"
                : [d] "+a" (dst), [n] "+d" (pairs)
                : [v] "d" (pair)
                : "memory", "cc");
        }
        count&=1u;
    }
#else
""" + FLAT_LOOP_OLD + "#endif\n"


def apply_f1(s):
    assert "R80-F1" not in s, "R80-F1 already applied"
    assert s.count(FLAT_LOOP_OLD) == 1, "R80-F1 anchor not unique"
    flat_fn = s.index("void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){")
    assert s.index(FLAT_LOOP_OLD) > flat_fn
    return s.replace(FLAT_LOOP_OLD, FLAT_LOOP_NEW)


def apply_text(s):
    assert "DOOM_R80_PIXOFS" not in s, "R80-P1 already applied"
    for old in (ANCHOR, WALL_OLD, FLAT_OLD):
        assert s.count(old) == 1, ("R80-P1 anchor not unique", old)
    # The wall site must be inside R42_DrawPackedWall and the flat site inside R_DrawColumnFlat.
    wall_fn = s.index(ANCHOR)
    flat_fn = s.index("void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){")
    assert wall_fn < s.index(WALL_OLD) < flat_fn < s.index(FLAT_OLD)
    s = s.replace(ANCHOR, block() + ANCHOR)
    s = s.replace(WALL_OLD, WALL_NEW).replace(FLAT_OLD, FLAT_NEW)
    return s


EXPERIMENTS = {"P1": apply_text, "F1": apply_f1}
DEFAULT = "P1"


def main():
    import os
    chosen = [x for x in os.environ.get("R80_EXPERIMENTS", DEFAULT).replace("+", " ").split() if x]
    assert chosen and all(x in EXPERIMENTS for x in chosen) and len(set(chosen)) == len(chosen), chosen
    p = ROOT / "src/r22_video.inc"
    s = p.read_text()
    assert "R79_PAL0" in s, "R80 hook must run after the R79 chain"
    for x in chosen:
        s = EXPERIMENTS[x](s)
    p.write_text(s)
    print("R80 candidate applied:", "+".join(chosen),
          "(P1: Pair-V offset tables, 240 B ROM; F1: DBRA flat fill; 0 B WRAM)")


if __name__ == "__main__":
    sys.exit(main())
