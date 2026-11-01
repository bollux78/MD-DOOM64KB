#!/usr/bin/env python3
"""R105 twoface -> true 38x22 scene sampling, retaining current Pair-V presentation/UI.

Apply after the exact R105 twoface chain, including R104 SRAM interrupt masking.
No post-render downsampling: BSP, wall columns and sprites use 38x22 geometry.
Each logical sample writes a complete vertical pair in each palette plane.
"""
from pathlib import Path
import shutil

def rep(file, old, new, n=1):
    p=Path(file); s=p.read_text(); assert s.count(old)==n,(file,old[:100],s.count(old))
    p.write_text(s.replace(old,new))

def body(file, signature, replacement, n=1):
    p=Path(file); s=p.read_text(); assert s.count(signature)==n,(file,signature,s.count(signature))
    pos=0
    for _ in range(n):
        a=s.index(signature,pos)+len(signature); start=s.index('{',a); end=start+1; depth=1
        while depth:
            depth+=(s[end]=='{')-(s[end]=='}'); end+=1
        s=s[:start]+'{\n'+replacement+'\n}'+s[end:]; pos=start+len(replacement)+4
    p.write_text(s)

assert 'R98 sprmul' in Path('src/r_draw.c').read_text()
assert 'r104_sr' in Path('src/r22_blocklinks.h').read_text()
assert "('twoface', 1)" in Path('scripts/lab/build_r71a12mul_hud.py').read_text()
shutil.copyfile('scripts/lab/cell8/r105_cell8.h','src/r105_cell8.h')

# Retain the video-format feature flags, but select the existing 38-column projection.
for old,new in (('-DVIEWWINDOWWIDTH=76','-DVIEWWINDOWWIDTH=38'),
                ('-DVIEWWINDOWHEIGHT=44','-DVIEWWINDOWHEIGHT=22'),
                ('-DMAPWIDTH=76','-DMAPWIDTH=38')):
    rep('scripts/build_silent.fish',old,new)
rep('src/r22_video.inc','#if VIEWWINDOWWIDTH != R22_W || VIEWWINDOWHEIGHT != R22_H',
    '#if VIEWWINDOWWIDTH != 38 || VIEWWINDOWHEIGHT != 22')

# Only the renderer sees half-sized crop coordinates. DMA/shadow/UI keep physical coordinates.
rep('src/r_draw.c','#include "r57_viewport.h"', '''#include "r57_viewport.h"
/* Cell8 scene coordinates; r57_view itself remains in physical 4px units. */
#undef R57_XMIN
#undef R57_XEND
#undef R57_YMIN
#undef R57_YEND
#define R57_XMIN (r57_view.xmin / 2)
#define R57_XEND (r57_view.xend / 2)
#define R57_YMIN (r57_view.ymin / 2)
#define R57_YEND (r57_view.yend / 2)
/* R66 is approximate neighbour reuse for 4px columns; every 8px column is independent. */
#undef DOOM_R66_COLPAIR
#include "r105_cell8.h"''')
rep('src/r22_video.inc','static inline void R22_Plot(int16_t x,int16_t y,uint8_t c) {',
    '#include "r105_cell8.h"\nstatic inline void R22_Plot(int16_t x,int16_t y,uint8_t c) {')
body('src/r22_video.inc','static inline void R22_Plot(int16_t x,int16_t y,uint8_t c)', '''    if (!R105_CellVisible(x,y)) return;
    R105_CellStore(r22_fb.pixels,x,y,c,c);''')

# Both fallback sprites and walls resolve the two palette maps once per column.
rep('src/r22_video.inc','void R_DrawColumnSprite(const draw_column_vars_t *v) {', '''static void R105_CellColumn(const draw_column_vars_t *v)
{
    const uint8_t *even=R52_LUT(v->colormap,0), *odd=R52_LUT(v->colormap,1);
    if(even && odd) R105_CellTexture(r22_fb.pixels,v,even,odd,0);
    else R105_CellTexture(r22_fb.pixels,v,R59_CURRENT.wall_even,R59_CURRENT.wall_odd,v->colormap);
}
void R_DrawColumnSprite(const draw_column_vars_t *v) {''')
body('src/r22_video.inc','void R_DrawColumnSprite(const draw_column_vars_t *v)', '    R105_CellColumn(v);')
body('src/r22_video.inc','void R_DrawColumnWall(const draw_column_vars_t *v)', '    R105_CellColumn(v);',2)
body('src/r22_video.inc','void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v)', '''    int16_t y0=v->yl,y1=v->yh;
    if(!R105_CellClip(v->x,&y0,&y1)) return;
    R105_CellFill(r22_fb.pixels,v->x,y0,y1,R59_CURRENT.flat_even[c],R59_CURRENT.flat_odd[c]);''')

# R95 hoisted flat colours and R96 hoisted wall LUTs stay useful at cell granularity.
body('src/r_draw.c','static inline __attribute__((always_inline)) void R95_Fill(uint8_t *fb, int16_t x, int16_t y0, int16_t y1, uint8_t s)',
     '    R105_CellFill(fb,x,y0,y1,s,t);')
rep('src/r_draw.c','int16_t y1, uint8_t s)\n{','int16_t y1, uint8_t s, uint8_t t)\n{')
for c in ('cs','fs'):
    rep('src/r_draw.c',f'(rw_x & 1) ? r95_{c}1 : r95_{c}0);',f'r95_{c}0,r95_{c}1);',6)
body('src/r_draw.c','static inline __attribute__((always_inline)) void R96_WallDraw(const draw_column_vars_t *v)', '''    if(!r96_fb || v->colormap!=r96_cmap) { R_DrawColumnWall(v); return; }
    R105_CellTexture(r96_fb,v,r96_lut[0],r96_lut[1],0);''')

# No 4px R60 kernel is called by the new scene writer; retain its build capability for UI tests.
rep('scripts/lab/build_r71a12mul_hud.py',"'r105-'","'r105-'")
rep('scripts/lab/build_r71a12mul_hud.py',"('twoface', 1)","('cell8', 1)")
rep('scripts/lab/build_r71a12mul_hud.py',"        assert 'R60_WallColumn' in nm, ('R60 linked kernel mismatch', name)",
    "        assert '-DVIEWWINDOWWIDTH=38' in flags[name] and '-DVIEWWINDOWHEIGHT=22' in flags[name]")
# The original packed4 pixel test extracts 4px routines; use the real cell8 writer test instead.
rep('scripts/lab/build_r35_linear.fish','python3 scripts/lab/test_r22_pixel4.py; or exit 1',
    'python3 scripts/lab/test_r105_cell8.py; or exit 1')
print('R105 cell8: 38x22 scene, current UI/assets/Shadow, protected SRAM')
