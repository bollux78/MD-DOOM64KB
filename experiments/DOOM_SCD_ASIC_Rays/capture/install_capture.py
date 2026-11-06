"""Add a debugger hook to a disposable R128 build."""
from pathlib import Path

path = Path("src/p_sight.c")
source = path.read_text()
signature = "boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)"
assert source.count(signature) == 1
source = source.replace(signature, "static " + signature.replace(
    "P_CheckSight", "P_CheckSightNative").replace("t2)", "t2, uint32_t *route)"))


def tag(anchor, replacement):
    global source
    assert source.count(anchor) == 1, anchor
    source = source.replace(anchor, replacement)


tag("   && prevlat2 == linearAddress(t2))\n    return prevr;",
    "   && prevlat2 == linearAddress(t2))\n  {\n    *route = 0;\n    return prevr;\n  }")
tag("    prevr = false;\n    return prevr;", "    *route = 1;\n    prevr = false;\n    return prevr;")
tag("    prevr = true;\n    return prevr;", "    *route = 2;\n    prevr = true;\n    return prevr;")
tag("  prevr = P_CrossBSPNode(numnodes-1);", "  *route = 3;\n  prevr = P_CrossBSPNode(numnodes-1);")
path.write_text('#include "d_player.h"\n' + source + """

/* Fixed debugger ABI, with seven 32-bit arguments. */
void __attribute__((noipa)) SCD_RayCapture(uint32_t tic, int32_t x1, int32_t y1,
                                          int32_t x2, int32_t y2, uint32_t visible, uint32_t route)
{
    __asm__ volatile ("" : : "g"(tic), "g"(x1), "g"(y1), "g"(x2), "g"(y2),
                       "g"(visible), "g"(route) : "memory");
}

boolean P_CheckSight(mobj_t __far* t1, mobj_t __far* t2)
{
    uint32_t route;
    const boolean visible = P_CheckSightNative(t1, t2, &route);
    if (_g_gamemap == 1 && _g_gametic >= 200 && _g_gametic <= 2600 &&
        t2 == _g_player.mo && (t1->flags & MF_COUNTKILL))
        SCD_RayCapture(_g_gametic, t1->x, t1->y, t2->x, t2->y, !!visible, route);
    return visible;
}
""")
