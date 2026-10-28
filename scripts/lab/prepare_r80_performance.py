#!/usr/bin/env python3
"""Prepare only control or candidate PERF/PLAY; never the R79 shadow matrix.
Run once in a clean, disposable checkout. Source changes are not committed.
"""
from pathlib import Path
import argparse,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',choices=('control','candidate'),default='control')
    a=p.parse_args();os.chdir(ROOT)
    video=ROOT/'src/r22_video.inc'
    if 'R79_PAL0' in video.read_text():
        p.error('checkout already prepared; start from a clean disposable checkout')
    subprocess.run([sys.executable,'scripts/lab/apply_r79.py'],check=True)
    if a.variant=='candidate':
        subprocess.run([sys.executable,'scripts/lab/apply_r80_performance.py'],check=True)
    builder=ROOT/'scripts/lab/build_r71a12mul_hud.py';s=builder.read_text()
    needle='\nLABEL = {}';assert s.count(needle)==1
    extra="\n# R80: only the accepted non-shadow R79 configuration.\nVARIANTS = tuple(v for v in VARIANTS if v[2].get('DOOM_R79_SHADOW') == '0')\n"
    if a.variant=='candidate':
        extra+="VARIANTS = tuple((n.replace('r79-base-', 'r80-perf-'),m,e,f) for n,m,e,f in VARIANTS)\n"
    s=s.replace(needle,extra+needle)
    needle='    assert len(records) == 6';assert s.count(needle)==1
    s=s.replace(needle,'    assert len(records) == 2')
    builder.write_text(s)
    dest=ROOT/'dist/hud';dest.mkdir(parents=True,exist_ok=True)
    (dest/'R80-PREPARATION.json').write_text(json.dumps(dict(variant=a.variant,shadow=False,rom_count=2,candidate_hook='scripts/lab/apply_r80_performance.py' if a.variant=='candidate' else None),indent=2)+'\n')
    print('Prepared',a.variant,'PERF/PLAY only; build separately with build_r71a12mul_hud.py')
if __name__=='__main__':main()
