from pathlib import Path
import argparse,sys,json,numpy as np,ctypes as C
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--host-library',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'reconstruction'))
from visibility import Memory,visible_list
from raster import render
rom=a.rom.read_bytes();rows=[];lib=C.CDLL(str(a.host_library.resolve())) if a.host_library else None;buffer=(C.c_ubyte*11520)()
for cap in ['geometry-still','geometry-turn']:
 z=np.load(a.results/cap/'geometry.npz')
 for i,states in enumerate(z['memory']):
  m=Memory(rom,bytes(states[0]));entry=next(e for e in z['events'] if e[0]==i and e[1]==0x77402);v=visible_list(m,int(entry[14]));pixels,coverage,stats=render(m,v['records']);end=Memory(rom,bytes(states[2]));expected=end.get(end.u32(0xff2c72),11520);diff=np.frombuffer(pixels,'uint8')!=np.frombuffer(expected,'uint8');covered=np.frombuffer(coverage,'uint8')!=0
  row={'capture':cap,'scene':i,'compared_written_bytes':int(covered.sum()),'different_written_bytes':int((diff&covered).sum()),'unwritten_different_bytes':int((diff&~covered).sum()),**stats}
  pose=0 if cap=='geometry-still' and i==0 else (i+1 if cap=='geometry-turn' and i<15 else None)
  if lib and pose is not None:
   lib.render_scene(buffer,pose);row['host_C_different_bytes']=sum(x!=y for x,y in zip(bytes(buffer),pixels));assert not row['host_C_different_bytes']
  assert not row['different_written_bytes'] and not stats['unsupported'];rows.append(row)
  if i==0:
   (a.results/cap/'model-walls.bin').write_bytes(pixels);(a.results/cap/'original-walls.bin').write_bytes(expected);(a.results/cap/'model-written-mask.bin').write_bytes(coverage)
(a.results/'raster-validation.json').write_text(json.dumps(rows,indent=2)+'\n');print('scenes',len(rows),'written-byte comparisons',sum(r['compared_written_bytes'] for r in rows),'mismatches',sum(r['different_written_bytes'] for r in rows))
