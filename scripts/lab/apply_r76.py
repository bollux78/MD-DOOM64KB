#!/usr/bin/env python3
"""R76 patch in runner checkout: four complete profiles, persistent Start overlay.
All changes are disposable; stable R71 and tested R75 code remain unchanged.
"""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r75.py'],check=True)

# R76 menu overlay: R75 already holds last 3D VRAM. Replace the repeated
# full WINDOW/BG_B DMA clear with occupancy-based stale-glyph retire.
# The existing R40b bitsets alias the frozen Pair-V framebuffer => 0 new BSS.
p=Path('src/r22_video.inc')
s=p.read_text()
needle='static void R40B_ResetNativeText(void)'
assert s.count(needle)==1
# Insert helper after definitions of R40B occupancy pointers, before text functions.
helper='''#if defined(DOOM_R76_MENU_STABLE)
static inline uint8_t R76_InGameMenu(void){
#if defined(DOOM_R50_MENU_FREEZE)
    return (_g_gamestate==GS_LEVEL && _g_menuactive && !_g_demoplayback);
#else
    /* PERF may still render during menu; framebuffer bitsets are not safe. */
    return 0;
#endif
}
#endif
'''
s=s.replace(needle,helper+needle)
needle='    if(x<0||x>=38||y<0||y>=22)return;\n    /* Window is independently addressable'
assert s.count(needle)==1
s=s.replace(needle,'''    if(x<0||x>=38||y<0||y>=22)return;
#if defined(DOOM_R76_MENU_STABLE)
    if(y>0 && R76_InGameMenu()){
        /* Clear only once on first entry; later changes retire stale glyphs.
         * No repeated VDP DMA blackout of top rows while user navigates. */
        if(r22_overlay_dirty!=2u){
            R22_ClearOverlay();
            R40B_ResetNativeText();
            r22_overlay_dirty=2u; /* 2 marks gameplay persistent overlay */
        }
        uint16_t col=(uint16_t)x;
        const char *scan=s;
        while(*scan && col<R40B_TEXT_W){
            uint16_t i=(uint16_t)(y*R40B_TEXT_W+col++);
            r40b_native_seen[i>>3]|=(uint8_t)(1u<<(i&7));
            ++scan;
        }
        r22_text_this_frame=1u;
        R20_StopVideo();
        uint16_t sr=R22_Lock();
        VDP_setWindowHPos(TRUE,0);VDP_setWindowVPos(FALSE,0);
        R22_Unlock(sr);
        R22_DrawText(VDP_WINDOW,s,(uint16_t)x,(uint16_t)y);
        return;
    }
#endif
    /* Window is independently addressable''')
needle='    R20_StopVideo();r22_text_this_frame=0;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R76_MENU_STABLE)
    if(R76_InGameMenu() && r22_overlay_dirty==2u)
        memset(r40b_native_seen,0,R40B_OCC_BYTES);
#endif''')
needle='void V_ClearViewWindow(void){'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R76_MENU_STABLE)
    if(R76_InGameMenu() && r22_overlay_dirty==2u) return;
#endif''')
needle='static int8_t r22_newpal=100,r22_queued_pal=100;'
assert s.count(needle)==1
func='''#if defined(DOOM_R76_MENU_STABLE)
/* Keep the old text until replacements are drawn; retire only cells that
 * were occupied last frame but not this frame. Uses aliased bitsets, no WRAM. */
void R76_MenuOverlayFinish(void){
    if(!R76_InGameMenu() || r22_overlay_dirty!=2u)return;
    uint16_t sr=R22_Lock();
    volatile uint32_t *ctrl=(volatile uint32_t*)0xC00004;
    volatile uint16_t *data=(volatile uint16_t*)0xC00000;
    VDP_setAutoInc(2);
    for(uint16_t y=1;y<R40B_TEXT_H;y++){
        for(uint16_t x=0;x<R40B_TEXT_W;x++){
            uint16_t i=(uint16_t)(y*R40B_TEXT_W+x);
            uint8_t bit=(uint8_t)(1u<<(i&7));
            if((r40b_native_prev[i>>3]&bit) && !(r40b_native_seen[i>>3]&bit)){
                *ctrl=VDP_WRITE_VRAM_ADDR(VDP_WINDOW+y*128u+x*2u);
                *data=0u;
            }
        }
    }
    R22_Unlock(sr);
    memcpy(r40b_native_prev,r40b_native_seen,R40B_OCC_BYTES);
}
#endif
'''
s=s.replace(needle,func+needle)
# Defer palette/tiles refresh until user closes Options, avoiding a mid-overlay flash.
needle='if(r59_color_dirty && r35_native_active<0){'
assert s.count(needle)==1
s=s.replace(needle,'''if(r59_color_dirty && r35_native_active<0
#if defined(DOOM_R76_PROFILES)
       && !_g_menuactive
#endif
    ){''')
p.write_text(s)

p=Path('src/d_main.c');s=p.read_text()
needle='    M_Drawer();          // menu is drawn even on top of everything'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R76_MENU_STABLE)
    extern void R76_MenuOverlayFinish(void);
    R76_MenuOverlayFinish();
#endif''')
p.write_text(s)

# R73 deliberately omitted R59 palette selector; restore only for R76.
p=Path('src/m_text.c');s=p.read_text()
# Cursor frame is 0/1 and its signed countdown stays in -1..10.
# Keep <=0 behavior at zero while saving two bytes under the strict BSS guard.
old='static int16_t skullAnimCounter;'
assert s.count(old)==1
s=s.replace(old,'static int8_t skullAnimCounter;')
old='static int16_t whichSkull;'
assert s.count(old)==1
s=s.replace(old,'static uint8_t whichSkull;')
old='#if defined(DOOM_R59_COLOR_VIEW) && !defined(DOOM_R73_R53_FIXED)'
assert s.count(old)>=3
s=s.replace(old,'#if defined(DOOM_R59_COLOR_VIEW) && (!defined(DOOM_R73_R53_FIXED) || defined(DOOM_R76_PROFILES))')
old='static const char *const r59_names[6]={"CM6","Balanced","Tolerant","Accents","A4 Tolerant","A4 Accents"};'
assert s.count(old)==1
s=s.replace(old,'''#if defined(DOOM_R76_PROFILES)
    static const char *const r59_names[4]={"Hybrid Blue","A2 Full","L3 Detail","HN Smooth"};
#else
    '''+old+'''
#endif''')
p.write_text(s)

p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text()
needle='                    python3 scripts/lab/inject_r75_hybrid.py; or exit 1'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
                    if set -q DOOM_R76_PROFILES
                        python3 scripts/lab/gen_r76_profiles.py; or exit 1
                        python3 scripts/lab/test_r76_profiles.py; or exit 1
                    end''')
needle="        set defs $defs '-DDOOM_R75_MENU_HOLD'"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        if set -q DOOM_R76_PROFILES
            set defs $defs '-DDOOM_R76_PROFILES' '-DDOOM_R76_MENU_STABLE'
        end''')
p.write_text(s)

p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
i=s.index('VARIANTS = (');j=s.index('\nLABEL =',i)
s=s[:i]+'''VARIANTS = (
    ('r76-col-pf','perf',{'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25',
        'DOOM_R72_FLAT_2D':'0','DOOM_R74_PROFILE':'l','DOOM_R74_FLATS':'f3',
        'DOOM_R75_HYBRID':'near','DOOM_R76_PROFILES':'1'},[]),
    ('r76-col-pl','play',{'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25',
        'DOOM_R72_FLAT_2D':'0','DOOM_R74_PROFILE':'l','DOOM_R74_FLATS':'f3',
        'DOOM_R75_HYBRID':'near','DOOM_R76_PROFILES':'1'},[]),
)'''+s[j:]
s=s.replace('assert len(records) == 8','assert len(records) == 2')
start=s.index("    for name in ('r75-a2-pf'")
stop=s.index(':\n        contents=flags[name]',start)
s=s[:start]+"    for name in ('r76-col-pf','r76-col-pl')"+s[stop:]
needle="        if extra_env.get('DOOM_R75_HYBRID'):"
assert s.count(needle)==1
s=s.replace(needle,'''        if extra_env.get('DOOM_R76_PROFILES'):
            shutil.copy2(work/'src/r76_profiles_report.json',dest/(name+'-profiles-report.json'))
'''+needle)
s=s.replace('assert \'-DDOOM_R75_MENU_HOLD\' in contents.split(),name',
            "assert '-DDOOM_R75_MENU_HOLD' in contents.split(),name\n        assert '-DDOOM_R76_PROFILES' in contents.split(),name\n        assert '-DDOOM_R76_MENU_STABLE' in contents.split(),name")
s=s.replace("print('PASS R75 hybrid 8 ROMs, all HUD, menu hold enabled',flush=True)",
            "print('PASS R76 two HUD ROMs, four complete selectable palettes and persistent menu overlay',flush=True)")
p.write_text(s)
print('R76 source patch complete: full profiles, persistent overlay, two PERF/PLAY ROMs')
