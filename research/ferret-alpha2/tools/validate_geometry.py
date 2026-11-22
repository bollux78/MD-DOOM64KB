from pathlib import Path
import argparse,sys,json,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reconstruction'))
from visibility import Memory,visible_list,read_records
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('capture',type=Path);a=p.parse_args();z=np.load(a.capture/'geometry.npz');rom=a.rom.read_bytes();out=[]
for i,states in enumerate(z['memory']):
 events=z['events'][z['events'][:,0]==i];entry=next(e for e in events if e[1]==0x77402);m=Memory(rom,bytes(states[0]));got=visible_list(m,int(entry[14]));expected=read_records(Memory(rom,bytes(states[1])))
 row={'scene':i,'records':len(got['records']),'tokens':len(got['tokens']),'actors':len(got['actors']),'list_equal':got['records']==expected,'actors_end_equal':m.u32(0xff1b80)==Memory(rom,bytes(states[1])).u32(0xff1b80)};out.append(row)
 if not row['list_equal']:
  print('MISMATCH',i,got['records'][:8],expected[:8]);break
(a.capture/'visibility-validation.json').write_text(json.dumps(out,indent=2)+'\n');print('validated',len(out),'equal',sum(r['list_equal'] for r in out));assert len(out)==16 and all(r['list_equal'] and r['actors_end_equal'] for r in out)
