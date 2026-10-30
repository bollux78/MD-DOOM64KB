#!/usr/bin/env python3
"""R96 (Claudio) after apply_r95.py: fast wall columns from the seg loop.

Profile R94: R42_DrawPackedWall (clipping + R64A context + colormap->LUT) costs as much as the
R60 asm kernel it calls (10.6% each). From R_RenderSegLoop every wall tier is already clipped to
the crop window (x never a solid/cropped column, yl >= ceilingclip+1, yh <= floorclip-1) and the
colormap is fixed for the seg, so its two composed LUTs (even/odd x) are resolved once per seg.
Per column only the R42 arithmetic that matters remains: frac, byte address, R60 kernel (count>=2)
or the single-nibble write (count==1), byte-identical to R42. Any other colormap (sky mutates it)
or state falls back to R_DrawColumnWall unchanged. BSS +16 B.
"""
from pathlib import Path
import os
name = os.environ.get('R96_NAME', 'wall')

def patch(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))

V = 'src/r22_video.inc'; D = 'src/r_draw.c'
assert 'R95_FlatSetup' in Path(V).read_text(), 'apply_r95.py first'
patch(V, 'void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){',
'''/* R96: per-seg wall setup (NULL = keep R_DrawColumnWall). */
uint8_t *R96_WallSetup(const uint8_t *colormap,const uint8_t **lut)
{
    if(_g_gamestate!=GS_LEVEL || !R57_CROP_ACTIVE) return 0;
    r64a_ctx_t tmp; const r64a_ctx_t *cx=R64A_Get(&tmp);
    lut[0]=R64A_LUT(cx,colormap,0); lut[1]=R64A_LUT(cx,colormap,1);
    if(!lut[0] || !lut[1]) return 0;
    return r22_fb.pixels;
}
void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){''')
patch(D, '#define R20_WALL_DRAW(v) R_DrawColumnWall(v)\n',
'''#include "r60_pair_wall.h"
static uint8_t *r96_fb;
static const uint8_t *r96_lut[2];
static const uint8_t *r96_cmap;
static inline __attribute__((always_inline)) void R96_WallDraw(const draw_column_vars_t *v)
{
    uint8_t *fb = r96_fb;
    if (!fb || v->colormap != r96_cmap) { R_DrawColumnWall(v); return; }
    const int16_t x = v->x, yl = v->yl, yh = v->yh;
    if (yh < yl) return;
    const uint16_t f = (uint16_t)((v->texturemid >> 7) + (yl - CENTERY) * v->fracstep);
    const uint8_t *lut = r96_lut[x & 1];
    uint8_t *dst = fb + (((uint16_t)x >> 1) << 1) + 1u + (((uint16_t)x & 1u) ? 76u : 0u) + ((uint16_t)yl >> 1) * 152u;
    const uint16_t count = (uint16_t)(yh - yl + 1);
    if (count >= 2) { R60_WallDraw(dst, v->source, lut, f, v->fracstep, count, (uint16_t)(yl & 1)); return; }
    const uint8_t c = (uint8_t)(lut[v->source[f >> 9]] & 15u);
    if (yl & 1) *dst = (uint8_t)((*dst & 0xf0u) | c); else *dst = (uint8_t)((*dst & 0x0fu) | (c << 4));
}
#define R20_WALL_DRAW(v) R96_WallDraw(v)
''')
patch(D, '    for ( ; rw_x < rw_stopx ; rw_x++)\n    {\n        R37_HIT(R37_COLUMNS);',
'''    extern uint8_t *R96_WallSetup(const uint8_t *colormap, const uint8_t **lut);
    r96_cmap = dcvars.colormap; r96_fb = R96_WallSetup(r96_cmap, r96_lut);
    for ( ; rw_x < rw_stopx ; rw_x++)
    {
        R37_HIT(R37_COLUMNS);''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r95-'" in s
p.write_text(s.replace("'r95-'", "'r96-'").replace("('flat', 1)", repr((name, 1))))
print('R96 fast seg-loop walls; ROM name r96-%s' % name)
