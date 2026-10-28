#!/usr/bin/env python3
"""Lossy experiments on R85 all. Each non-control variant includes static sky."""
from pathlib import Path
import os,struct,collections
MODES=('control','sky','farwalls','vhalf','decor','sprites','ai')
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:80],s.count(a));p.write_text(s.replace(a,b))

def wallcolors():
 from r84_texture_audit import audit
 b=Path('scripts/doom64.wad').read_bytes();n=struct.unpack_from('>h',b,4)[0];di=struct.unpack_from('>I',b,8)[0];lumps=[]
 for i in range(n):
  o=di+i*16;p,z=struct.unpack_from('>IH',b,o);lumps.append((b[o+8:o+16].rstrip(b'\0').decode(),b[p:p+z]))
 d=dict(lumps);tp=d['TEXTUREP'];nt=struct.unpack_from('>I',d['TEXTURE1'])[0];cols=[];audit('scripts/doom64.wad',columns=cols);hist=[collections.Counter() for _ in range(nt)]
 for t,x,c in cols:hist[t].update(c)
 colors=[]
 for t in range(nt):
  if not hist[t]:
   o=struct.unpack_from('>H',tp,t*2)[0];pn=struct.unpack_from('>h',tp,o+12)[0];p=lumps[pn][1];w=struct.unpack_from('>h',p)[0]
   for x in range(w):
    j=struct.unpack_from('>I',p,8+4*x)[0]
    while p[j]!=255:
     z=p[j+1];hist[t].update(p[j+3:j+3+z]);j+=z+4
  colors.append(hist[t].most_common(1)[0][0] if hist[t] else 0)
 Path('src/r87_wallcolors.h').write_text('static const uint8_t r87_wallcols[][128]={\n'+',\n'.join('{'+','.join([str(c)]*128)+'}' for c in colors)+'};\n')

def halfkernel(s):
 a=s.index('3:\n');b=s.index('4:\n',a)
 s=s[:a]+'''3:
 move.b (%a1,%d0.w),%d5
 add.w %d6,%d4
 addx.w %d1,%d0
 and.w %d7,%d0
 move.b (%a2,%d5.w),%d5
 move.b %d5,%d3
 lsl.b #4,%d5
 or.b %d3,%d5
 move.b %d5,(%a0)
 lea 152(%a0),%a0
 dbra %d2,3b
'''+s[b:]
 # Double the phase increment only after the partial odd head.
 s=s.replace('2:\n moveq #0,%d3','2:\n add.w %d6,%d6\n addx.w %d1,%d1\n and.w #127,%d1\n moveq #0,%d3')
 # Tail position is correct, but an odd tail must not need a doubled phase advance.
 return s

def main():
 mode=os.environ['R87_CANDIDATE'];assert mode in MODES
 if mode!='control':
  # R_LoadSkyPatch is already a no-op. Only the visible spans invoke R_DrawSky.
  patch('src/r_sky.c','''void R_DrawSky(draw_column_vars_t *dcvars)
{
''','''void R_DrawSky(draw_column_vars_t *dcvars)
{
    /* Screen-anchored sky: no view angle or angular perspective. Clip
       before resolving the patch column or sampling its texture. */
    int16_t lo=dcvars->yl,hi=dcvars->yh;
    int16_t xmin=0,xend=VIEWWINDOWWIDTH,ymin=0,yend=VIEWWINDOWHEIGHT;
#if defined(DOOM_R57_CROP16)
    if(R57_CROP_ACTIVE){xmin=R57_XMIN;xend=R57_XEND;ymin=R57_YMIN;yend=R57_YEND;}
#endif
    if(dcvars->x<xmin || dcvars->x>=xend)return;
    if(lo<ymin)lo=ymin;if(hi>=yend)hi=yend-1;
    if(lo>hi)return;
    dcvars->yl=lo;dcvars->yh=hi;
''')
  patch('src/r_sky.c','void R_DrawSky(draw_column_vars_t *dcvars)',
        'static const uint8_t r87_skyx[76]={'+','.join(str(x*256//76) for x in range(76))+'};\nvoid R_DrawSky(draw_column_vars_t *dcvars)')
  patch('src/r_sky.c','#include "w_wad.h"','#include "w_wad.h"\n#include "r57_viewport.h"')
  patch('src/r_sky.c','''\tint16_t xc = viewangle >> FRACBITS;
\txc += xtoviewangleTable[dcvars->x];
\txc >>= ANGLETOSKYSHIFT - FRACBITS;
\txc &= skywidthmask;''','''\tint16_t xc=r87_skyx[dcvars->x] & skywidthmask;''')
 if mode=='farwalls':
  wallcolors()
  p=Path('src/r_draw.c');p.write_text('#include <stdint.h>\n#include "r87_wallcolors.h"\n'+p.read_text())
  patch('src/r_draw.c','''    R20_COUNT(tex->overlapped ? R20C_WALL_COMPOSITE :''','''    /* The source remains valid for R66's next-column reuse. */
    if(dcvars->fracstep>=4096u){
        dcvars->source=r87_wallcols[texture];
        R20_WALL_DRAW(dcvars);return;
    }
    R20_COUNT(tex->overlapped ? R20C_WALL_COMPOSITE :''')
  patch('src/r22_video.inc','''static void R42_DrawPackedWall(const draw_column_vars_t *v)
{''','''void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v);
static void R42_DrawPackedWall(const draw_column_vars_t *v)
{
    if(v->fracstep>=4096u){
        uint8_t c=v->source[0];if(v->colormap)c=v->colormap[c];
        R_DrawColumnFlat(c,v);return;
    }''')
 if mode=='vhalf':
  p=Path('src/r60_pair_wall.s');p.write_text(halfkernel(p.read_text()))
 if mode=='decor':
  patch('src/r_draw.c','''    fixed_t xc = FixedMulAngle(tr_x, viewcos);''','''    if(!(thing->flags & (MF_SHOOTABLE|MF_MISSILE|MF_SPECIAL)) &&
       ((uint32_t)tr_x+384UL*FRACUNIT>768UL*FRACUNIT ||
        (uint32_t)tr_y+384UL*FRACUNIT>768UL*FRACUNIT))return;
    fixed_t xc = FixedMulAngle(tr_x, viewcos);''')
 if mode=='sprites':
  patch('src/r_draw.c','''typedef void (*R_DrawColumn_f)(const draw_column_vars_t *dcvars);''','''typedef void (*R_DrawColumn_f)(const draw_column_vars_t *dcvars);
static void R87_SpriteFlat(const draw_column_vars_t *v){
    uint8_t c=v->source[0];if(v->colormap)c=v->colormap[c];
    R_DrawColumnFlat(c,v);
}''')
  patch('src/r_draw.c','''            dcvars->source =  (const byte __far*)column + 3;''','''            dcvars->source =  (const byte __far*)column + 3;
            if(colfunc==R87_SpriteFlat)dcvars->source+=column->length>>1;''')
  patch('src/r_draw.c','''    if (!dcvars.colormap)   // NULL colormap = shadow draw''','''    if(dcvars.colormap && vis->scale<FRACUNIT/6)colfunc=R87_SpriteFlat;
    if (!dcvars.colormap)   // NULL colormap = shadow draw''')
 if mode=='ai':
  patch('src/p_enemy2.c','''void A_Look(mobj_t __far* actor)
{''','''static int R87_DeferDecision(const mobj_t *a){
    if(!_g_player.mo || !((_g_leveltime+a->type)&3u))return 0;
    uint32_t dx=(uint32_t)a->x-(uint32_t)_g_player.mo->x;
    uint32_t dy=(uint32_t)a->y-(uint32_t)_g_player.mo->y;
    return dx+512UL*FRACUNIT>1024UL*FRACUNIT || dy+512UL*FRACUNIT>1024UL*FRACUNIT;
}
void A_Look(mobj_t __far* actor)
{
    if(R87_DeferDecision(actor))return;''')
  patch('src/p_enemy2.c','''    if (!actor->target || !(actor->target->flags&MF_SHOOTABLE))''','''    if(actor->target && actor->target->health>0 &&
       !(actor->flags&MF_JUSTATTACKED) && R87_DeferDecision(actor))goto r87_move;
    if (!actor->target || !(actor->target->flags&MF_SHOOTABLE))''')
  patch('src/p_enemy2.c','''    // chase towards player
''','''r87_move:
    // chase towards player
''')
 p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text();assert "'r85-'" in s and "('all',0)" in s
 p.write_text(s.replace("'r85-'","'r87-'").replace("('all',0)","('%s',0)"%mode))
 print('R87',mode,'on R85 all; non-control modes use screen-anchored sky')
if __name__=='__main__':main()
