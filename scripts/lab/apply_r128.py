#!/usr/bin/env python3
"""R128 (after apply_r126.py early): behaviour/map simplifications accepted by the user (2026-11-04).

R128_MODE: stairs, corpses, sight, far (joined with '+') or 'all'.
  stairs  - build step: scripts/lab/r128_stairs.py merges small steps in the converted maps (risers vanish,
            stairs keep <= 24-unit steps). Local test on the converted WAD: E1M1 6, E1M2 20, E1M3 12, E1M4 5,
            E1M5 8, E1M6 23, E1M7 10, E1M8 2, E1M9 7 step pairs merged.
  corpses - a dead monster (MF_CORPSE, final frame tics == -1) is removed after R128_CORPSE_TICS (70 = 2 s);
            the player's own body is kept. Fewer sprites to draw and fewer things in blockmap/hitscan/collision.
  sight   - a monster may only do line-of-sight checks in a 4-tic window of every 12 tics (staggered per
            monster); outside it P_CheckSight returns false (sees nothing). The player's checks are not limited.
  far     - sprites farther than R128_FAR_UNITS (1280) from the view are not drawn.
No RAM added (corpse timer reuses movecount, unused by a corpse outside Nightmare respawn).
"""
import os
from pathlib import Path

mode = os.environ['R128_MODE']
ALL = {'stairs', 'corpses', 'sight', 'far'}
modes = ALL if mode == 'all' else set(mode.split('+'))
assert modes and modes <= ALL, mode


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))


if 'stairs' in modes:
    F = 'scripts/lab/build_r35_linear.fish'
    a = '    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1\n'
    rep(F, a, a + '    python3 scripts/lab/r128_stairs.py scripts/doom64.wad; or exit 1\n')

if 'corpses' in modes:
    rep('src/p_mobj.c', 'void P_MobjThinker (mobj_t __far* mobj)\n{\n',
        '''void P_MobjThinker (mobj_t __far* mobj)
{
    /* R128 corpses: bodies vanish 2 s after their last frame (not the player's). */
    if ((mobj->flags & MF_CORPSE) && mobj->tics == -1 && mobj != _g_player.mo)
    {
        if (++mobj->movecount >= 70)
        {
            P_RemoveMobj(mobj);
            return;
        }
    }
''')

if 'sight' in modes:
    rep('src/p_sight.c', '''boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)
{
''', '''boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)
{
  /* R128 sight: monsters look only in a 4-tic window of every 12 tics (staggered by address). */
  if (t1 != _g_player.mo)
    {
      const uint16_t ph = (uint16_t)((uint16_t)_g_gametic + (uint16_t)(((uintptr_t)t1) >> 5)) % 12u;
      if (ph >= 4u)
        return false;
    }
''')

if 'far' in modes:
    rep('src/r_draw.c', '''    const fixed_t tz = xc - (-ys);

    // thing is behind view plane?
    if (tz < MINZ)''', '''    const fixed_t tz = xc - (-ys);

    /* R128 far: no sprites beyond 1280 units. */
    if (tz > 1280*FRACUNIT)
        return;

    // thing is behind view plane?
    if (tz < MINZ)''')

tag = 'all' if mode == 'all' else ''.join(sorted(modes))
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert s.count("'r126-'") == 1 and s.count("('early', 1)") == 1
p.write_text(s.replace("'r126-'", "'r128-'").replace("('early', 1)", "('%s', 1)" % tag))
print('R128', sorted(modes))
