#!/usr/bin/env python3
"""R120 experimental exact sight bbox and collision clipping fast paths.

Run AFTER R118_MODE=mulvc and R119_MODE=both.
R120_MODE = sight | collision | both. No new static RAM.

sight:
  Convert LOS fixed-point bbox edges to floor/ceil map coordinates once per
  subsector; compare with int16 line bbox without re-shifting 4 corners per
  seg; defer mapline address calculation until after validcount test.
collision:
  In PIT_CheckLine, replace four int16->fixed shifts per checked line with
  exact floor/ceil fixed-point comparisons, preserving all <=/>= boundaries.
All changes require 10-demo state identity, pixel checks, memory equality,
and A/B improvements. Never merge a regressing variant.
"""
from pathlib import Path
import os
mode=os.environ["R120_MODE"]
assert mode in ("sight","collision","both")
def rep(p,a,b):
    path=Path(p);s=path.read_text()
    assert s.count(a)==1,(p,a[:120],s.count(a))
    path.write_text(s.replace(a,b))
if mode in ("sight","both"):
    rep("src/p_sight.c",
'''    const sector_t __far* back  = NULL;

    for (count = _g_mapsubsectors[num].numsegs; --count >= 0; seg++)''',
'''    const sector_t __far* back  = NULL;
    /* R120 exact integer thresholds: for integer n and fixed f,
       (n<<16)>f iff n>floor(f/65536);
       (n<<16)<f iff n<ceil(f/65536). */
    const int32_t r120_right_floor = los.bbox[BOXRIGHT] >> FRACBITS;
    const int32_t r120_top_floor = los.bbox[BOXTOP] >> FRACBITS;
    const int32_t r120_left_ceil =
        (los.bbox[BOXLEFT] >> FRACBITS) + ((uint16_t)los.bbox[BOXLEFT] != 0);
    const int32_t r120_bottom_ceil =
        (los.bbox[BOXBOTTOM] >> FRACBITS) + ((uint16_t)los.bbox[BOXBOTTOM] != 0);

    for (count = _g_mapsubsectors[num].numsegs; --count >= 0; seg++)''')
    rep("src/p_sight.c",
'''        const line_t *mapline = &_g_maplines[linenum];
        divline_t divl;''',
'''        divline_t divl;''')
    rep("src/p_sight.c",
'''        if ((fixed_t)mapline->bbox[BOXLEFT  ]<<FRACBITS > los.bbox[BOXRIGHT ] ||
            (fixed_t)mapline->bbox[BOXRIGHT ]<<FRACBITS < los.bbox[BOXLEFT  ] ||
            (fixed_t)mapline->bbox[BOXBOTTOM]<<FRACBITS > los.bbox[BOXTOP   ] ||
            (fixed_t)mapline->bbox[BOXTOP   ]<<FRACBITS < los.bbox[BOXBOTTOM])
            continue;''',
'''        const line_t *mapline = &_g_maplines[linenum];
        if (mapline->bbox[BOXLEFT] > r120_right_floor ||
            mapline->bbox[BOXRIGHT] < r120_left_ceil ||
            mapline->bbox[BOXBOTTOM] > r120_top_floor ||
            mapline->bbox[BOXTOP] < r120_bottom_ceil)
            continue;''')
if mode in ("collision","both"):
    rep("src/p_map.c",
'''  if (_g_tmbbox[BOXRIGHT]  <= (fixed_t)ld->bbox[BOXLEFT]   << FRACBITS
   || _g_tmbbox[BOXLEFT]   >= (fixed_t)ld->bbox[BOXRIGHT]  << FRACBITS
   || _g_tmbbox[BOXTOP]    <= (fixed_t)ld->bbox[BOXBOTTOM] << FRACBITS
   || _g_tmbbox[BOXBOTTOM] >= (fixed_t)ld->bbox[BOXTOP]    << FRACBITS)
    return true; // didn't hit it''',
'''  /* R120: floor/ceil comparisons preserve <= and >= inclusive bounds.
     ceil(f/65536) = (f>>16) + (low16(f)!=0), including negative f. */
  const int32_t r120_right_ceil =
      (_g_tmbbox[BOXRIGHT] >> FRACBITS) + ((uint16_t)_g_tmbbox[BOXRIGHT] != 0);
  const int32_t r120_left_floor = _g_tmbbox[BOXLEFT] >> FRACBITS;
  const int32_t r120_top_ceil =
      (_g_tmbbox[BOXTOP] >> FRACBITS) + ((uint16_t)_g_tmbbox[BOXTOP] != 0);
  const int32_t r120_bottom_floor = _g_tmbbox[BOXBOTTOM] >> FRACBITS;
  if (r120_right_ceil <= ld->bbox[BOXLEFT] ||
      r120_left_floor >= ld->bbox[BOXRIGHT] ||
      r120_top_ceil <= ld->bbox[BOXBOTTOM] ||
      r120_bottom_floor >= ld->bbox[BOXTOP])
    return true; // didn't hit it''')
p=Path("scripts/lab/build_r71a12mul_hud.py");s=p.read_text()
assert s.count("'r119-'")==1 and s.count("('both', 1)")==1,(s.count("'r119-'"),s.count("('both', 1)"))
p.write_text(s.replace("'r119-'","'r120-'").replace("('both', 1)","('%s', 1)"%mode))
print("R120",mode)
