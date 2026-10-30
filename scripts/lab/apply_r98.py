#!/usr/bin/env python3
"""R98 (Claudio) after apply_r97.py: three independent test candidates (R98_CANDIDATE).

texcol    -DDOOM_R20_WALL_HOIST: single-patch, non-overlapped wall textures resolve the patch once per
          seg (R20_PrepareWallSource) instead of R_GetColumn + W_GetLumpByNum + call per column.
          Same column address as R_GetColumn for patchcount==1. BSS +~24 B.
sprmul    R_DrawMaskedColumn: spryscale * topdelta/length (32x8, two __mulsi3 calls per post)
          computed with two MULU.W, exact modulo 2^32 like the original product.
segsplit  R_RenderSegLoop marked noinline: LTO currently merges it into R_Subsector (24% of the
          profile, heavy stack spills). Probe whether separate register allocation helps; pure
          compiler change, same semantics.
"""
from pathlib import Path
import os
cand = os.environ['R98_CANDIDATE']; assert cand in ('texcol', 'sprmul', 'segsplit')
names = {'texcol': 'texcol', 'sprmul': 'sprmul', 'segsplit': 'segsplit'}

def patch(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))

D = 'src/r_draw.c'
assert 'R97_ShadowJoint' in Path('src/r92_shadow.inc').read_text(), 'apply_r97.py first'
if cand == 'texcol':
    patch(D, '#include <stdint.h>\n#include "r84_columns.h"', '#include <stdint.h>\n#define DOOM_R20_WALL_HOIST 1 /* R98 texcol */\n#include "r84_columns.h"')
elif cand == 'sprmul':
    patch(D, '''        const int32_t topscreen = sprtopscreen + spryscale*column->topdelta;
        const int32_t bottomscreen = topscreen + spryscale*column->length;''',
'''        /* R98 sprmul: 32x8 products with two MULU.W, exact modulo 2^32. */
        const uint32_t r98_s = (uint32_t)spryscale;
        const uint16_t r98_lo = (uint16_t)r98_s, r98_hi = (uint16_t)(r98_s >> 16);
        const uint16_t r98_td = column->topdelta, r98_ln = column->length;
        const int32_t topscreen = (int32_t)((uint32_t)sprtopscreen + (uint32_t)r98_lo * r98_td + (((uint32_t)r98_hi * r98_td) << 16));
        const int32_t bottomscreen = (int32_t)((uint32_t)topscreen + (uint32_t)r98_lo * r98_ln + (((uint32_t)r98_hi * r98_ln) << 16));''')
else:
    patch(D, 'static void R_RenderSegLoop(int16_t rw_x, boolean segtextured, boolean markfloor, boolean markceiling)',
             'static void __attribute__((noinline)) R_RenderSegLoop(int16_t rw_x, boolean segtextured, boolean markfloor, boolean markceiling)')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r97-'" in s
p.write_text(s.replace("'r97-'", "'r98-'").replace("('shasm', 1)", repr((names[cand], 1))))
print('R98', cand)
