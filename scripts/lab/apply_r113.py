#!/usr/bin/env python3
"""R113 hilut (after the R107 direct chain): drop LSL.B #4 from the seg-wall pair loop.

Kernel R113_WallColumn = R60 with a pre-shifted LUT twin for the high-nibble sample
(a3 = LUT + 8704, saved/restored inside the kernel): per pixel pair one LSL.B #4 (14 cycles) less.
Used only by R96 seg walls (LUT is always a composed X_comp table). Sprites/R42 keep R60.
Build step r113_shift_luts.py appends the twins to the six composed LUTs (+52 KB ROM).
Identical pixels.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


k = Path('src/r60_pair_wall.s').read_text()
assert k.count(' rts') == 1
k = k.replace('R60_WallColumn', 'R113_WallColumn')
k = k.replace('R113_WallColumn:\n', 'R113_WallColumn:\n move.l %a3,-(%sp)\n lea 8704(%a2),%a3\n', 1)
a = ' move.b (%a2,%d5.w),%d5\n move.b (%a2,%d3.w),%d3\n lsl.b #4,%d5\n'
assert k.count(a) == 1; k = k.replace(a, ' move.b (%a3,%d5.w),%d5\n move.b (%a2,%d3.w),%d3\n')
a = ' move.b (%a2,%d5.w),%d5\n lsl.b #4,%d5\n'
assert k.count(a) == 1; k = k.replace(a, ' move.b (%a3,%d5.w),%d5\n')
k = k.replace(' rts', ' move.l (%sp)+,%a3\n rts')
Path('src/r113_hilut_wall.s').write_text(k)
h = Path('src/r60_pair_wall.h').read_text()
Path('src/r113_hilut_wall.h').write_text(h.replace('R60_PAIR_WALL_H', 'R113_HILUT_WALL_H').replace('R60_WallDraw', 'R113_WallDraw').replace('R60_WallColumn', 'R113_WallColumn'))
D = 'src/r_draw.c'
rep(D, '#include "r60_pair_wall.h"\nstatic uint8_t *r96_fb;', '#include "r60_pair_wall.h"\n#include "r113_hilut_wall.h"\nstatic uint8_t *r96_fb;')
rep(D, '    if (count >= 2) { R60_WallDraw(dst, v->source, lut, f, v->fracstep, count, (uint16_t)(yl & 1)); return; }',
       '    if (count >= 2) { R113_WallDraw(dst, v->source, lut, f, v->fracstep, count, (uint16_t)(yl & 1)); return; }')
F = 'scripts/lab/build_r35_linear.fish'
a = '    rm -rf out\n    rm -f res/music.rs res/music.d\n'
rep(F, a, '    python3 scripts/lab/r113_shift_luts.py src/r59_color_tables.h; or exit 1\n' + a)
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r107-'" in s and "('direct', 1)" in s
p.write_text(s.replace("'r107-'", "'r113-'").replace("('direct', 1)", "('hilut', 1)"))
print('R113 hilut')
