#!/usr/bin/env python3
"""Independent R128 runtime experiments, applied after the shareware overlays."""
from pathlib import Path
import os

mode = os.environ.get('R128_BATCH', 'control')
options = {'block', 'shot', 'openings', 'effects'}
enabled = options if mode == 'all' else {mode}
assert enabled <= options or mode == 'control'

def edit(file, old, new):
    path = Path(file)
    text = path.read_text()
    assert text.count(old) == 1, (file, old[:80], text.count(old))
    path.write_text(text.replace(old, new))

if 'block' in enabled:
    edit('src/r22_blocklinks.h',
         'static inline uint32_t R22_SramRead32(uint32_t a){',
         '''uint32_t R129_BlockRead(uint32_t address);
void R129_BlockWrite(uint32_t address,uint32_t value);
static inline uint32_t R22_SramRead32(uint32_t a){''')
    edit('src/r22_blocklinks.h',
         'R22_IsSramLink(p)?(mobj_t*)(uintptr_t)R22_SramRead32((uint32_t)(uintptr_t)p):*p',
         'R22_IsSramLink(p)?(mobj_t*)(uintptr_t)R129_BlockRead((uint32_t)(uintptr_t)p):*p')
    edit('src/r22_blocklinks.h',
         'if(R22_IsSramLink(p))R22_SramWrite32((uint32_t)(uintptr_t)p,(uint32_t)(uintptr_t)v);',
         'if(R22_IsSramLink(p))R129_BlockWrite((uint32_t)(uintptr_t)p,(uint32_t)(uintptr_t)v);')
    edit('src/r22_blocklinks.c', 'uint16_t r22_block_cells;', '''uint16_t r22_block_cells;
typedef struct { uint32_t value; uint16_t tag; } r129_head_t;
static r129_head_t r129_heads[8];
uint32_t R129_BlockRead(uint32_t address){
    uint16_t index=(uint16_t)((address-R22_SRAM_BASE)>>3);
    r129_head_t *entry=&r129_heads[index&7u];
    if(entry->tag!=(uint16_t)(index+1u)){
        entry->value=R22_SramRead32(address);
        entry->tag=(uint16_t)(index+1u);
    }
    return entry->value;
}
void R129_BlockWrite(uint32_t address,uint32_t value){
    uint16_t index=(uint16_t)((address-R22_SRAM_BASE)>>3);
    r129_head_t *entry=&r129_heads[index&7u];
    R22_SramWrite32(address,value);
    entry->value=value;entry->tag=(uint16_t)(index+1u);
}''')
    edit('src/r22_blocklinks.c', '    r22_block_cells=(uint16_t)cells;',
         '    for(uint16_t i=0;i<8;i++)r129_heads[i].tag=0;\n    r22_block_cells=(uint16_t)cells;')

if 'shot' in enabled:
    edit('src/p_map.c', 'static fixed_t  aimslope;', '''static fixed_t  aimslope;
static mobj_t *r129_shooter;
static fixed_t r129_x,r129_y,r129_z,r129_height,r129_shootz;
static fixed_t R129_ShootZ(mobj_t *actor){
    fixed_t height=MOBJ_HEIGHT(actor);
    if(r129_shooter!=actor || r129_x!=actor->x || r129_y!=actor->y ||
       r129_z!=actor->z || r129_height!=height){
        r129_shooter=actor;r129_x=actor->x;r129_y=actor->y;
        r129_z=actor->z;r129_height=height;
        r129_shootz=actor->z+(height>>1)+8*FRACUNIT;
    }
    return r129_shootz;
}''')
    p=Path('src/p_map.c');s=p.read_text()
    expression='shootz = t1->z + (MOBJ_HEIGHT(t1)>>1) + 8*FRACUNIT;'
    assert s.count(expression)==2
    p.write_text(s.replace(expression,'shootz = R129_ShootZ(t1);'))

if 'openings' in enabled:
    edit('src/p_maputl.c', 'void P_LineOpening(const line_t __far* linedef)',
         '''static const line_t *r129_openline;
static fixed_t r129_frontfloor,r129_backfloor,r129_frontceil,r129_backceil;
static fixed_t r129_top,r129_bottom,r129_low;
void P_LineOpening(const line_t __far* linedef)''')
    anchor='    openbacksector  = LN_BACKSECTOR(linedef);'
    edit('src/p_maputl.c',anchor,anchor+'''
    if(r129_openline==linedef &&
       r129_frontfloor==openfrontsector->floorheight &&
       r129_backfloor==openbacksector->floorheight &&
       r129_frontceil==openfrontsector->ceilingheight &&
       r129_backceil==openbacksector->ceilingheight){
        _g_opentop=r129_top;_g_openbottom=r129_bottom;_g_lowfloor=r129_low;
        _g_openrange=r129_top-r129_bottom;
        return;
    }
    r129_openline=linedef;
    r129_frontfloor=openfrontsector->floorheight;
    r129_backfloor=openbacksector->floorheight;
    r129_frontceil=openfrontsector->ceilingheight;
    r129_backceil=openbacksector->ceilingheight;
''')
    edit('src/p_maputl.c','    _g_openrange = _g_opentop - _g_openbottom;',
         '''    _g_openrange = _g_opentop - _g_openbottom;
    r129_top=_g_opentop;r129_bottom=_g_openbottom;r129_low=_g_lowfloor;''')

if 'effects' in enabled:
    p=Path('src/p_mobj.c');s=p.read_text()
    a=s.index('void P_SpawnBlood(');b=s.index('// P_CheckMissileSpawn',a)
    s=s[:a]+'''void P_SpawnBlood(fixed_t x,fixed_t y,fixed_t z,int16_t damage)
{
    (void)x;(void)y;(void)z;(void)damage;
    /* Preserve the four RNG calls of the removed spawn. */
    P_Random();P_Random();P_Random();P_Random();
}


//
//
'''+s[b:]
    anchor='void P_SpawnPuff(fixed_t x,fixed_t y,fixed_t z)\n  {'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''
  if(_g_player.mo &&
     (P_AproxDistance(x-_g_player.mo->x,y-_g_player.mo->y)>192*FRACUNIT ||
      z-_g_player.mo->z>192*FRACUNIT || _g_player.mo->z-z>192*FRACUNIT)){
      P_Random();P_Random();P_Random();P_Random();
      return;
  }''')
    p.write_text(s)
print('R128 batch option',mode)
