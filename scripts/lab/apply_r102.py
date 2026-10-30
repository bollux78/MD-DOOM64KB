#!/usr/bin/env python3
"""R102 (Claudio) after apply_r100.py: R102_CANDIDATE=bits.

bits  (a) exact native multiplies for the remaining 32x32 libgcc products in sight / map
          utilities: R102_Mul(a, b) uses the existing exact R47_Mul32x16 (low 32 bits of
          int32 x int16 with MULU/MULS) when one operand fits in int16, else the original
          product. Sites: P_DivlineSide, P_InterceptVector2 (p_sight.c and p_maputl.c),
          P_PointOnDivlineSide (p_maputl.c). The p_sight slope sites stay unchanged.
      (b) the (y>>1)*152 row offset of the R95/R96 inline fills becomes a 44-entry ROM table.
"""
from pathlib import Path
import os, re
cand = os.environ.get('R102_CANDIDATE', 'bits'); assert cand == 'bits'

def patch(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))

h = Path('src/r47_mul.h'); t = h.read_text()
t = t.replace('#endif\n', '''/* R102: exact low 32 bits of int32 x int32; native 16-bit multiplies when one side fits int16. */
static inline int32_t R102_Mul(int32_t a,int32_t b)
{
    if ((int32_t)(int16_t)b == b) return R47_Mul32x16(a,(int16_t)b);
    if ((int32_t)(int16_t)a == a) return R47_Mul32x16(b,(int16_t)a);
    return (int32_t)((uint32_t)a*(uint32_t)b);
}
#endif
''') if t.rstrip().endswith('#endif') else None
assert t; h.write_text(t)
def gate(f, first_line):
    s = Path(f).read_text()
    k = '#if defined(DOOM_R47_MUL_LOGIC)\n' + first_line
    assert s.count(k) == 1, (f, first_line[:60]); s = s.replace(k, '#if 1 /* R102 bits */\n' + first_line)
    Path(f).write_text(s)
for f in ('src/p_sight.c', 'src/p_maputl.c'):
    s = Path(f).read_text()
    s = s.replace('#if defined(DOOM_R47_MUL_LOGIC)\n#include "r47_mul.h"\n#endif', '#include "r47_mul.h"')
    if '#include "r47_mul.h"' not in s.split('#if 1 /* R102')[0]:
        assert s.count('#include "r47_mul.h"') >= 1, f
    Path(f).write_text(s)
gate('src/p_sight.c', '    (right = R47_Mul32x16((y - node->y) >> FRACBITS,(int16_t)(node->dx >> FRACBITS))) <')
gate('src/p_sight.c', '\tfixed_t a = R47_Mul32x16((v1->x - v2->x) >> 8,(int16_t)(v1->dy >> FRACBITS));')
gate('src/p_maputl.c', '    R47_Mul32x16((y - ((fixed_t)line->v1.y<<FRACBITS)) >> 8,line->dx) >=')
gate('src/p_maputl.c', '    R47_Mul32x16(y >> 8,(int16_t)(line->dx >> 16)) >=')
gate('src/p_maputl.c', '\tfixed_t a = R47_Mul32x16((v1->x - v2->x) >> 8,(int16_t)(v1->dy >> FRACBITS));')
for f in ('src/p_sight.c', 'src/p_maputl.c'):
    s = Path(f).read_text()
    # (int16_t)(X >> N) operands become full int32 expressions guarded inside R102_Mul.
    s2, n = re.subn(r'R47_Mul32x16\(([^;]*?),\(int16_t\)\(([^()]*?(?:\([^()]*\))?[^()]*?)\)\)', r'R102_Mul(\1,(\2))', s)
    Path(f).write_text(s2); print(f, 'guarded sites', n)
D = 'src/r_draw.c'
patch(D, '/* R95: same bytes as R_DrawColumnFlat', '''static const uint16_t r102_rowofs[44] = {0,0,152,152,304,304,456,456,608,608,760,760,912,912,1064,1064,1216,1216,1368,1368,1520,1520,1672,1672,1824,1824,1976,1976,2128,2128,2280,2280,2432,2432,2584,2584,2736,2736,2888,2888,3040,3040,3192,3192};
/* R95: same bytes as R_DrawColumnFlat''')
patch(D, '((uint16_t)y0 >> 1) * 152u;', 'r102_rowofs[(uint16_t)y0];')
patch(D, '((uint16_t)yl >> 1) * 152u;', 'r102_rowofs[(uint16_t)yl];')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r100-'" in s and "('f1', 1)" in s
p.write_text(s.replace("'r100-'", "'r102-'").replace("('f1', 1)", "('bits', 1)"))
print('R102 bits')
