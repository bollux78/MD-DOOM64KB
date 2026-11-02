#!/usr/bin/env python3
"""Build one isolated candidate/map using the pinned R113 chain."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess

CHAIN=[('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),
('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'}),
('apply_r88.py',{'R88_CANDIDATE':'ai'}),('apply_r89.py',{}),('apply_r90.py',{'R90_CANDIDATE':'control'}),
('apply_r91.py',{'R91_CANDIDATE':'sh1'}),('apply_r92.py',{'R92_CANDIDATE':'toggle'}),
('apply_r95.py',{'R95_NAME':'flat'}),('apply_r96.py',{'R96_NAME':'wall'}),('apply_r97.py',{'R97_NAME':'shasm'}),
('apply_r98.py',{'R98_CANDIDATE':'sprmul'}),('apply_r100.py',{'R100_MODE':'f1t','R100_PREFIX':'r102','R100_NAME':'twoface'}),
('apply_r104.py',{'R104_PREFIX':'r105','R104_NAME':'twoface'}),('apply_r107.py',{}),('apply_r113.py',{})]


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',choices=('control','depth','sprite','subos','subiv'),required=True)
    p.add_argument('--map',type=int,choices=(1,7),required=True);a=p.parse_args()
    root=pathlib.Path(__file__).resolve().parents[2]
    label='%s-m%d'%(a.candidate,a.map)
    w=pathlib.Path(os.environ['RUNNER_TEMP'])/('r114-'+label+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1'))
    assert not w.exists(),w
    shutil.copytree(root,w,ignore=shutil.ignore_patterns('.git','dist','__pycache__'),symlinks=True)
    def run(script,env=None):subprocess.run(['python3','scripts/lab/'+script],cwd=w,env={**os.environ,**(env or {})},check=True)
    for script,env in CHAIN:run(script,env)
    # Baseline MUST stay byte-for-byte R113, including the original build name.
    if a.candidate!='control':run('apply_r114.py',{'R114_CANDIDATE':a.candidate})
    d=w/'src/r_draw.c'
    if a.candidate in ('depth','sprite'):
        # Reject accidental mutations of the SRAM/IRQ routines: only intended files/blocks change.
        assert 'R25_SRAM_BEGIN();' in d.read_text() and 'R25_SRAM_END();' in d.read_text()
    b=w/'scripts/lab/build_r71a12mul_hud.py';s=b.read_text()
    old="(('pl','play'),)";assert s.count(old)==1
    if a.map==1:
        s=s.replace(old,"(('pl','play'),('pf','perf'))")
        s=s.replace('    assert len(records) == 1\n','    assert len(records) == 2\n')
    else:
        # Test fixture only. PLAY keeps the existing menu and PERF E1M1 remains unchanged.
        g=w/'src/g_game.c';gs=g.read_text()
        oldmap='/* PERF uses original E1M1 geometry for recorded DEMO3. */\n    map = 1;'
        assert gs.count(oldmap)==1
        g.write_text(gs.replace(oldmap,'/* R114 test fixture: DEMO3 commands on E1M7. Not a delivery ROM. */\n    map = 7;'))
        s=s.replace(old,"(('m7-pf','perf'),)")
    b.write_text(s)
    dest=root/'dist/r114/builds'/label;dest.mkdir(parents=True,exist_ok=False)
    try:
        with open(dest/'BUILD.log','w') as log:
            subprocess.run(['python3','scripts/lab/build_r71a12mul_hud.py'],cwd=w,
                env={**os.environ,'HUD_WORK':str(w)+'-hud'},stdout=log,stderr=subprocess.STDOUT,check=True)
    except subprocess.CalledProcessError:
        print((dest/'BUILD.log').read_text()[-12000:]);raise
    shutil.copytree(w/'dist/hud',dest,dirs_exist_ok=True)
    records=json.loads((dest/'MANIFEST.json').read_text())
    if a.candidate=='control' and a.map==1:
        expected={'r113-hilut-pl':'3106d4ede3c1c441ac5905ec181c9babba691dd5e245413c68d97192230c25c8',
                  'r113-hilut-pf':'e181c87742426e65bac78b14e061fba21d8834b27689c2b6c45cc1b84bfd4a48'}
        for r in records:assert r['sha256']==expected[r['variant']],('R113 baseline is not identical',r)
    od=os.environ['OBJDUMP']
    for r in records:
        assert r['bss_bytes']<=57920 and r['bytes']<=4194304,r
        rom=dest/r['rom'];assert hashlib.sha256(rom.read_bytes()).hexdigest()==r['sha256']
        if r['variant'].endswith('pf'):
            dump=subprocess.check_output([od,'-d',str(dest/r['elf'])],text=True)
            (dest/'objdump.txt').write_text(dump)
            import re
            funcs=re.findall(r'^[0-9a-f]{8} <((?:R_Subsector|R_ProjectSprite|R_DrawColumnSprite|R_DrawSegTextureColumn)[^>]*)>:',dump,re.M)
            with open(dest/'metrics.json','w') as f:subprocess.run(['python3',str(root/'scripts/lab/r100_asm_metrics.py'),str(dest/'objdump.txt'),*funcs],stdout=f,check=True)
    print(json.dumps(dict(candidate=a.candidate,map=a.map,roms=records)))
if __name__=='__main__':main()
