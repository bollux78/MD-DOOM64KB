#!/usr/bin/env python3
"""R74 compatibility patch: R71 renderer + R53 M50 + flat-only LUTs.
Run only in CI checkout. Leaves R71/R73 sources in Git unchanged."""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r73_r53.py'],check=True)
# Preserve original historical R53 50% pixel checker (not the rejected R73-F logical checker).
p=Path('src/r22_video.inc');s=p.read_text()
old='(((x+row)&3u)==0u)'
assert s.count(old)==1
s=s.replace(old,'(((x+row)&1u)==0u)')
p.write_text(s)
# Keep the R59 cache structure but override only flat indices AFTER generating R53 tables.
p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text()
old='--ratio 25; or exit 1'
assert s.count(old)==1
s=s.replace(old,'--ratio 50; or exit 1')
old='                python3 scripts/lab/gen_r73_r53_fixed.py "$DOOM_R73_STYLE"; or exit 1'
assert s.count(old)==1
s=s.replace(old,old+'''
                python3 scripts/lab/gen_r74_flats.py --profile "$DOOM_R74_PROFILE" --policy "$DOOM_R74_FLATS"; or exit 1
                python3 scripts/lab/inject_r74_flats.py "$DOOM_R74_FLATS"; or exit 1''')
p.write_text(s)
# Two profiles, four policies, PERF and PLAY. Independently isolated checkout per ROM.
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text()
i=s.index('VARIANTS = (');j=s.index('\nLABEL =',i)
lines=['VARIANTS = (']
for profile,preset,zero in [('a','near25','allow'),('l','luma32','forbid')]:
    for policy,short in [('ctl','c'),('f1','1'),('f2','2'),('f3','3')]:
        for mode,suffix in [('perf','pf'),('play','pl')]:
            name=f'r74-{profile}{short}-{suffix}'
            env={'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25','DOOM_R72_FLAT_2D':'0',
                 'DOOM_R74_PROFILE':profile,'DOOM_R74_FLATS':policy}
            lines.append('    ('+repr(name)+', '+repr(mode)+', '+repr(env)+', []),')
lines.append(')')
names=[f'r74-{p}{n}-{mode}' for p in ('a','l') for n in ('c','1','2','3') for mode in ('pf','pl')]
s=s[:i]+'\n'.join(lines)+s[j:]
assert "'DOOM_R52_AB_PROFILE': 'near25'" in s
s=s.replace("'DOOM_R52_AB_PROFILE': 'near25'","'DOOM_R52_AB_PROFILE': 'near25'") # overridden below by profile
# Profile is an ENV key already cleaned by the builder? Explicitly set in each isolated build.
anchor="        env.update(extra_env)"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
        env['DOOM_R52_AB_PROFILE']='near25' if extra_env['DOOM_R74_PROFILE']=='a' else 'luma32'
        env['DOOM_R52_ZERO_POLICY']='allow' if extra_env['DOOM_R74_PROFILE']=='a' else 'forbid'
        # FLAT_WALL would route walls through flat LUTs; reject unsafe combinations.
        assert not any(x == '-DFLAT_WALL' for x in _extra_flags)
''')
s=s.replace('assert len(records) == 6','assert len(records) == 16')
start=s.index("    for name in ('r73-s-pf'")
end=s.index(':\n        contents=flags[name]',start)
s=s[:start]+'    for name in '+repr(tuple(names))+s[end:]
s=s.replace("print('PASS R73 R53 fixed palette triplet: R71A12MUL + HUD',flush=True)","print('PASS R74 16 ROMs: M50 N25A/L32F flat-only controls and F1/F2/F3 + mandatory HUD',flush=True)")
# Persist each policy report alongside ROMs
anchor="        report = json.loads((work / 'src/r58_colormatch_report.json').read_text())"
assert s.count(anchor)==1
s=s.replace(anchor,"        shutil.copy2(work/'src/r74_flats_report.json',dest/(name+'-flat-report.json'))\n"+anchor)
p.write_text(s)
print('R74: prepared 16 M50 ROM configurations (A/L x control/F1/F2/F3 x PERF/PLAY)')
