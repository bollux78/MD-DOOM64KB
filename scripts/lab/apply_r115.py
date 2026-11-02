#!/usr/bin/env python3
"""R115 dbuf (after the R113 hilut chain): double-buffered framebuffer during plain gameplay.

Why: the main loop waited (R22_BeginFrame -> R20_StopVideo) for the VBlank DMA of the previous
frame before drawing the next one (~4% of frame time in the R110 profile).
How:
  - A second 3,344-byte pixel buffer is taken from the Doom zone at the end of P_SetupLevel
    (PU_LEVEL, freed with the level), only if the zone keeps a safe margin afterwards
    (largest block >= buffer+64 and total free >= buffer+5632). Otherwise the level runs
    single-buffered exactly as R113.
  - Renderer writes go to r115_draw; the VBlank DMA reads r115_show (set when the frame is
    posted). After posting, the draw pointer flips to the other buffer, whose DMA has already
    completed (I_FinishUpdate waits for it). R22_BeginFrame no longer waits in that case.
  - Double buffering runs only in GS_LEVEL without menu/overlay/native art/colour reload. On
    entering it, the primary buffer (with its pair attribute words) is copied to the second one;
    on leaving it, the last shown frame is copied back, so menus, Shadow toggles, crop changes and
    saves keep using the single primary buffer as before.
  - E1M6 at Ultra-Violence/Nightmare spawns the Hurt Me Plenty thing set (zone survey R114:
    UV leaves 2.7 KB, HMP 9.7 KB). Damage, ammo, speed and respawn keep the chosen skill.
BSS: +14 bytes.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


V = 'src/r22_video.inc'
rep(V, 'static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;',
       'static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;\n'
       '/* R115: draw/show pointers (both = r22_fb.pixels when single-buffered). */\n'
       'static uint8_t *r115_draw=r22_fb.pixels;\nstatic uint8_t *volatile r115_show=r22_fb.pixels;\n'
       'static uint8_t *r115_fb2;\nstatic uint8_t r115_db;')
rep(V, '    R22_Put(r22_fb.pixels,(uint16_t)x,(uint16_t)y,c);', '    R22_Put(r115_draw,(uint16_t)x,(uint16_t)y,c);')
rep(V, '    uint8_t *dst=R80_PIXEL_BYTE(r22_fb.pixels,x,first);', '    uint8_t *dst=R80_PIXEL_BYTE(r115_draw,x,first);', 2)
rep(V, '    return r22_fb.pixels;', '    return r115_draw;', 2)
rep(V, '    uint8_t *dst=R80_PIXEL_BYTE(r22_fb.pixels,x,y0);', '    uint8_t *dst=R80_PIXEL_BYTE(r115_draw,x,y0);')
rep(V, '    const uint16_t *srca=(const uint16_t *)(const void *)(r22_fb.pixels+152);\n    const uint16_t *srcb=(const uint16_t *)(const void *)(r22_fb.pixels+152+76);',
       '    const uint16_t *srca=(const uint16_t *)(const void *)(r115_show+152);\n    const uint16_t *srcb=(const uint16_t *)(const void *)(r115_show+152+76);')
rep(V, '        R92_ShadowPass((uint16_t *)(void *)r22_fb.pixels,r91_joint[r59_color_mode-1u],',
       '        R92_ShadowPass((uint16_t *)(void *)r115_draw,r91_joint[r59_color_mode-1u],')
# Post the drawn buffer, then flip.
rep(V, '''    __asm__ volatile("":::"memory");r22_ready=1;
#if defined(TIMEDEMO) || defined(DOOM_R50_PLAY_BENCH)''', '''    r115_show=r115_draw;
    __asm__ volatile("":::"memory");r22_ready=1;
    if(r115_db)r115_draw=(r115_draw==r22_fb.pixels)?r115_fb2:r22_fb.pixels;
#if defined(TIMEDEMO) || defined(DOOM_R50_PLAY_BENCH)''')
# BeginFrame: wait only when the draw buffer may be pending.
rep(V, '''void R22_BeginFrame(void){
    /* Complete the old flip before VDP use, retaining the displayed menu
       throughout title/raster work. Text replacement happens just-in-time. */
    R20_StopVideo();r22_text_this_frame=0;''', '''void R22_BeginFrame(void){
    /* R115: in plain gameplay with a second buffer the draw buffer is never the pending one. */
    const uint8_t r115_want=(uint8_t)(r115_fb2 && _g_gamestate==GS_LEVEL && !_g_menuactive
        && r35_native_active<0 && !r59_color_dirty && !r22_overlay_dirty);
    if(!(r115_want && r115_db)){
    /* Complete the old flip before VDP use, retaining the displayed menu
       throughout title/raster work. Text replacement happens just-in-time. */
    R20_StopVideo();
        if(r115_want){                       /* enter: primary (attributes + image) -> second */
            memcpy(r115_fb2,r22_fb.pixels,R22_FB_BYTES);
            r115_draw=r115_fb2;r115_db=1;
        }else if(r115_db){                   /* leave: last shown frame -> primary */
            if(r115_show!=r22_fb.pixels)memcpy(r22_fb.pixels,(const void*)r115_show,R22_FB_BYTES);
            r115_draw=r22_fb.pixels;r115_show=r22_fb.pixels;r115_db=0;
        }
    }
    r22_text_this_frame=0;''')
rep(V, '    r22_fb.before=r22_fb.after=R22_GUARD;\n',
       '    r22_fb.before=r22_fb.after=R22_GUARD;\n    r115_draw=r22_fb.pixels;r115_show=r22_fb.pixels;r115_db=0;\n')
# Level hooks (defined here, called from p_setup.c).
s = Path(V).read_text()
s += '''
/* R115 level hooks. */
extern uint32_t R115_ZoneTotal(void);
extern uint32_t R115_ZoneLargest(void);
void R115_LevelEnd(void){
    if(!r115_fb2 && !r115_db)return;
    R20_StopVideo();
    if(r115_show!=r22_fb.pixels)memcpy(r22_fb.pixels,(const void*)r115_show,R22_FB_BYTES);
    r115_draw=r22_fb.pixels;r115_show=r22_fb.pixels;r115_db=0;r115_fb2=0;
}
void R115_LevelStart(void){
    const uint32_t need=(uint32_t)R22_FB_BYTES+16u;
    r115_fb2=0;
    if(R115_ZoneLargest()>=need+64u && R115_ZoneTotal()>=need+5632u)
        r115_fb2=(uint8_t*)Z_CallocLevel(R22_FB_BYTES);
}
'''
Path(V).write_text(s)
if 'z_zone.h' not in s:
    rep(V, '#include "w_wad.h"\n', '#include "w_wad.h"\n#include "z_zone.h"\n')

Z = 'src/z_zone.c'; s = Path(Z).read_text()
s += '\nuint32_t R115_ZoneTotal(void){return Z_GetTotalFreeMemory();}\nuint32_t R115_ZoneLargest(void){return Z_GetLargestFreeBlockSize();}\n'
Path(Z).write_text(s)

P = 'src/p_setup.c'
rep(P, '''    R22_MapMark(map,0);
    P_FreeLevelData();''', '''    R22_MapMark(map,0);
    {   extern void R115_LevelEnd(void); R115_LevelEnd(); }
    /* R115: E1M6 at UV/Nightmare spawns the HMP thing set (zone headroom). */
    r115_spawnskill=(uint8_t)((map==6 && _g_gameskill>=sk_hard)?sk_medium:_g_gameskill);
    P_FreeLevelData();''')
rep(P, '''    P_MapEnd();R22_MapMark(map,13);''', '''    P_MapEnd();R22_MapMark(map,13);
    {   extern void R115_LevelStart(void); R115_LevelStart(); }''')
rep(P, '    int16_t bit=_g_gameskill<=sk_easy?1:_g_gameskill==sk_medium?2:4;',
       '    int16_t bit=r115_spawnskill<=sk_easy?1:r115_spawnskill==sk_medium?2:4;')
rep(P, '#include "r22_blocklinks.h"\n', '#include "r22_blocklinks.h"\nuint8_t r115_spawnskill; /* R115: skill used for the spawn filter */\n')
R = 'src/r24_romthings.c'
rep(R, '    int bit=_g_gameskill<=sk_easy?1:_g_gameskill==sk_medium?2:4;',
       '    extern uint8_t r115_spawnskill;\n    int bit=r115_spawnskill<=sk_easy?1:r115_spawnskill==sk_medium?2:4;')
M = 'src/p_mobj.c'
rep(M, '''    if (_g_gameskill == sk_baby || _g_gameskill == sk_easy ?
            !(mthing->options & MTF_EASY) :
            _g_gameskill == sk_hard || _g_gameskill == sk_nightmare ?''', '''    extern uint8_t r115_spawnskill;
    if (r115_spawnskill == sk_baby || r115_spawnskill == sk_easy ?
            !(mthing->options & MTF_EASY) :
            r115_spawnskill == sk_hard || r115_spawnskill == sk_nightmare ?''')
# Host test harness extracts R22_Plot/R_DrawColumnSprite with its own r22_fb.
rep('scripts/lab/test_r22_pixel4.py', 'static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;\n',
    'static struct {uint32_t before;uint8_t pixels[R22_FB_BYTES];uint32_t after;} r22_fb;\n#define r115_draw (r22_fb.pixels)\n')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r113-'" in s and "('hilut', 1)" in s
p.write_text(s.replace("'r113-'", "'r115-'").replace("('hilut', 1)", "('dbuf', 1)"))
print('R115 dbuf')
