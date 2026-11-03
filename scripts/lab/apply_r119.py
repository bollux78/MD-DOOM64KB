#!/usr/bin/env python3
"""R119 exact, independently switchable SRAM secnode / collision blockmap optimizations.

Apply *after* R118_MODE=mulvc. No additional static RAM.
R119_MODE=secnodes | collision | both

secnodes: fuse a node's SRAM accesses in P_AddSecnode and P_CreateSecNodeList,
using one bounded R25 protected SRAM window per node operation; do not hold an
SRAM window across callbacks, allocators, or nested functions.
collision: use proven R47_Muls16 for blockmap index y*width in iterator hot paths,
avoiding generic 32-bit libgcc multiplication while retaining full 32-bit result.

Both are experimental, subject to strict logic/pixel/RAM equivalence on the runner.
"""
import os
from pathlib import Path

mode = os.environ["R119_MODE"]
assert mode in ("secnodes", "collision", "both")
def rep(path, a, b, n=1):
    p=Path(path); s=p.read_text(); c=s.count(a)
    assert c==n, (path, a[:90], c)
    p.write_text(s.replace(a,b))

if mode in ("secnodes", "both"):
    p=Path("src/r23_mapmem.h");s=p.read_text()
    anchor="void R23_NodeFree(void *p);"
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''
/* R119: one SRAM window per short linked-node operation (R104 IRQ-safe). */
struct msecnode_s;
struct sector_s;
struct mobj_s;
struct msecnode_s *R119_NodeClearAndNext(struct msecnode_s *p);
int R119_NodeFindOrMark(struct msecnode_s *p,void *s,
                       struct mobj_s *thing,struct msecnode_s **next);
struct mobj_s *R119_NodeThingAndNext(struct msecnode_s *p,
                                     struct msecnode_s **next);
''')
    p.write_text(s)

    p=Path("src/r23_mapmem.c");s=p.read_text()
    anchor='uint32_t R23_MapRead(const void *p,uint16_t offset,uint16_t size){'
    assert s.count(anchor)==1
    extra='''#if defined(DOOM_R24_EPISODE)
/* Each helper holds only one node's read/write operations inside a single,
 * short SRAM window. No callback, allocator or other SRAM-opening call here. */
msecnode_t *R119_NodeClearAndNext(msecnode_t *p){
    R25_SRAM_BEGIN();
    node_write(p,offsetof(msecnode_t,m_thing),0);
    msecnode_t *next=(msecnode_t*)(uintptr_t)node_read(p,offsetof(msecnode_t,m_tnext));
    R25_SRAM_END();
    return next;
}
int R119_NodeFindOrMark(msecnode_t *p,void *s,mobj_t *thing,msecnode_t **next){
    R25_SRAM_BEGIN();
    uint32_t found=node_read(p,offsetof(msecnode_t,m_sector));
    if(found==(uint32_t)(uintptr_t)s){
        node_write(p,offsetof(msecnode_t,m_thing),(uint32_t)(uintptr_t)thing);
        R25_SRAM_END();
        return 1;
    }
    *next=(msecnode_t*)(uintptr_t)node_read(p,offsetof(msecnode_t,m_tnext));
    R25_SRAM_END();
    return 0;
}
mobj_t *R119_NodeThingAndNext(msecnode_t *p,msecnode_t **next){
    R25_SRAM_BEGIN();
    mobj_t *thing=(mobj_t*)(uintptr_t)node_read(p,offsetof(msecnode_t,m_thing));
    *next=(msecnode_t*)(uintptr_t)node_read(p,offsetof(msecnode_t,m_tnext));
    R25_SRAM_END();
    return thing;
}
#endif
'''
    s=s.replace(anchor,extra+anchor)
    p.write_text(s)

    rep("src/p_map.c",'''    if (R23_GET(node,m_sector) == s)   // Already have a node for this sector?
      {
      R23_SET(node,m_thing,thing); // Yes. Setting m_thing says 'keep it'.
      return;
      }
    node = R23_GET(node,m_tnext);''',
    '''    msecnode_t __far* r119_next;
    if (R119_NodeFindOrMark(node,s,thing,&r119_next))
      return;
    node = r119_next;''')
    rep("src/p_map.c",'''    R23_SET(node,m_thing,NULL);
    node = R23_GET(node,m_tnext);''',
    '''    node = R119_NodeClearAndNext(node);''')
    rep("src/p_map.c",'''    if (R23_GET(node,m_thing) == NULL)
      {
      if (node == _s_sector_list)
        _s_sector_list = R23_GET(node,m_tnext);
      node = P_DelSecnode(node);
      }
    else
      node = R23_GET(node,m_tnext);''',
    '''    msecnode_t __far* r119_next;
    mobj_t __far* r119_thing = R119_NodeThingAndNext(node,&r119_next);
    if (r119_thing == NULL)
      {
      if (node == _s_sector_list)
        _s_sector_list = r119_next;
      node = P_DelSecnode(node);
      }
    else
      node = r119_next;''')
    # Original includes r23_mapmem.h via shared map headers. Ensure symbols visible.
    p=Path("src/p_map.c"); s=p.read_text()
    assert '#include "r23_mapmem.h"' not in s
    assert s.count('#include "globdata.h"')==1
    p.write_text(s.replace('#include "globdata.h"','#include "globdata.h"\n#include "r23_mapmem.h"'))

if mode in ("collision", "both"):
    p=Path("src/p_maputl.c");s=p.read_text()
    assert "#define DOOM_R47_MUL_LOGIC 1" in s, "R118 mulvc must run first"
    original="y*_g_bmapwidth+x"
    assert s.count(original)==3, ("expected 3 blockmap iterator indices (including inactive #else)",s.count(original))
    # R47_Muls16 returns the exact signed 32-bit product of two 16-bit operands.
    s=s.replace(original,"R47_Muls16(y,_g_bmapwidth)+x")
    p.write_text(s)

p=Path("scripts/lab/build_r71a12mul_hud.py");s=p.read_text()
assert s.count("'r118-'")==1 and s.count("('mulvc', 1)")==1
s=s.replace("'r118-'","'r119-'").replace("('mulvc', 1)","('%s', 1)"%mode)
p.write_text(s)
print("R119",mode,"generated")
