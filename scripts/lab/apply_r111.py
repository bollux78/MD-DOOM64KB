#!/usr/bin/env python3
"""R111 colsrc (after the R107 direct chain): per-column wall source without the function call.

R110 profile: R_DrawSegTextureColumn ~10% of frame time, mostly call overhead (9-register MOVEM,
argument reloads, R_GetColumn, lump lookup) around a 3-line lookup. The two common cases are now
resolved inline in the seg loop from the R84 ROM tables already in the build:
  - single-patch, non-overlapped texture: lump + r84_simple_offsets[col & mask] (== columnofs+3);
  - composite with a baked column: r84_pixels + r84_offsets[...] with the R107 bookkeeping.
Everything else still calls R_DrawSegTextureColumn. Same source pointers -> identical pixels.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


rep('src/r_draw.c', '''#else
#define R20_WALLCOL(w, tex, texture, col, dc) R_DrawSegTextureColumn((tex), (texture), (col), (dc))
#endif''', '''#else
static inline __attribute__((always_inline)) void R111_WallCol(const texture_t __far* tex, int16_t texture,
                                                               int16_t texcolumn, draw_column_vars_t* dc)
{
    const int16_t pn = r84_patches[texture];
    if (pn >= 0) {
        const uint16_t xc = (uint16_t)texcolumn & tex->widthmask;
        dc->source = (const byte __far*)W_GetLumpByNum(pn) + r84_simple_offsets[r84_simple_starts[texture] + xc];
        R20_WALL_DRAW(dc);
        return;
    }
    if (tex->overlapped) {
        const uint16_t xc = ((uint16_t)texcolumn & 0xfffcu) & tex->widthmask;
        const uint32_t baked = r84_offsets[r84_starts[texture] + (xc >> 2)];
        if (baked != 0xffffffffUL) {
            r89_rom_pending = r84_pixels + baked;   /* same bookkeeping as R107 */
            r39c_tmpValid = 0;
            dc->source = r89_rom_pending;
            R20_WALL_DRAW(dc);
            return;
        }
    }
    R_DrawSegTextureColumn(tex, texture, texcolumn, dc);
}
#define R20_WALLCOL(w, tex, texture, col, dc) R111_WallCol((tex), (texture), (col), (dc))
#endif''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r107-'" in s and "('direct', 1)" in s
p.write_text(s.replace("'r107-'", "'r111-'").replace("('direct', 1)", "('colsrc', 1)"))
print('R111 colsrc')
