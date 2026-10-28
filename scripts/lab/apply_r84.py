#!/usr/bin/env python3
"""Independent candidates, applied after R83 sprites."""
from pathlib import Path
import os,subprocess
mode=os.environ['R84_CANDIDATE'];assert mode in ('control','reuse','precomp','directory','sram')
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:80],s.count(a));p.write_text(s.replace(a,b))
if mode=='reuse':
 patch('scripts/lab/build_r35_linear.fish',"case mall\n                set defs $defs '-DDOOM_R39C_MOVEP_CACHE' '-DDOOM_R39C_MOVEP_MAP'", "case mall\n                set defs $defs '-DDOOM_R39C_MOVEP_CACHE' '-DDOOM_R39C_MOVEP_MAP' '-DDOOM_R39C_REUSE_CACHE'")
if mode in ('precomp','directory'):
 subprocess.run(['python3','scripts/lab/gen_r84_columns.py'],check=True)
 patch('src/r_draw.c','#define MAX_CACHE_TRIES 4','#define MAX_CACHE_TRIES 4\n#include "r84_columns.h"')
 # Directory's consumer precedes the cache declaration; put include near file start.
 p=Path('src/r_draw.c');s=p.read_text().replace('#include "r84_columns.h"','');s='#include <stdint.h>\n#include "r84_columns.h"\n'+s;p.write_text(s)
if mode=='precomp':
 a="""        uint8_t i = 0;
        uint8_t patchcount = tex->patchcount;"""
 patch('src/r_draw.c',a,"""        uint32_t baked=r84_offsets[r84_starts[texture]+((uint16_t)xc>>2)];
        if(baked!=0xffffffffUL)memcpy(tmpCache,r84_pixels+baked,128);
        else {
        uint8_t i = 0;
        uint8_t patchcount = tex->patchcount;""")
 patch('src/r_draw.c','        //Block copy will drop low 2 bits of len.','        } /* preserve partial composition and SRAM cache history */\n        //Block copy will drop low 2 bits of len.')
if mode=='directory':
 patch('src/r_draw.c',"""    if (!tex->overlapped)
    {
        int16_t patch_num;""","""    if (!tex->overlapped && r84_patches[texture]>=0) {
        uint16_t xc=(uint16_t)texcolumn & tex->widthmask;
        dcvars->source=(const byte*)W_GetLumpByNum(r84_patches[texture])+r84_simple_offsets[r84_simple_starts[texture]+xc];
        R7_VOID(6,R20_WALL_DRAW(dcvars));
    }
    else if (!tex->overlapped)
    {
        int16_t patch_num;""")
if mode=='sram':
 patch('src/r_draw.c',"""static void R_RecalcLineFlags(void)
{
    const side_t""","""static void R_RecalcLineFlags(void)
{
#if defined(DOOM_R27_GROUP_LINE)
    if(!(maplinedef->flags & ML_TWOSIDED)) {
        R27_SET_RENDER_FLAGS(linedef,(RF_CLOSED | (R23_GET(linedef,r_flags) & ML_MAPPED)));
        return;
    }
#endif
    const side_t""")
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text();assert "r83-" in s;s=s.replace("'r83-'","'r84-'").replace("('sprite-p1f1',0)","('%s',0)"%mode);p.write_text(s)
print('R84',mode,'on R83 sprites')
