#!/usr/bin/env python3
"""R103 diag (applied after apply_r100.py f1): validate blockmap thing pointers.

Real hardware: ADDRESS ERROR in PIT_AddThingIntercepts, thing = 0xBCFCFFFF, always at the same
point of the benchmark demo (E1M1 and E1M7) in several versions. This build checks every mobj
pointer that P_BlockThingsIterator hands out (SRAM head or bnext chain). On a bad pointer it calls
R103_Bad() (noipa: BlastEm breakpoint) and then I_Error with tic, map, cell, the SRAM head and the
previous thing, so the real console shows where it happens instead of the address error.
r103_norender (1 B BSS, default 0) lets the BlastEm probe skip R_RenderPlayerView to reach late tics.
Diagnostic only, never a deliverable.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


OLD = """#if defined(DOOM_R22_SRAM_BLOCKLINKS)
    for (mobj = R22_BlockHead((uint16_t)(y*_g_bmapwidth+x)); mobj; mobj = mobj->bnext)
#else
    for (mobj = _g_blocklinks[y*_g_bmapwidth+x]; mobj; mobj = mobj->bnext)
#endif
      if (!func(mobj))
        return false;
"""
NEW = """#if defined(DOOM_R22_SRAM_BLOCKLINKS)
  {
    uint16_t r103_cell=(uint16_t)(y*_g_bmapwidth+x);
    mobj_t *r103_head=R22_BlockHead(r103_cell), *r103_prev=NULL;
    for (mobj = r103_head; mobj; r103_prev = mobj, mobj = mobj->bnext)
    {
      if (R103_BadPtr(mobj)) R103_Bad(mobj, r103_cell, r103_head, r103_prev);
      if (!func(mobj))
        return false;
    }
  }
#else
    for (mobj = _g_blocklinks[y*_g_bmapwidth+x]; mobj; mobj = mobj->bnext)
      if (!func(mobj))
        return false;
#endif
"""
HELPER = """//
// P_BlockThingsIterator
//
#include "i_system.h"
volatile uint8_t r103_norender;
static inline int R103_BadPtr(const void *p)
{
  uint32_t v=(uint32_t)(uintptr_t)p;
  return (v&1u) || ((v&0x00FF0000u)!=0x00FF0000u);
}
static void r103_hex(char *o, uint32_t v)
{
  for (int i=7;i>=0;i--){ uint8_t d=v&15u; o[i]=(char)(d<10?'0'+d:'A'+d-10); v>>=4; }
  o[8]=0;
}
void __attribute__((noipa,noinline,noreturn)) R103_Bad(mobj_t *bad, uint16_t cell, mobj_t *head, mobj_t *prev)
{
  char hb[9], hh[9], hp[9];
  r103_hex(hb,(uint32_t)(uintptr_t)bad); r103_hex(hh,(uint32_t)(uintptr_t)head); r103_hex(hp,(uint32_t)(uintptr_t)prev);
  I_Error("R103 BAD THING %s\\nTIC %d MAP %d\\nCELL %u W %d H %d\\nHEAD %s\\nPREV %s T %d",
          hb, (int)_g_gametic, (int)_g_gamemap, (unsigned)cell, (int)_g_bmapwidth, (int)_g_bmapheight,
          hh, hp, prev ? (int)prev->type : -1);
}
"""

rep('src/p_maputl.c', OLD, NEW)
rep('src/p_maputl.c', "//\n// P_BlockThingsIterator\n//\n", HELPER)
s = Path('src/d_main.c').read_text()
a = "            if (viewactive)\n                R_RenderPlayerView (&_g_player);\n"
assert s.count(a) == 1, s.count(a)
s = s.replace(a, "            extern volatile uint8_t r103_norender;\n            if (viewactive && !r103_norender)\n                R_RenderPlayerView (&_g_player);\n")
Path('src/d_main.c').write_text(s)
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r100-'" in s and "('f1', 1)" in s
p.write_text(s.replace("'r100-'", "'r103-'").replace("('f1', 1)", "('diag', 1)"))
print('R103 diag applied')
