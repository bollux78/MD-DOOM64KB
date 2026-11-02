#!/usr/bin/env python3
"""Runner orchestration: full captures, exact comparison, original one-second windows.
Only candidates completing ALL fixtures are copied to play/. Hardware approval remains pending.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'dist/r114'
# Off and On, A2 and L3. E1M7 uses the same recorded input, AI Normal.
CASES=((1,0,1),(1,0,2),(1,1,1),(1,1,2),(7,1,1),(7,1,2))

def run(args,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with open(log,'w') as f:
        r=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:
        print(log.read_text()[-12000:],flush=True)
        raise RuntimeError('%s failed (%d); see %s'%(args[1],r.returncode,log))

def readrows(p):return [json.loads(s) for s in (p/'frames.jsonl').read_text().splitlines() if s.strip()]

def compare(base,cand):
    a=readrows(base);b=readrows(cand)
    assert [(r['tic'],r['bench_frame']) for r in a]==[(r['tic'],r['bench_frame']) for r in b], 'different tic/frame sequences'
    # Ignore the first two tics while the one-time palette write is being applied.
    ids=[i for i,r in enumerate(a) if r['tic']>=3]
    aa=(base/'post.bin').read_bytes();bb=(cand/'post.bin').read_bytes()
    diff=[dict(frame=a[i]['bench_frame']+1,tic=a[i]['tic']) for i in ids
          if aa[i*3344:(i+1)*3344]!=bb[i*3344:(i+1)*3344]]
    ma=json.loads((base/'CAPTURE.json').read_text());mb=json.loads((cand/'CAPTURE.json').read_text())
    av=a[ids[-1]]['vb']-a[ids[0]]['vb'];bv=b[ids[-1]]['vb']-b[ids[0]]['vb']
    indexed={r['bench_frame']+1:i for i,r in enumerate(a)}
    windows=[]
    for w in ma['worst_windows']:
        lo=indexed.get(w['frame_start']-1);hi=indexed.get(w['frame_end'])
        if lo is None or hi is None:continue
        ac=a[hi]['vb']-a[lo]['vb'];bc=b[hi]['vb']-b[lo]['vb']
        windows.append(dict(frame_start=w['frame_start'],frame_end=w['frame_end'],
                            tic_start=a[lo]['tic'],tic_end=a[hi]['tic'],vblanks_control=ac,vblanks_candidate=bc,
                            delta_pct=round((bc/ac-1)*100,3)))
    return dict(compared_frames=len(ids),post_pass_frames_differing=len(diff),first_differences=diff[:8],
                vblanks_control=av,vblanks_candidate=bv,delta_pct=round((bv/av-1)*100,3),
                benchmark_min_control=ma['end']['min_x10']/10,benchmark_min_candidate=mb['end']['min_x10']/10,
                worst_control_windows_aligned_by_frame=windows,
                stack_control=ma['stack'],stack_candidate=mb['stack'],
                timing_note='Emulated VBlanks, not hardware. Aligned windows use post-pass boundaries; game MIN uses its own counters.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',choices=('control','depth','sprite','subos','subiv','combo'),required=True);a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);cand=a.candidate
    summary=dict(candidate=cand,base_commit='e35345b',status='running',cases={},hardware_validation='pending')
    report=OUT/(cand+'-SUMMARY.json')
    def save():report.write_text(json.dumps(summary,indent=1)+'\n')
    save()
    try:
        for mp in (1,7):
            run([sys.executable,'scripts/lab/r114_build.py','--candidate',cand,'--map',str(mp)],OUT/'logs'/('build-%s-m%d.log'%(cand,mp)))
        for mp,shadow,mode in CASES:
            name='m%d-s%d-c%d'%(mp,shadow,mode)
            d=OUT/'builds'/('%s-m%d'%(cand,mp));roms=list(d.glob('*-pf.bin'));assert len(roms)==1,roms
            rom=roms[0];target=OUT/'captures'/cand/name
            cmd=[sys.executable,'scripts/lab/r114_capture.py','--blastem',os.environ['BLASTEM'],
                 '--rom',str(rom),'--elf',str(rom.with_suffix('.elf')),'--out',str(target),
                 '--shadow',str(shadow),'--mode',str(mode),'--map',str(mp),'--stack']
            if cand=='control':cmd.append('--profile')
            run(cmd,OUT/'logs'/('capture-%s-%s.log'%(cand,name)))
            if cand=='control':summary['cases'][name]=json.loads((target/'CAPTURE.json').read_text())
            else:
                summary['cases'][name]=compare(OUT/'captures/control'/name,target)
            save()
            print('::notice title=R114 %s %s::%s'%(cand,name,json.dumps(summary['cases'][name] if cand!='control' else {k:summary['cases'][name][k] for k in ('frames','last_tic','end','stack')})),flush=True)
        if cand!='control':
            assert all(r['post_pass_frames_differing']==0 for r in summary['cases'].values()),'REJECTED: pixels differ'
        if cand=='combo':
            depth=json.loads((OUT/'depth-SUMMARY.json').read_text())
            subiv=json.loads((OUT/'subiv-SUMMARY.json').read_text())
            summary['interaction']={}
            for name,c in summary['cases'].items():
                d=depth['cases'][name];v=subiv['cases'][name];base=c['vblanks_control']
                assert base==d['vblanks_control']==v['vblanks_control']
                independent=d['vblanks_candidate']+v['vblanks_candidate']-base
                summary['interaction'][name]=dict(control_vblanks=base,depth_vblanks=d['vblanks_candidate'],
                    subiv_vblanks=v['vblanks_candidate'],combined_vblanks=c['vblanks_candidate'],
                    independent_savings_prediction_vblanks=independent,
                    interaction_vblanks=c['vblanks_candidate']-independent,
                    combined_delta_pct=c['delta_pct'])
        summary['status']='baseline_complete' if cand=='control' else 'pixels_equivalent_hardware_pending'
        play=OUT/'play';play.mkdir(exist_ok=True)
        for rom in (OUT/'builds'/('%s-m1'%cand)).glob('*-pl.bin'):shutil.copy2(rom,play/rom.name)
    except Exception as e:
        summary.update(status='failed_or_rejected',error=str(e));save();raise
    finally:save()
if __name__=='__main__':main()
