#!/usr/bin/env python3
"""R118 (after apply_r117.py lowmem): exact logic speed-ups found by the R117 per-map profile.

R117 profile (R116 base, BlastEm, 10 demos), logic-only samples:
  P_CheckSight 18.5%, P_MobjThinker 12.0%, P_CheckPosition 11.1%, __mulsi3 10.7%,
  R23_MapRead 8.5% + R23_MapWrite 4.6% (SRAM map state), P_SetThingPosition 6.0%, R_PointInSubsector 5.2%.
With rendering, logic is ~25-45% of the frame in the combat maps (E1M3/E1M7/E1M9 worst windows).

R118_MODE:
  mul   - exact native multiplies in logic/BSP side tests (no __mulsi3 calls):
          * enables the existing DOOM_R47_MUL_LOGIC (p_sight.c, p_maputl.c) and DOOM_R47_MUL_BSP (r_draw.c,
            R_PointOnSide -> R_PointInSubsector) paths: low 32 bits of int32 x int16 via MULU/MULS, identical
            to libgcc __mulsi3 (r47_mul.h, checked by scripts/lab/test_r118_mul.py);
          * P_DivlineSide (sight): both factors are (int32 >> 16), always in int16 range -> one MULS.W each.
  vc    - P_CrossSubsector (sight) checks and marks line validcount in ONE SRAM window (R89_VisitLine, already
          used by P_BlockLinesIterator) instead of R23_GET + R23_SET (two windows and the generic dispatch).
          Same semantics: skip if equal, otherwise store; both uint16.
  mulvc - both.
No RAM is added (no BSS/.data). Game logic must be bit-identical: checked by r118_logic_check.py.
"""
import os
from pathlib import Path

mode = os.environ['R118_MODE']; assert mode in ('mul', 'vc', 'mulvc'), mode


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


def prepend(f, text):
    p = Path(f); s = p.read_text(); assert text not in s; p.write_text(text + s)


if 'mul' in mode:
    prepend('src/p_sight.c', '/* R118 mul */\n#define DOOM_R47_MUL_LOGIC 1\n')
    prepend('src/p_maputl.c', '/* R118 mul */\n#define DOOM_R47_MUL_LOGIC 1\n')
    prepend('src/r_draw.c', '/* R118 mul */\n#define DOOM_R47_MUL_BSP 1\n')
    rep('src/p_sight.c', '''    (right = R47_Mul32x16((y - node->y) >> FRACBITS,(int16_t)(node->dx >> FRACBITS))) <
    (left  = R47_Mul32x16((x - node->x) >> FRACBITS,(int16_t)(node->dy >> FRACBITS))) ? 0 :''',
        '''    /* R118: (int32 >> 16) always fits int16, so one MULS.W gives the exact product. */
    (right = R47_Muls16((int16_t)((y - node->y) >> FRACBITS),(int16_t)(node->dx >> FRACBITS))) <
    (left  = R47_Muls16((int16_t)((x - node->x) >> FRACBITS),(int16_t)(node->dy >> FRACBITS))) ? 0 :''')

if 'vc' in mode:
    rep('src/p_sight.c', '''        // allready checked other side?
        if(R23_GET(line,validcount) == validcount)
            continue;

        R23_SET(line,validcount,validcount);
''', '''        // allready checked other side?  R118: test-and-set in one SRAM window.
#if defined(DOOM_R23_MAPMEM)
        if(!R89_VisitLine(line,validcount))
            continue;
#else
        if(R23_GET(line,validcount) == validcount)
            continue;

        R23_SET(line,validcount,validcount);
#endif
''')

p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r117-'" in s and "('meas', 1)" in s
p.write_text(s.replace("'r117-'", "'r118-'").replace("('meas', 1)", "('%s', 1)" % mode))
print('R118', mode)
