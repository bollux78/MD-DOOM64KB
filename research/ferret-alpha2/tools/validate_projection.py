from pathlib import Path
import numpy as np,sys,json,collections
import argparse
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--results',type=Path,required=True);args=p.parse_args()
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'reconstruction'))
from visibility import Memory
from projection import project,s16
rom=args.rom.read_bytes()
for cap in ['geometry-still','geometry-turn']:
 z=np.load(args.results/cap/'geometry.npz');stats=collections.Counter();errors=[]
 for scene,states in enumerate(z['memory']):
  mem=Memory(rom,bytes(states[1]));events=z['events'][z['events'][:,0]==scene];pred=None;seen_job=False
  def finish():
   if pred is not None and (not pred['rejected']) != seen_job:errors.append({'scene':scene,'type':'dispatch_classification','predicted_reject':pred['rejected'],'observed_job':seen_job})
  for e in events:
   pc=int(e[1]);regs=list(map(int,e[4:20]))
   if pc==0x770b6:
    finish();seen_job=False
    try:pred=project(mem,regs[13],regs[7]&255);stats['wall_inputs']+=1
    except Exception as ex:errors.append({'scene':scene,'error':str(ex)});pred=None
   elif pc==0x7716e and pred:
    got=list(map(s16,regs[2:6]));stats['transforms']+=1
    if got!=pred['transformed']:errors.append({'scene':scene,'type':'transform','expected':got,'got':pred['transformed']})
   elif pc in [0x7731e,0x773fc] and pred:
    seen_job=True;stats['jobs']+=1;got=[s16(regs[2])//8,s16(regs[3])+1,regs[4]&65535,int(e[22]),s16(int(e[21]))]
    own=[pred.get('x0'),pred.get('width'),pred.get('inv0'),pred.get('inv1'),pred.get('scale_step')]
    if pred['textured']:
     got += [regs[6],regs[7],regs[8],regs[9]];own += [pred['texture_start'],pred['texture_step'],pred['kernel'],pred['texture']]
    else:
     got += [regs[8]];own += [pred['kernel']]
    if own!=got:errors.append({'scene':scene,'type':'projection','expected':got,'got':own,'pred':pred})
  finish()
 out={'stats':dict(stats),'errors':errors};(args.results/cap/'projection-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(cap,dict(stats),'errors',len(errors));print(errors[:2]);assert not errors
