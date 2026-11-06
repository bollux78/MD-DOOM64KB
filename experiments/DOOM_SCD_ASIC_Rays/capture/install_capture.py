"""Add a debugger hook to a disposable R128 build."""
from pathlib import Path

path = Path("src/p_sight.c")
source = path.read_text()
signature = "boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)"
assert source.count(signature) == 1
source = source.replace(signature, "static " + signature.replace("P_CheckSight", "P_CheckSightNative"))
path.write_text('#include "d_player.h"\n' + source + """

/* Fixed debugger ABI, with six 32-bit arguments. */
void __attribute__((noipa)) SCD_RayCapture(uint32_t tic, int32_t x1, int32_t y1,
                                          int32_t x2, int32_t y2, uint32_t visible)
{
    __asm__ volatile ("" : : "g"(tic), "g"(x1), "g"(y1), "g"(x2), "g"(y2),
                       "g"(visible) : "memory");
}

boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)
{
    const boolean visible = P_CheckSightNative(t1, t2);
    if (_g_gamemap == 1 && _g_gametic >= 200 && _g_gametic <= 440 &&
        t2 == _g_player.mo && (t1->flags & MF_COUNTKILL))
        SCD_RayCapture(_g_gametic, t1->x, t1->y, t2->x, t2->y, !!visible);
    return visible;
}
""")
