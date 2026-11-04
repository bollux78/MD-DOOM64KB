#!/usr/bin/env python3
"""R126 early (after apply_r122.py layout): hitscan stops at the first obstacle, block by block.

Behaviour change accepted by the user (2026-11-04): not bit-identical to vanilla.
Original P_PathTraverse collects intercepts along the WHOLE trace (up to 2048 units, up to 64 blockmap
blocks) and only then visits them in order; bullets almost always stop in the first blocks, so most of
the work is thrown away. That is the E1M7/E1M3 frame spikes (R121: 50-60 VBlanks vs 20).
Now, for traces that add things (P_AimLineAttack / P_LineAttack only; use-lines and sliding unchanged):
after each block, the intercepts collected so far are visited in increasing frac exactly like
P_TraverseIntercepts; if the traverser stops (wall, monster) the trace ends there; otherwise the
array is emptied and the next block is added.
Differences vs vanilla:
  - the 64-intercept overflow (whole shot silently cancelled) practically disappears;
  - a thing whose centre lies in a later block but whose cross-section is crossed slightly before a
    two-sided line already visited is visited after that line (order inside one block boundary).
No RAM added.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


U = 'src/p_maputl.c'
rep(U, '''      if (flags & PT_ADDTHINGS)
        if (!P_BlockThingsIterator(mapx, mapy,PIT_AddThingIntercepts))
          return false; // early out
''', '''      if (flags & PT_ADDTHINGS)
        {
          if (!P_BlockThingsIterator(mapx, mapy,PIT_AddThingIntercepts))
            return false; // early out
          /* R126: visit what this block added; stop the trace at the first obstacle. */
          {
            const int8_t r = R126_VisitPending(trav);
            if (r == 0) return false;
            if (r == 1) return true;
          }
        }
''')
s = Path(U).read_text()
i = s.index('boolean P_PathTraverse(')
s = s[:i] + '''/* R126: 0 = traverser stopped, 1 = beyond range (done), 2 = all pending visited, keep tracing. */
static int8_t R126_VisitPending(traverser_t func)
{
  while (intercept_p > intercepts)
    {
      intercept_t *in = NULL, *scan;
      fixed_t dist = INT32_MAX;
      for (scan = intercepts; scan < intercept_p; scan++)
        if (scan->frac < dist)
          dist = (in=scan)->frac;
      if (!in)
        break;                  // everything pending already visited
      if (dist > FRACUNIT)
        return 1;
      if (!func(in))
        return 0;
      in->frac = INT32_MAX;
    }
  intercept_p = intercepts;     // empty: next block starts a fresh list
  return 2;
}

''' + s[i:]
Path(U).write_text(s)

# R126b: no I_Error on drawseg/opening overflow (PIXEL4 keeps only 64 drawsegs to save RAM).
# Vanilla behaviour: skip the extra wall for that frame instead of stopping the game. Seen on the console:
# E1M2 demo, "Drawsegs overflow." -> halt. This is a latent crash of the base too (any view with > 64 segs).
R = 'src/r_draw.c'
rep(R, """    if (ds_p == &_s_drawsegs[MAXDRAWSEGS])
    {
#if defined(RANGECHECK) || defined(DOOM_R22_PIXEL4)
        I_Error("Drawsegs overflow.");
#endif
        return;
    }""", """    if (ds_p == &_s_drawsegs[MAXDRAWSEGS])
    {
#if defined(RANGECHECK)
        I_Error("Drawsegs overflow.");
#endif
        return; /* R126b: drop the extra wall for this frame */
    }""")
rep(R, """#if defined(RANGECHECK) || defined(DOOM_R22_PIXEL4)
    if(need > MAXOPENINGS)
        I_Error("Openings overflow. Need = %ld", need);
#endif""", """#if defined(RANGECHECK)
    if(need > MAXOPENINGS)
        I_Error("Openings overflow. Need = %ld", need);
#endif""")

p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert s.count("'r122-'") == 1 and s.count("('layout', 1)") == 1
p.write_text(s.replace("'r122-'", "'r126-'").replace("('layout', 1)", "('early', 1)"))
print('R126 early')
