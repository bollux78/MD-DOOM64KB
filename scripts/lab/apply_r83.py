#!/usr/bin/env python3
"""Two independent R83 candidates on R82 (R81 + R80 P1/F1), no new WRAM."""
from pathlib import Path
import os,re
ROOT=Path(__file__).resolve().parents[2]
SPRITE='void R_DrawColumnSprite(const draw_column_vars_t *v) {'
WALL='static void R42_DrawPackedWall(const draw_column_vars_t *v)\n'
SPR_PTR='    uint8_t *dst=R22_PixelByte(r22_fb.pixels,(uint16_t)x,(uint16_t)first);\n'
SPR_COUNT='    uint16_t count=(uint16_t)(n+1u);\n'
SPR_NEW='''#if defined(DOOM_R60_PAIR_ASM)
    /* R83 sprite P1/F1: the existing Pair-V DBRA kernel has the same
     * two-texel phase progression and preserves clipped neighbour nibbles.
     * Keep the original C path for an uncomposed colormap. */
    if(!colormap && count>=2u){
        R60_WallDraw(dst,source,r52map,frac,step,count,(uint16_t)(first&1u));
        return;
    }
#endif
'''
CLIP_OLD='''    int16_t x=v->x, y0=v->yl, y1=v->yh;
    if(y1<y0 || (uint16_t)x>=R22_W) return;
    int16_t border=cx->border;
    if(x>=cx->xend)return;
    if(y1>=cx->yend)y1=(int16_t)(cx->yend-1);
    if(x<cx->xmin)return;
    int16_t first=y0;
'''
CLIP_NEW='''    int16_t x=v->x, y0=v->yl, y1=v->yh;
    /* R83 wall clipping: intersect context and physical limits once.
     * R64A_Fill supplies 0<=xmin<=xend, border>=0; inactive ends are 32767. */
    const int16_t xend=cx->xend<R22_W?cx->xend:R22_W;
    if(y1<y0 || (uint16_t)(x-cx->xmin)>=(uint16_t)(xend-cx->xmin))return;
    int16_t border=cx->border;
    const int16_t yend=cx->yend<R22_H?cx->yend:R22_H;
    if(y1>=yend)y1=(int16_t)(yend-1);
    int16_t first=y0;
'''
FRAC_OLD='''    uint16_t f=(uint16_t)((v->texturemid>>7)+(y0-CENTERY)*v->fracstep);
    f=(uint16_t)(f+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)v->fracstep));
'''
FRAC_NEW='''    /* Modulo 65536, (y0-CENTERY)*step+(first-y0)*step is
     * (first-CENTERY)*step. One multiply instead of the two-stage skip. */
    uint16_t f=(uint16_t)((v->texturemid>>7)+(first-CENTERY)*v->fracstep);
'''
def region(s,start,end):
 a=s.index(start);b=s.index(end,a);return a,b,s[a:b]
def apply_sprite(s):
 assert 'R83 sprite P1/F1' not in s,'R83 sprite already applied'
 # R80 emitted the tables below the sprite function; move that unchanged
 # block above its new caller, retaining a single ROM copy.
 from apply_r80_performance import block
 tables=block();assert s.count(tables)==1,'R82 P1 table block absent/changed'
 s=s.replace(tables,'');assert s.count(SPRITE)==1
 s=s.replace(SPRITE,tables+SPRITE)
 a,b,t=region(s,SPRITE,'/* R42 Q2:')
 assert t.count(SPR_PTR)==1 and t.count(SPR_COUNT)==1
 t=t.replace(SPR_PTR,'    uint8_t *dst=R80_PIXEL_BYTE(r22_fb.pixels,x,first);\n')
 t=t.replace(SPR_COUNT,SPR_COUNT+SPR_NEW)
 return s[:a]+t+s[b:]
def apply_wall(s):
 assert 'R83 wall clipping' not in s,'R83 wall clip already applied'
 a,b,t=region(s,WALL,'void R_DrawColumnWall(')
 assert t.count(CLIP_OLD)==1 and t.count(FRAC_OLD)==1
 t=t.replace(CLIP_OLD,CLIP_NEW).replace(FRAC_OLD,FRAC_NEW)
 old='    if(y1>=R22_H) y1=R22_H-1;\n';assert t.count(old)==1
 t=t.replace(old,'#if !defined(DOOM_R64A_PROLOGUE)\n'+old+'#endif\n')
 return s[:a]+t+s[b:]
def rename(s,tag):
 assert re.fullmatch('[a-z0-9-]+',tag)
 old="('r81-'+label+'-'+suffix";labels="for label,strength in (('menu',0),)"
 assert s.count(old)==1 and s.count(labels)==1,'R81 builder names changed'
 return s.replace(old,"('r83-'+label+'-'+suffix").replace(labels,"for label,strength in (('%s',0),)"%tag)
def main():
 mode=os.environ['R83_CANDIDATE'];assert mode in ('sprites','wallclip'),mode
 p=ROOT/'src/r22_video.inc';s=p.read_text()
 assert 'R80-F1' in s and 'DOOM_R80_PIXOFS' in s,'apply on R82 P1+F1, after R81'
 p.write_text((apply_sprite if mode=='sprites' else apply_wall)(s))
 tag='sprite-p1f1' if mode=='sprites' else 'wall-clip'
 p=ROOT/'scripts/lab/build_r71a12mul_hud.py';p.write_text(rename(p.read_text(),tag))
 print('R83 candidate:',tag,'on R82 P1+F1; no added WRAM; separate ROM/header/benchmark names')
if __name__=='__main__':main()
