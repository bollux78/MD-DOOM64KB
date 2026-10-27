#!/usr/bin/env python3
"""R77 disposable patch: shadowed stone menu + revised Hybrid Blue CRAM."""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r76.py'],check=True)
p=Path('src/r22_video.inc');s=p.read_text()
needle='static uint8_t r59_color_mode;\nstatic uint8_t r59_color_dirty;'
assert s.count(needle)==1
s=s.replace(needle,'''#if defined(DOOM_R77_MENU)
/* Keep byte state together rather than paying common-symbol alignment gaps.
 * Full byte fields preserve R59 semantics; no per-pixel bitfield decoding. */
static struct {uint8_t mode,dirty,palette;} r77_color_state;
#define r59_color_mode (r77_color_state.mode)
#define r59_color_dirty (r77_color_state.dirty)
#define r77_last_palette (r77_color_state.palette)
typedef char r77_color_state_size[(sizeof(r77_color_state)==3u)?1:-1];
#else
'''+needle+'''
#endif''')
needle='static uint8_t r22_overlay_dirty,r22_text_this_frame;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R77_MENU)
static void R77_MenuEnter(void);
static void R77_MenuLeave(void);
static uint16_t R77_MenuWord(uint16_t x,uint8_t c);
#endif''')
needle='    R20_StopVideo();\n    uint16_t sr=R22_Lock();\n    /* Only rows0..21:'
assert s.count(needle)==1
s=s.replace(needle,'''    R20_StopVideo();
#if defined(DOOM_R77_MENU)
    if(r22_overlay_dirty==2u)R77_MenuLeave();
#endif
    uint16_t sr=R22_Lock();
    /* Only rows0..21:''')
needle='*data=0x8000u+(uint16_t)TILE_FONT_INDEX+c-32;'
assert s.count(needle)==1
s=s.replace(needle,'''*data=
#if defined(DOOM_R77_MENU)
        (plane==VDP_WINDOW && r22_overlay_dirty==2u && R76_InGameMenu())?
            R77_MenuWord((uint16_t)(x-1u),c):
#endif
        (uint16_t)(0x8000u+(uint16_t)TILE_FONT_INDEX+c-32);''')
needle='            R40B_ResetNativeText();\n            r22_overlay_dirty=2u;'
assert s.count(needle)==1
s=s.replace(needle,'''            R40B_ResetNativeText();
#if defined(DOOM_R77_MENU)
            R77_MenuEnter();
#endif
            r22_overlay_dirty=2u;''')
start=s.index('if(y>0 && R76_InGameMenu())');end=s.index('    /* Window is independently',start)
part=s[start:end]
needle='VDP_setWindowHPos(TRUE,0);VDP_setWindowVPos(FALSE,0);'
assert part.count(needle)==1
part=part.replace(needle,'''#if defined(DOOM_R77_MENU)
        VDP_setWindowHPos(FALSE,0);VDP_setWindowVPos(FALSE,22);
#else
        VDP_setWindowHPos(TRUE,0);VDP_setWindowVPos(FALSE,0);
#endif''')
s=s[:start]+part+s[end:]
needle='    if(p<0)p=0;if(p>13)p=13;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R77_MENU)
    r77_last_palette=(uint8_t)p;
#endif''')
needle='#include "hud_wad.inc"'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R77_MENU)
#include "r77_menu.inc"
#endif''')
p.write_text(s)
p=Path('src/r22_video.inc');s=p.read_text()
needle='    R20_StopVideo();r22_text_this_frame=0;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R77_MENU)
    /* Restore SH/CRAM before title art, mode changes or gameplay touch VRAM. */
    if(r22_overlay_dirty==2u && !R76_InGameMenu())R22_ClearOverlay();
#endif''')
needle='    R20_StopVideo();VDP_setScreenWidth320();VDP_setPlaneSize(64,32,FALSE);'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R77_MENU)
    VDP_setHilightShadow(FALSE);
#endif''')
p.write_text(s)
p=Path('src/m_text.c');s=p.read_text().replace('"Hybrid Blue","A2 Full"','"Hybrid Blue+","A2 Full"');p.write_text(s)
p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text()
needle='                        python3 scripts/lab/test_r76_profiles.py; or exit 1'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
                        python3 scripts/lab/gen_r77_profiles.py; or exit 1
                        python3 scripts/lab/test_r77.py --generated; or exit 1''')
needle="set defs $defs '-DDOOM_R76_PROFILES' '-DDOOM_R76_MENU_STABLE'"
assert s.count(needle)==1
s=s.replace(needle,needle+" '-DDOOM_R77_MENU'")
p.write_text(s)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
s=s.replace('r76-col-','r77-col-')
needle="            shutil.copy2(work/'src/r76_profiles_report.json',dest/(name+'-profiles-report.json'))"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
            for file in ('r77_profiles_report.json','r77_shadow_report.json','r77_shadow_pairs.csv','r77_blue_comparison.csv'):
                shutil.copy2(work/'src'/file,dest/(name+'-'+file))''')
needle="        assert '-DDOOM_R76_MENU_STABLE' in contents.split(),name"
s=s.replace(needle,needle+"\n        assert '-DDOOM_R77_MENU' in contents.split(),name")
p.write_text(s)
print('PASS R77 shadow stone menu patch, no highlight operators, two HUD ROMs')
