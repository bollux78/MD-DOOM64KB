#!/usr/bin/env python3
"""R95 (Claudio) after apply_r92.py (toggle): fast flat columns inside the seg loop.

Profile R94 (R92 toggle PERF, DEMO3): R_DrawColumnFlat = 9.9% of the time, of which the fill loop
is ~0.6%; the rest is per-call overhead (5 stacked args, R64A context, crop clipping, LUT lookup).
Inside R_RenderSegLoop every flat column is already clipped to the crop window by construction:
x is never a solid (cropped) column, top >= ceilingclip+1 >= R57_YMIN and bottom <= floorclip-1
<= R57_YEND-1, top <= bottom. The flat colour is constant for the whole seg, so its two nibble
samples (even/odd x) are looked up once per seg. The column fill writes exactly the same bytes as
R_DrawColumnFlat (Pair-V, no R72 2D flats): odd first row -> low nibble, pairs -> both nibbles,
trailing even row -> high nibble. Sky columns and every other caller keep R_DrawColumnFlat.
Gate: only in GS_LEVEL with the R57 crop active (always true during gameplay in this build).
"""
from pathlib import Path
import os
name = os.environ.get('R95_NAME', 'flat')

def patch(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))

V = 'src/r22_video.inc'; D = 'src/r_draw.c'
s = Path(V).read_text()
assert '#define R72' not in s or True
patch(V, 'void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){',
'''#if defined(DOOM_R72_FLAT_2D)
#error R95 fast flats assume one sample per flat column (no R72 2D flats)
#endif
/* R95: per-seg setup for the inlined flat fill of R_RenderSegLoop. Returns the framebuffer
 * base (NULL = use R_DrawColumnFlat) and the two flat LUTs of the current frame/profile. */
uint8_t *R95_FlatSetup(const uint8_t **lut)
{
    if(_g_gamestate!=GS_LEVEL || !R57_CROP_ACTIVE) return 0;
    r64a_ctx_t tmp; const r64a_ctx_t *cx=R64A_Get(&tmp);
    lut[0]=cx->flat[0]; lut[1]=cx->flat[1];
    return r22_fb.pixels;
}
void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){''')

patch(D, '    for ( ; rw_x < rw_stopx ; rw_x++)\n    {\n        R37_HIT(R37_COLUMNS);',
'''    /* R95: flat samples are constant for the seg (colour fixed, LUT per frame). */
    extern uint8_t *R95_FlatSetup(const uint8_t **lut);
    const uint8_t *r95_lut[2];
    uint8_t *const r95_fb = R95_FlatSetup(r95_lut);
    uint8_t r95_cs0 = 0, r95_cs1 = 0, r95_fs0 = 0, r95_fs1 = 0;
    if (r95_fb) {
        r95_cs0 = r95_lut[0][(uint8_t)ceilingplane_color] & 15u; r95_cs1 = r95_lut[1][(uint8_t)ceilingplane_color] & 15u;
        r95_fs0 = r95_lut[0][(uint8_t)floorplane_color] & 15u;   r95_fs1 = r95_lut[1][(uint8_t)floorplane_color] & 15u;
    }
    for ( ; rw_x < rw_stopx ; rw_x++)
    {
        R37_HIT(R37_COLUMNS);''')
patch(D, '                    R_DrawColumnFlat(ceilingplane_color, &dcvars);',
'''                    if (r95_fb) R95_Fill(r95_fb, rw_x, top, bottom, (rw_x & 1) ? r95_cs1 : r95_cs0);
                    else R_DrawColumnFlat(ceilingplane_color, &dcvars);''')
patch(D, '                R_DrawColumnFlat(floorplane_color, &dcvars);',
'''                if (r95_fb) R95_Fill(r95_fb, rw_x, top, bottom, (rw_x & 1) ? r95_fs1 : r95_fs0);
                else R_DrawColumnFlat(floorplane_color, &dcvars);''')
# the fill itself, before the seg loop function (file scope, after includes)
patch(D, 'static int16_t floorclip[VIEWWINDOWWIDTH];',
'''/* R95: same bytes as R_DrawColumnFlat (Pair-V, 152-byte pair rows, A/B low bytes). */
static inline __attribute__((always_inline)) void R95_Fill(uint8_t *fb, int16_t x, int16_t y0, int16_t y1, uint8_t s)
{
    uint8_t *dst = fb + (((uint16_t)x >> 1) << 1) + 1u + (((uint16_t)x & 1u) ? 76u : 0u) + ((uint16_t)y0 >> 1) * 152u;
    uint16_t count = (uint16_t)(y1 - y0 + 1);
    if (y0 & 1) { *dst = (uint8_t)((*dst & 0xf0u) | s); dst += 152; --count; }
    const uint8_t both = (uint8_t)((s << 4) | s);
    for (uint16_t n = count >> 1; n; --n) { *dst = both; dst += 152; }
    if (count & 1u) *dst = (uint8_t)((*dst & 0x0fu) | (s << 4));
}
static int16_t floorclip[VIEWWINDOWWIDTH];''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r92-'" in s and "('toggle', 1)" in s
p.write_text(s.replace("'r92-'", "'r95-'").replace("('toggle', 1)", repr((name, 1))))
print('R95 fast seg-loop flats; ROM name r95-%s' % name)
