#!/usr/bin/env python3
"""R123 (after apply_r122.py layout): exact speed-ups chosen from the R121 E1M7 profile (run 41754556915).

R121 findings (R119 both, BlastEm, pinned 68000 divider):
  - The E1M7/E1M3 minimum windows are single-frame spikes (E1M7 tic 296: 60 VBlanks vs median 20;
    tic 424: 57; E1M3 tic 305: 51). Inside them: P_PathTraverse, PIT_AddThingIntercepts,
    PIT_AddLineIntercepts, P_PointOnDivlineSide, P_BlockLinesIterator = hitscan fire (pistol, shotgun,
    chaingun; player and zombies/sergeants), plus the normal render.
  - Logic hot spots: P_CheckSight 23%, P_CheckPosition 14.5%, P_SetThingPosition 12.5%, P_MobjThinker 8.9%.
    The instruction right after each SRAM window (move.w d0,sr) collects ~9% of logic samples (VBlanks
    delayed by the masked window), i.e. time inside SRAM windows.
  - Renderer: R23_MapRead/MapWrite called from R_Subsector ~1.9% of all samples.

R123_MODE (comma list, or 'all'):
  flags  - R_AddLine/R_RecalcLineFlags (R27_GROUP_LINE): the line's r_flags already came with the 4-byte
           r_validcount read; recalculation reuses it instead of R23_GET (1 SRAM window per rule) and returns
           the value it wrote instead of reading it back (1 more window). Same bytes written, same flags used.
  idle   - P_MobjThinker: a mobj with no momentum, on its floor, tics == -1 and not a Nightmare respawn
           candidate does nothing in the original; the public P_MobjThinker returns at once for it and calls
           the original body (now P_MobjThinkerFull, noinline) otherwise. Corpses no longer pay the big prologue.
  shoot  - PIT_AddThingIntercepts: a thing without MF_SHOOTABLE is ignored by both traversers that add things
           (PTR_AimTraverse, PTR_ShootTraverse: "corpse or something", return true, no side effect). It still
           takes its intercept slot exactly as before (same side tests, same 'behind source' sign test, same
           64-entry overflow), but with frac = FRACUNIT+1 instead of the FixedDiv long division: it is never
           visited before an in-range intercept and never changes the result.
No RAM is added. Logic must be bit-identical (r118_logic_check) and pixels identical.
"""
import os
from pathlib import Path

mode = os.environ['R123_MODE']
modes = {'flags', 'idle', 'shoot'} if mode == 'all' else set(mode.split('+'))
assert modes and modes <= {'flags', 'idle', 'shoot'}, mode


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))


if 'flags' in modes:
    R = 'src/r_draw.c'
    rep(R, '#define R27_SET_RENDER_FLAGS(p,v) R23_MapWrite((p),offsetof(linedata_t,r_validcount),4,((uint32_t)(uint16_t)_g_gametic<<16)|(uint16_t)(v))',
        '/* R123 flags: also keep the byte that is stored (r_flags is one byte with R81). */\n'
        '#define R27_SET_RENDER_FLAGS(p,v) (r123_new=(uint8_t)(uint16_t)(v), R23_MapWrite((p),offsetof(linedata_t,r_validcount),4,((uint32_t)(uint16_t)_g_gametic<<16)|(uint16_t)(v)))')
    s = Path(R).read_text()
    a = s.index('static void R_RecalcLineFlags(void)\n{'); b = s.index('\n}\n', a) + 3
    body = s[a:b]
    assert body.count('R23_GET(linedef,r_flags) & ML_MAPPED') == 4, body.count('R23_GET(linedef,r_flags) & ML_MAPPED')
    body = body.replace('static void R_RecalcLineFlags(void)\n{', 'static uint16_t R_RecalcLineFlags(uint16_t r123_old)\n{\n    uint16_t r123_new = 0; /* R123: r_flags as written */')
    body = body.replace('R23_GET(linedef,r_flags) & ML_MAPPED', 'r123_old & ML_MAPPED')
    # Every exit returns the byte written. The twosided early return and the end of the function.
    assert body.count('        return;\n') == 1
    body = body.replace('        return;\n', '        return r123_new;\n')
    assert body.endswith('\n}\n'); body = body[:-3] + '\n    return r123_new;\n}\n'
    s = s[:a] + body + s[b:]
    Path(R).write_text(s)
    rep(R, '        R_RecalcLineFlags();render_info=(uint16_t)R23_GET(linedef,r_flags);',
        '        render_info=R_RecalcLineFlags((uint16_t)render_info); /* R123: no SRAM read-back */')
    # Non-GROUP_LINE path is not built here; keep it compiling with the new signature.
    rep(R, '''    if (R23_GET(linedef,r_validcount) != (uint16_t)_g_gametic)
        R_RecalcLineFlags();''', '''    if (R23_GET(linedef,r_validcount) != (uint16_t)_g_gametic)
        R_RecalcLineFlags((uint16_t)R23_GET(linedef,r_flags));''')

if 'idle' in modes:
    M = 'src/p_mobj.c'
    rep(M, 'void P_MobjThinker (mobj_t __far* mobj)\n{\n    // momentum movement\n',
        '''static void __attribute__((noinline)) P_MobjThinkerFull (mobj_t __far* mobj);
/* R123 idle: exactly the cases where the full thinker below does nothing at all. */
void P_MobjThinker (mobj_t __far* mobj)
{
    if (!(mobj->momx | mobj->momy) && mobj->z == mobj->floorz && !mobj->momz && mobj->tics == -1
        && (!(mobj->flags & MF_COUNTKILL) || !_g_respawnmonsters))
        return;
    P_MobjThinkerFull(mobj);
}
static void __attribute__((noinline)) P_MobjThinkerFull (mobj_t __far* mobj)
{
    // momentum movement
''')

if 'shoot' in modes:
    U = 'src/p_maputl.c'
    s = Path(U).read_text()
    a = s.index('static boolean PIT_AddThingIntercepts(mobj_t __far* thing)'); b = s.index('\n}\n', a) + 3
    body = s[a:b]
    old = '''  frac = P_InterceptVector3(&_g_trace, &dl);

  if (frac < 0)
    return true;                // behind source
'''
    assert body.count(old) == 1
    new = '''  if (!(thing->flags & MF_SHOOTABLE))
    {
      /* R123 shoot: ignored by PTR_AimTraverse/PTR_ShootTraverse. Same slot and overflow as before,
         'behind source' decided by the same sign test as P_InterceptVector3, no FixedDiv. */
      if (r123_behind(&_g_trace, &dl))
        return true;            // behind source
      frac = FRACUNIT + 1;      // never visited before an in-range intercept
    }
  else
    {
      frac = P_InterceptVector3(&_g_trace, &dl);

      if (frac < 0)
        return true;            // behind source
    }
'''
    body = body.replace(old, new)
    helper = '''/* R123 shoot: true exactly when P_InterceptVector3 returns a negative value (num, den nonzero, signs differ). */
static boolean r123_behind(const divline_t *v2, const divline_t *v1)
{
#if defined(DOOM_R47_MUL_LOGIC)
	fixed_t a = R47_Mul32x16((v1->x - v2->x) >> 8,(int16_t)(v1->dy >> FRACBITS));
	fixed_t b = R47_Mul32x16((v2->y - v1->y) >> 8,(int16_t)(v1->dx >> FRACBITS));
#else
	fixed_t a = (v1->dy >> FRACBITS) * ((v1->x - v2->x) >> 8);
	fixed_t b = (v1->dx >> FRACBITS) * ((v2->y - v1->y) >> 8);
#endif
	fixed_t c = FixedMul(v2->dx, v1->dy >> 8);
	fixed_t d = FixedMul(v2->dy, v1->dx >> 8);
	fixed_t num = a + b;
	fixed_t den = c - d;
	return num != 0 && den != 0 && (num ^ den) < 0;
}

'''
    s = s[:a] + helper + body + s[b:]
    Path(U).write_text(s)

tag = '+'.join(sorted(modes)) if mode != 'all' else 'all'
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert s.count("'r122-'") == 1 and s.count("('layout', 1)") == 1
p.write_text(s.replace("'r122-'", "'r123-'").replace("('layout', 1)", "('%s', 1)" % tag.replace('+', '')))
print('R123', sorted(modes))
