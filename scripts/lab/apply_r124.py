#!/usr/bin/env python3
"""R124: exact reuse of adjacent-segment endpoint angle in a subsector.
Apply after R119 both + R122 layout. No persistent RAM, no rendering change.
Only reuse when exact vertex coordinates match; otherwise use original angle calculation.
"""
from pathlib import Path

p = Path("src/r_draw.c")
s = p.read_text()

def change(old, new):
    global s
    n = s.count(old)
    assert n == 1, (old[:100], n)
    s = s.replace(old, new, 1)

change(
"""static void R_AddLine(const seg_t __far* line)
{
    curline = line;

    angle16_t angle1 = R_PointToAngle16(line->v1.x, line->v1.y);
    angle16_t angle2 = R_PointToAngle16(line->v2.x, line->v2.y);""",
"""/* R124: precomputed angles are valid for precisely the same vertex coordinates. */
static void R_AddLineAngles(const seg_t __far* line,
                             angle16_t angle1, angle16_t angle2)
{
    curline = line;""")

change(
"""    R_AddSprites(sub, frontsector->lightlevel);
    while (count--)
    {
        R37_HIT(R37_SEGS);
        R7_VOID(9, R_AddLine(line));
        line++;
        curline = NULL;""",
"""    R_AddSprites(sub, frontsector->lightlevel);
    /* Adjacent segs often share v2(previous) == v1(next).
       Cache by exact coordinates, not pointer identity or geometry assumptions.
       This state is stack-only and reset for each subsector. */
    int have_last = 0;
    int16_t last_x = 0, last_y = 0;
    angle16_t last_angle = 0;
    while (count--)
    {
        const int16_t x1 = line->v1.x;
        const int16_t y1 = line->v1.y;
        const int16_t x2 = line->v2.x;
        const int16_t y2 = line->v2.y;
        angle16_t a1 = (have_last && x1 == last_x && y1 == last_y)
                     ? last_angle : R_PointToAngle16(x1, y1);
        angle16_t a2 = R_PointToAngle16(x2, y2);
        R37_HIT(R37_SEGS);
        R7_VOID(9, R_AddLineAngles(line, a1, a2));
        last_x = x2;
        last_y = y2;
        last_angle = a2;
        have_last = 1;
        line++;
        curline = NULL;""")
p.write_text(s)
b = Path("scripts/lab/build_r71a12mul_hud.py")
z = b.read_text()
assert z.count("'r122-'") == 1 and z.count("('layout', 1)") == 1
b.write_text(z.replace("'r122-'", "'r124-'").replace("('layout', 1)", "('segangle', 1)"))
print("R124 SEGANGLE applied; angle reuse only on exact contiguous vertex positions")
