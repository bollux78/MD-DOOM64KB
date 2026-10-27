#!/usr/bin/env python3
"""R79: face side transparency + baseline/two shadow experiment builds."""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r78.py'],check=True)
p=Path('src/r22_video.inc');s=p.read_text()
needle='#define R59_CURRENT (r59_color_tables[r59_color_mode])';assert s.count(needle)==1
s=s.replace(needle,needle+'''
#if defined(DOOM_R79_SHADOW)
#include "r79_shadow_tables.h"
#define R79_PAL0 (r79_pal[r59_color_mode][0])
#define R79_PAL1 (r79_pal[r59_color_mode][1])
#else
#define R79_PAL0 (R59_CURRENT.pal0)
#define R79_PAL1 (R59_CURRENT.pal1)
#endif''')
s=s.replace('R59_CURRENT.pal0[','R79_PAL0[').replace('R59_CURRENT.pal1[','R79_PAL1[')
needle='void I_FinishUpdate(void){';assert s.count(needle)==1
s=s.replace(needle,'''#if defined(DOOM_R79_SHADOW)
#include "r79_shadow.inc"
#endif
'''+needle)
needle='    if(_g_gamestate==GS_LEVEL)R22_HUD();\n    r22_next_bank=0;';assert s.count(needle)==1
s=s.replace(needle,'''    if(_g_gamestate==GS_LEVEL)R22_HUD();
#if defined(DOOM_R79_SHADOW)
    if(_g_gamestate==GS_LEVEL && !R76_InGameMenu()){
        uint8_t p=r22_newpal==100?r77_last_palette:(uint8_t)r22_newpal;
        if(p>13u)p=0;
        R79_Convert((uint16_t *)(void *)r22_fb.pixels,
            r79_map[r59_color_mode][p],r79_cost[r59_color_mode][p]);
        VDP_setHilightShadow(TRUE);
    }
#endif
    r22_next_bank=0;''')
p.write_text(s)
p=Path('src/r35_native4.inc');s=p.read_text().replace('R59_CURRENT.pal0[','R79_PAL0[').replace('R59_CURRENT.pal1[','R79_PAL1[')
s=s.replace('        R20_StopVideo();\n        VDP_setEnable(FALSE);','''        R20_StopVideo();
#if defined(DOOM_R79_SHADOW)
        VDP_setHilightShadow(FALSE);
#endif
        VDP_setEnable(FALSE);''')
p.write_text(s)
p=Path('src/r77_menu.inc');s=p.read_text()
needle='    VDP_setHilightShadow(FALSE);'
assert s.count(needle)==1
s=s.replace(needle,'''#if defined(DOOM_R79_SHADOW)
    VDP_setHilightShadow(TRUE);
#else
    VDP_setHilightShadow(FALSE);
#endif''')
p.write_text(s)
p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text()
needle='                        python3 scripts/lab/test_r77.py --generated; or exit 1';assert s.count(needle)==1
s=s.replace(needle,needle+'''
                        if test "$DOOM_R79_SHADOW" != 0
                            python3 scripts/lab/gen_r79_shadow.py --strength "$DOOM_R79_SHADOW"; or exit 1
                            python3 scripts/lab/test_r79_shadow.py --generated; or exit 1
                        end''')
needle="            set defs $defs '-DDOOM_R78_ART'";assert s.count(needle)==1
s=s.replace(needle,needle+'''
            if test "$DOOM_R79_SHADOW" != 0
                set defs $defs "-DDOOM_R79_SHADOW=$DOOM_R79_SHADOW"
            end''')
p.write_text(s)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
a=s.index('VARIANTS = (');b=s.index('\nLABEL =',a)
s=s[:a]+'''VARIANTS = tuple(
    ('r79-'+label+'-'+suffix,mode,{'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25',
        'DOOM_R72_FLAT_2D':'0','DOOM_R74_PROFILE':'l','DOOM_R74_FLATS':'f3',
        'DOOM_R75_HYBRID':'near','DOOM_R76_PROFILES':'1','DOOM_R79_SHADOW':str(strength)},[])
    for label,strength in (('base',0),('sh1',1),('sh2',2))
    for suffix,mode in (('pf','perf'),('pl','play'))
)
'''+s[b:]
s=s.replace('    assert len(records) == 2','    assert len(records) == 6')
s=s.replace("    for name in ('r78-art-pf','r78-art-pl'):","    for name,mode,extra_env,_ in VARIANTS:")
needle="        shutil.copy2(work/'res/r78-art-report.json',dest/(name+'-art-report.json'))";assert s.count(needle)==1
s=s.replace(needle,needle+'''
        if extra_env['DOOM_R79_SHADOW']!='0':
            assert '-DDOOM_R79_SHADOW='+extra_env['DOOM_R79_SHADOW'] in flags[name].split()
            for file in ('r79_shadow_report.json','r79_shadow_pairs.csv'):
                shutil.copy2(work/'src'/file,dest/(name+'-'+file))''')
p.write_text(s)
print('PASS R79 patch: six HUD ROMs, transparent 2px face sides, 8x8 adaptive shadow')
