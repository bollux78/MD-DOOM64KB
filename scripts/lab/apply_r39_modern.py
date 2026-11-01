#!/usr/bin/env python3
"""R105 twoface -> original R39f tile-word renderer and colour model, current UI."""
from pathlib import Path
import shutil,re

def rep(file,old,new,n=1):
    p=Path(file);s=p.read_text();assert s.count(old)==n,(file,old[:90],s.count(old));p.write_text(s.replace(old,new))

def span(s,sig,pos=0):
    a=s.index(sig,pos);start=s.index('{',a+len(sig));end=start+1;depth=1
    while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return a,start,end

def body(file,sig,new,n=1):
    p=Path(file);s=p.read_text();assert s.count(sig)==n,(file,sig,s.count(sig));pos=0
    for _ in range(n):
        a,start,end=span(s,sig,pos);s=s[:start]+'{\n'+new+'\n}'+s[end:];pos=start+len(new)+4
    p.write_text(s)

V='src/r22_video.inc';D='src/r_draw.c';B='scripts/lab/build_r71a12mul_hud.py';F='scripts/lab/build_r35_linear.fish'
assert 'r104_sr' in Path('src/r22_blocklinks.h').read_text()
assert "('twoface', 1)" in Path(B).read_text()
for name in ('r39m_draw.h','r39m_scene.inc','r39m_raster.inc'):
    shutil.copyfile('scripts/lab/r39modern/'+name,'src/'+name)

for old,new in (('-DVIEWWINDOWWIDTH=76','-DVIEWWINDOWWIDTH=38'),('-DVIEWWINDOWHEIGHT=44','-DVIEWWINDOWHEIGHT=22'),('-DMAPWIDTH=76','-DMAPWIDTH=38')):
    rep('scripts/build_silent.fish',old,new)
rep(V,'#if VIEWWINDOWWIDTH != R22_W || VIEWWINDOWHEIGHT != R22_H','#if VIEWWINDOWWIDTH != 38 || VIEWWINDOWHEIGHT != 22')
rep(D,'#include "r57_viewport.h"','''#include "r57_viewport.h"
#undef R57_XMIN
#undef R57_XEND
#undef R57_YMIN
#undef R57_YEND
#define R57_XMIN (r57_view.xmin/2)
#define R57_XEND (r57_view.xend/2)
#define R57_YMIN (r57_view.ymin/2)
#define R57_YEND (r57_view.yend/2)
#undef DOOM_R66_COLPAIR
#include "r39m_draw.h"
extern uint8_t *R39M_Framebuffer(void);
extern uint16_t R39M_FlatCell(uint8_t c);
extern void R39M_DrawFast(const draw_column_vars_t *v,const uint16_t *map);''')
rep(D,'void R_RenderPlayerView (player_t* player)\n{','''void __attribute__((noinline,used)) R39M_BeginScene(void){__asm__ volatile("nop":::"memory");}
void R_RenderPlayerView (player_t* player)
{
    R39M_BeginScene();''')
# Preserve four original scene palettes and two HUD palettes with a bottom-gap raster switch.
rep('src/r57_viewport.h','result.hcrop=h;result.vcrop=v;','v=v<8?8:v; /* reserve the scene/HUD palette-switch gap */\n    result.hcrop=h;result.vcrop=v;')
rep(V,'static volatile uint16_t r22_ready;','static volatile uint16_t r22_ready;\n#include "r39m_scene.inc"')
body(V,'uint8_t R59_ColorMode(void)','    return (uint8_t)R39F_DitherMode();')
body(V,'void R59_ChangeColor(int16_t right)','    uint16_t m=R39F_DitherMode();R39F_SetDitherMode((m+(right?1u:2u))%3u);')
body(V,'void R64A_FrameBegin(void)','    /* Tile-word backend has no Pair-V context to resolve. */')
body(V,'void R64A_FrameEnd(void)','    /* Tile-word backend has no Pair-V context to invalidate. */')
body(V,'static inline void R22_Plot(int16_t x,int16_t y,uint8_t c)', '''    int16_t lo=y,hi=y;if(!R39M_Clip(x,&lo,&hi))return;
    ((uint16_t *)(void *)r22_fb.pixels)[(uint16_t)y*38u+(uint16_t)x]=colorcell[c];''')
# Automap passes original Doom colour indices instead of the old packed4 nibble.
rep(V,'c=r22_color[c];\n','/* R39f: c remains an original Doom colour index. */\n')
body(V,'void R_DrawColumnSprite(const draw_column_vars_t *v)', '    R39M_DrawFast(v,R39M_Map(v->colormap));')
body(V,'void R_DrawColumnWall(const draw_column_vars_t *v)', '    R39M_DrawFast(v,R39M_Map(v->colormap));',2)
body(V,'void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v)', '''    int16_t lo=v->yl,hi=v->yh;if(!R39M_Clip(v->x,&lo,&hi))return;
    R39M_Fill(r22_fb.pixels,v->x,lo,hi,colorcell[c]);''')
body(V,'uint8_t *R96_WallSetup(const uint8_t *colormap,const uint8_t **lut)', '''    const uint16_t *m=R39M_Map(colormap);lut[0]=(const uint8_t *)m;lut[1]=(const uint8_t *)m;
    return m?r22_fb.pixels:0;''')
body(D,'static inline __attribute__((always_inline)) void R96_WallDraw(const draw_column_vars_t *v)', '''    if(!r96_fb || v->colormap!=r96_cmap){R_DrawColumnWall(v);return;}
    R39M_DrawFast(v,(const uint16_t *)(const void *)r96_lut[0]);''')
body(D,'static inline __attribute__((always_inline)) void R95_Fill(uint8_t *fb, int16_t x, int16_t y0, int16_t y1, uint8_t s)', '    R39M_Fill(fb,x,y0,y1,s);')
rep(D,'int16_t y1, uint8_t s)\n{','int16_t y1, uint16_t s)\n{')
p=Path(D);s=p.read_text();a=s.index('    /* R95: flat samples are constant');b=s.index('    extern uint8_t *R96_WallSetup',a)
s=s[:a]+'''    uint8_t *const r95_fb=R39M_Framebuffer();
    const uint16_t r95_cs0=R39M_FlatCell((uint8_t)ceilingplane_color),r95_cs1=r95_cs0;
    const uint16_t r95_fs0=R39M_FlatCell((uint8_t)floorplane_color),r95_fs1=r95_fs0;
'''+s[b:];p.write_text(s)

# Load the ORIGINAL R39 solid/checker/vertical tiles verbatim, at original tile base 16.
old=Path('src/i_genesisv.c').read_text();_,a,b=span(old,'static void I_BuildSolidTiles(void)')
body(V,'static void R47_LoadPairTiles(void)\n',old[a+1:b-1])
body(V,'static void R47_ClearPairBuffer(void)', '''    uint16_t *w=(uint16_t *)(void *)r22_fb.pixels;
    for(uint16_t i=0;i<R22_FB_BYTES/2u;i++)w[i]=16u;''')
body(V,'static void R22_Palette(int8_t p)', '''    if(p<0)p=0;if(p>=GENPAL_NSUB)p=GENPAL_NSUB-1;
    uint16_t sr=R22_Lock();
    r39m_palette=(uint8_t)p;PAL_setColors(0,genpal_cram[(uint8_t)p],64,CPU);
    VDP_setHilightShadow(FALSE);R22_Unlock(sr);''')

# One tile-word DMA per row, no second scene plane, no Pair-V conversion or attributes.
body(V,'void R20_VBlankVideo(void)', '''    if(r22_ready && r22_queued_pal!=100)R22_Palette(r22_queued_pal);
    R39M_FramePalette();
    if(!r22_ready)return;
    uint16_t line=(*(volatile uint16_t*)0xC00008)>>8;if(line<224||line>232)return;
    uint16_t sr=R22_Lock();bool bus=Z80_getAndRequestBus(TRUE);VDP_setAutoInc(2);
    volatile uint16_t *ctrl=(volatile uint16_t *)0xC00004;
    const uint16_t *src=(const uint16_t *)(const void *)r22_fb.pixels;
    for(uint16_t y=r92_rect.y0;y<r92_rect.y1;y++){
        uint16_t count=(uint16_t)(r92_rect.x1-r92_rect.x0);
        uint32_t a=((uint32_t)(uintptr_t)(src+y*38u+r92_rect.x0))>>1;
        *ctrl=0x9300|count;*ctrl=0x9400;
        *ctrl=0x9500|(a&255);*ctrl=0x9600|((a>>8)&255);*ctrl=0x9700|((a>>16)&127);
        volatile uint32_t cmd=VDP_DMA_VRAM_ADDR(VDP_BG_A+y*128u+r92_rect.x0*2u);
        volatile uint16_t *words=(volatile uint16_t *)&cmd;*ctrl=words[0];
        __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
    }
    if(!bus)Z80_releaseBus();r22_ready=0;R22_Unlock(sr);''')
rep(V,'#include "hud_wad.inc"','#include "hud_wad.inc"\n#include "r39m_raster.inc"')
rep('src/hud_wad.inc','    PAL_setColors(48, hudw_pal, 16, CPU);',
    '    sr=R22_Lock();\n    PAL_setColors(48, hudw_pal, 16, CPU);')
rep('src/hud_wad.inc','    PAL_setColors(32, hudw_fpal, 16, CPU);',
    '    PAL_setColors(32, hudw_fpal, 16, CPU);R22_Unlock(sr);')
rep('src/r77_menu.inc','static void R77_MenuEnter(void)\n{',
    'static void R77_MenuEnter(void)\n{\n    VDP_setHInterrupt(FALSE);')
rep('src/r35_native4.inc','static bool R35_DrawNative4(int16_t lump)\n{',
    'static bool R35_DrawNative4(int16_t lump)\n{\n    VDP_setHInterrupt(FALSE);')
rep(V,'    VDP_setHInterrupt(FALSE);','    r39m_scene_active=0;VDP_setHInterrupt(FALSE);')
rep(V,'void I_FinishUpdate(void){','void I_FinishUpdate(void){\n    r39m_scene_active=(_g_gamestate==GS_LEVEL);')
# The nominal Pair-V capability flag remains for shared UI storage guards, never for drawing.
rep(V,'VDP_setHorizontalScroll(BG_B,desired?-20:4);','VDP_setHorizontalScroll(BG_B,desired?-24:0);')
rep(V,'VDP_setHorizontalScroll(BG_B,4);','VDP_setHorizontalScroll(BG_B,0);')
rep(V,'VDP_setHorizontalScroll(BG_B,-20);','VDP_setHorizontalScroll(BG_B,-24);')
rep('src/r35_native4.inc','VDP_setHorizontalScroll(BG_B,4);','VDP_setHorizontalScroll(BG_B,0);')
for file in (V,'src/r35_native4.inc'):
    p=Path(file);s=p.read_text()
    for bank in (0,1):
        s=re.sub(r'PAL_setColors\('+str(bank*16)+r',R79_PAL'+str(bank)+r'\[0\],16,CPU\);',
                 'R22_Palette(0);' if bank==0 else '/* R39f restores all four palette banks together. */',s)
    p.write_text(s)

# Restore the original dither selector; remove Pair-V A2/L3 and Shadow selectors.
p=Path('src/m_text.c');s=p.read_text()
s=s.replace('static void M_R92Shadow(int16_t c){(void)c;R92_SetShadow(!R92_ShadowOn());}','')
s=s.replace('  shadow_mode,\n','').replace('  color_mode,\n','')
s=s.replace('  {2,"Shadow:",      M_R92Shadow},\n','').replace('  {2,"Color mode:", M_ChangeColorMode},\n','')
s=s.replace(' V_DrawString(OptionsDef.x+13,OptionsDef.y+LINEHEIGHT*shadow_mode,12,R92_ShadowOn()?"On ":"Off");\n','')
a=s.index('    #if defined(DOOM_R76_PROFILES)',s.index('static void M_DrawOptions(void)\n{'))
b=s.index('    /* Fixed-width size label',a)
s=s[:a]+'#endif\n'+s[b:];p.write_text(s)
rep('src/r22_benchmark.inc','    VDP_drawText(R92_ShadowOn()?"SHADOW: ON":"SHADOW: OFF",5,7);',
    '    VDP_drawText(R39F_DitherMode()==0?"DITHER: OFF":R39F_DitherMode()==1?"DITHER: CHECKER":"DITHER: VERTICAL",5,7);')
rep('src/r22_benchmark.inc','#include "r89_ai.h"','#include "r89_ai.h"\n#include "r39f_dither.h"')

rep(B,"('twoface', 1)","('r39modern', 0)")
rep(B,"'DOOM_R79_SHADOW':str(strength)","'DOOM_R79_SHADOW':'0','DOOM_R39D_DITHER_TOGGLE':'1','DOOM_R39F_DITHER3':'1'")
rep(B,"        assert 'R60_WallColumn' in nm, ('R60 linked kernel mismatch', name)",
    "        assert 'R39F_SetDitherMode' in nm and '-DVIEWWINDOWWIDTH=38' in flags[name]")
# Enable generation of original 16-bit colour LUTs in the scene-specific build path.
rep(F,'        set -gx DOOM_CELL_LUT 0','        set -gx DOOM_CELL_LUT 1')
rep(F,'and contains -- $v cell-play cell-perf cell-profperf\n        set defs $defs \'-DDOOM_R35D_CHECKER\'',
    'and contains -- $v cell-play cell-perf cell-profperf pixel4-play pixel4-perf\n        set defs $defs \'-DDOOM_R35D_CHECKER\'')
rep(F,'        if contains -- $v cell-play cell-perf\n            set defs $defs \'-DDOOM_R39D_DITHER_TOGGLE\'',
    '        if contains -- $v cell-play cell-perf pixel4-play pixel4-perf\n            set defs $defs \'-DDOOM_R39D_DITHER_TOGGLE\'')
rep(F,"        if not contains -- $v cell-play cell-perf\n            echo 'R39f", "        if not contains -- $v cell-play cell-perf pixel4-play pixel4-perf\n            echo 'R39f")
# Replace incompatible packed4 source tests with a tile-word writer oracle; retain shared tests.
rep(F,'python3 scripts/lab/test_r22_pixel4.py; or exit 1','python3 scripts/lab/test_r39_modern.py; or exit 1')
rep(F,'python3 scripts/lab/test_r59_colorview.py; or exit 1','python3 scripts/lab/test_r39_modern.py --source; or exit 1')
rep('scripts/lab/test_r76_profiles.py',"assert 'A2 Full' in menu and 'L3 Detail' in menu and 'Hybrid Blue' not in menu and 'HN Smooth' not in menu",
    "assert 'r39f_mode_names' in menu and '{2,\"Shadow:\"' not in menu and '{2,\"Color mode:\"' not in menu")
print('R39 modern: original 4-palette tile-word engine, tri-dither, current UI and protected SRAM')
