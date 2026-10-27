#!/usr/bin/env python3
"""R78 disposable build patch: seamless lower HUD stone, user native pictures."""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r77.py'],check=True)
p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text()
needle='    python3 scripts/lab/gen_r30_native.py --dither "$dither" --storage raw > "$dest/art-$v.json"; or exit 1'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
    if set -q DOOM_R78_ART
        python3 scripts/lab/gen_r78_art.py; or exit 1
    end''')
needle="        set defs $defs '-DDOOM_R71_MUL_ASM'"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        if set -q DOOM_R78_ART
            set defs $defs '-DDOOM_R78_ART'
        end''')
p.write_text(s)
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text().replace('r77-col-','r78-art-')
needle='        env.update(extra_env)';assert s.count(needle)==1
s=s.replace(needle,needle+"\n        env['DOOM_R78_ART']='1'")
needle="        report = json.loads((work / 'src/r58_colormatch_report.json').read_text())"
assert s.count(needle)==1
s=s.replace(needle,"        shutil.copy2(work/'res/r78-art-report.json',dest/(name+'-art-report.json'))\n"+needle)
needle="        assert '-DDOOM_R77_MENU' in contents.split(),name"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n        assert '-DDOOM_R78_ART' in contents.split(),name")
p.write_text(s)
print('PASS R78 source patch: lossless dual-plane PNG art and seamless lower stone')
