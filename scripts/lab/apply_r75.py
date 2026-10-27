#!/usr/bin/env python3
"""Runner-local R75 integration: A2/L3 controls + two hybrid flat maps, menu VRAM hold."""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r74.py'],check=True)
# Prevent empty flat framebuffer submission while GAME MENU is active.
# The menu text is drawn to VDP by M_Drawer; do not overwrite it via R22 DMA.
p=Path('src/d_main.c');s=p.read_text()
needle='    D_BuildNewTiccmds();\n\n    if (wipe)'
assert s.count(needle)==1
s=s.replace(needle,'''    D_BuildNewTiccmds();
#if defined(DOOM_R75_MENU_HOLD)
    /* Overlay writes are direct to VDP; hold the last rendered 3D VRAM tiles
     * and do not queue a blank Pair-V frame while Start menu is open.
     * First normal gameplay update on close restores the 3D background. */
    if (_g_menuactive && !_g_demoplayback && _g_gamestate==GS_LEVEL)
        return;
#endif
    if (wipe)''')
p.write_text(s)
p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text()
needle='                python3 scripts/lab/inject_r74_flats.py "$DOOM_R74_FLATS"; or exit 1'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
                if set -q DOOM_R75_HYBRID
                    python3 scripts/lab/gen_r75_hybrid.py "$DOOM_R75_HYBRID"; or exit 1
                    python3 scripts/lab/inject_r75_hybrid.py; or exit 1
                end''')
needle="        set defs $defs '-DDOOM_R71_MUL_ASM'"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        set defs $defs '-DDOOM_R75_MENU_HOLD'
''')
p.write_text(s)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
start=s.index('VARIANTS = (');stop=s.index('\nLABEL =',start)
v=[]
for key,profile,flat,hybrid in [
    ('a2','a','f2',None),('l3','l','f3',None),
    ('h2','l','f3','a2'),('hn','l','f3','near')]:
    for mode,suffix in [('perf','pf'),('play','pl')]:
        name='r75-'+key+'-'+suffix
        env={'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25',
            'DOOM_R72_FLAT_2D':'0','DOOM_R74_PROFILE':profile,'DOOM_R74_FLATS':flat}
        if hybrid:env['DOOM_R75_HYBRID']=hybrid
        v.append((name,mode,env,[]))
s=s[:start]+'VARIANTS = '+repr(tuple(v))+s[stop:]
s=s.replace('assert len(records) == 16','assert len(records) == 8')
s=s.replace("contents=flags[name]", "contents=flags[name]\\n        assert '-DDOOM_R75_MENU_HOLD' in contents.split(),name")
# Validate the menu fix is actually linked in all PERF/PLAY variants.
s=s.replace("'DOOM_R73_R53_FIXED')","'DOOM_R73_R53_FIXED', '-DDOOM_R75_MENU_HOLD')")

start=s.index('    for name in (\'r74-ac-pf\'')
stop=s.index(':\n        contents=flags[name]',start)
s=s[:start]+'    for name in '+repr(tuple(x[0] for x in v))+s[stop:]
needle="        shutil.copy2(work/'src/r74_flats_report.json',dest/(name+'-flat-report.json'))"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        if extra_env.get('DOOM_R75_HYBRID'):
            shutil.copy2(work/'src/r75_hybrid_report.json',dest/(name+'-hybrid-report.json'))''')
s=s.replace("print('PASS R74 16 ROMs: M50 N25A/L32F flat-only controls and F1/F2/F3 + mandatory HUD',flush=True)","print('PASS R75 hybrid 8 ROMs, all HUD, menu hold enabled',flush=True)")
p.write_text(s)
print('R75 prepared: A2 and L3 controls plus two hybrid options, each PERF/PLAY')
