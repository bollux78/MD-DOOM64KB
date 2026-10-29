#!/usr/bin/env python3
"""R89-all optimizations, original four-mode Options menu, Normal AI, R90 flats."""
from pathlib import Path
import os,subprocess
mode=os.environ['R90_CANDIDATE'];assert mode in ('control','flats')
# Apply all approved optimizations, discard the quick-color menu regression.
menu=Path('src/m_text.c').read_bytes()
subprocess.run(['python3','scripts/lab/apply_r89_routes.py'],env={**os.environ,'R89_ROUTE':'all'},check=True)
Path('src/m_text.c').write_bytes(menu)
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:80],s.count(a));p.write_text(s.replace(a,b))
patch('src/p_enemy2.c','static uint8_t r89_ai_low=1;','static uint8_t r89_ai_low=0;')
needle='                        python3 scripts/lab/test_r77.py --generated; or exit 1'
patch('scripts/lab/build_r35_linear.fish',needle,needle+'\n                        python3 scripts/lab/r90_inject_flats.py'+(' --verify-only' if mode=='control' else '')+'; or exit 1')
patch('scripts/lab/build_r71a12mul_hud.py',"'r89-'","'r90-'")
patch('scripts/lab/build_r71a12mul_hud.py',"('all', 0)",repr((mode,0)))
needle="        for table in ('r56_tables.h', 'r59_color_tables.h'):"
patch('scripts/lab/build_r71a12mul_hud.py',needle,"        shutil.copy2(work/'src/r90_flats_report.json',dest/(name+'-flats-report.json'))\n"+needle)
print('R90',mode,'R89-all, original four-mode Options, AI Normal default, PLAY only')
