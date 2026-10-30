#!/usr/bin/env python3
"""R99 (Claudio) after apply_r98.py (R98_CANDIDATE=sprmul): three independent test candidates.

texsplit  R_DrawSegTextureColumn (10.8% in R99 profile, ~2% of it MOVEM save/restore): the
          overlapped (multi-patch composite) branch moves into a noinline helper, so the common
          single-patch path no longer carries R_ComposeColumn's register pressure.
angcache  R_AddLine: consecutive segs share a vertex (v2 of seg i == v1 of seg i+1). The last
          vertex/angle is cached for the current frame (reset in R_ClearClipSegs). Exact.
recip     FixedReciprocal/FixedReciprocalBig (0xffffffff/v): for v >= 65536 the libgcc
          __udivsi3 shift loop (L4, ~1% of the profile) is replaced by a computed shift with the
          same normalisation, DIVU and single correction; host-tested equal to C division.
"""
from pathlib import Path
import os, shutil
cand = os.environ['R99_CANDIDATE']; assert cand in ('texsplit', 'angcache', 'recip')

def patch(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))

D = 'src/r_draw.c'
assert 'R98 sprmul' in Path(D).read_text(), 'apply_r98.py sprmul first'
if cand == 'texsplit':
    patch(D, '''    else
    {
        dcvars->source = R7_VALUE(7, R_ComposeColumn(texture, tex, texcolumn
#if defined(DOOM_R20_COMPOSITE_HOIST)
            , prepared
#endif
        ));
        /* P4 profile attribution: multipatch composition is bucket 7;
         * the subsequent actual wall write belongs to bucket 6, as in
         * the non-overlapped case. R7_VOID is inert in clean builds. */
        R7_VOID(6, R20_WALL_DRAW(dcvars));
    }
}''', '''    else
        R99_DrawComposite(tex, texture, texcolumn, dcvars);
}''')
    patch(D, 'static void R_DrawSegTextureColumn(const texture_t __far* tex, int16_t texture, int16_t texcolumn, draw_column_vars_t* dcvars\n',
'''#if defined(DOOM_R20_COMPOSITE_HOIST)
#error R99 texsplit assumes no R20 composite hoist
#endif
/* R99 texsplit: rare multi-patch composite path kept out of the hot single-patch function. */
static void __attribute__((noinline)) R99_DrawComposite(const texture_t __far* tex, int16_t texture, int16_t texcolumn, draw_column_vars_t* dcvars)
{
    dcvars->source = R7_VALUE(7, R_ComposeColumn(texture, tex, texcolumn));
    R7_VOID(6, R20_WALL_DRAW(dcvars));
}
static void R_DrawSegTextureColumn(const texture_t __far* tex, int16_t texture, int16_t texcolumn, draw_column_vars_t* dcvars
''')
elif cand == 'angcache':
    patch(D, '''    angle16_t angle1 = R_PointToAngle16(line->v1.x, line->v1.y);
    angle16_t angle2 = R_PointToAngle16(line->v2.x, line->v2.y);''',
'''    /* R99 angcache: v1 of this seg is usually v2 of the previous one (same frame, same view). */
    angle16_t angle1 = (r99_ac.valid && r99_ac.x == line->v1.x && r99_ac.y == line->v1.y)
                       ? r99_ac.a : R_PointToAngle16(line->v1.x, line->v1.y);
    angle16_t angle2 = R_PointToAngle16(line->v2.x, line->v2.y);
    r99_ac.x = line->v2.x; r99_ac.y = line->v2.y; r99_ac.a = angle2; r99_ac.valid = 1;''')
    patch(D, 'static void R_AddLine(const seg_t __far* line)\n{',
'''static struct { int16_t x, y; angle16_t a; uint8_t valid; } r99_ac;
static void R_AddLine(const seg_t __far* line)
{''')
    patch(D, 'static void R_ClearClipSegs (void)\n{', 'static void R_ClearClipSegs (void)\n{\n    r99_ac.valid = 0;   /* R99: new frame, new view */')
else:
    shutil.copyfile('scripts/lab/r99/r99_recip.h', 'src/r99_recip.h')
    patch('src/m_fixed.h', '''#define FixedReciprocal(v)      (0xffffffffu/(v))
#define FixedReciprocalBig(v)   (0xffffffffu/(v))''', '''#include "r99_recip.h"
#define FixedReciprocal(v)      R99_Recip((uint32_t)(v))
#define FixedReciprocalBig(v)   R99_Recip((uint32_t)(v))''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r98-'" in s and "('sprmul', 1)" in s
p.write_text(s.replace("'r98-'", "'r99-'").replace("('sprmul', 1)", repr((cand, 1))))
print('R99', cand)
