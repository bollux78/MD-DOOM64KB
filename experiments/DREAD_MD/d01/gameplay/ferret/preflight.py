#!/usr/bin/env python3
"""Check prepared WAD data and lossless column codec, without building a ROM."""
from pathlib import Path
import argparse,json,sys,random,re
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from pack_episode import entries,numbers
from ferret_columns import encode_column,decode_column
from ferret_pvs import encode_group,decode_group
from gen_ferret_scalers import offsets
p=argparse.ArgumentParser();p.add_argument('assets',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
rng=random.Random(25)
for n in [1,2,3,127,128,129,256,288,512]:
 for data in [bytes(n),bytes([255])*n,bytes(rng.randrange(256) for _ in range(n)),bytes((i//3)&255 for i in range(n))]:assert decode_column(encode_column(data))==data
stats=[];seen=set()
for n in range(1,10):
 d=a.assets/f'E1M{n}';meta=json.loads((d/'source-pixels.json').read_text());assert meta['source_pixels'] and not meta['resized']
 data=entries(d/'mapdata.c');blob=bytes(numbers(data['tex_blob']));raw=data['map_tex'];cols=0
 for group in re.finditer(r'\{(\d+),(\d+),(\d+),(\d+),\{([\d,]+)\},\{[\d,]+\}\}',raw):
  width,h=1<<int(group[1]),1<<int(group[2]);realh,realw=int(group[3]),int(group[4]);assert width>=realw and width<2*realw and h>=realh
  stride=h+min(h,32)
  for start in map(int,group[5].split(',')):
   for at in range(start,start+width*stride,stride):
    col=blob[at:at+stride];assert len(col)==stride and stride<=160
    packed=encode_column(col);assert decode_column(packed)==col;seen.add(col);cols+=1
 rows=numbers(data['map_segs']);assert len(rows)%12==0
 assert all(0<=rows[k]<=256 for k in range(11,len(rows),12))
 sprites=numbers(data['map_sprites']);assert len(sprites)==len(meta['sprites'])*8
 assert all(sprites[i*8]==s['width'] and sprites[i*8+1]==s['height'] for i,s in enumerate(meta['sprites']))
 vis=entries(d/'pvs.c');nw=numbers(vis['pvs_nbytes'])[0];sw=numbers(vis['pvs_sbytes'])[0];nn=bytes(numbers(vis['pvs_nodes']));ss=bytes(numbers(vis['pvs_subs']));nsub=len(ss)//sw
 rowcount=min(8,1408//(nw+sw));assert rowcount>=1
 for first in range(0,nsub,rowcount):
  raw=b''.join(nn[j*nw:(j+1)*nw]+ss[j*sw:(j+1)*sw] for j in range(first,min(nsub,first+rowcount)))
  assert len(raw)<=1408 and decode_group(encode_group(raw))==raw
 stats.append({'map':f'E1M{n}','textures':len(meta['textures']),'sprites':len(meta['sprites']),'columns_checked':cols,'resized':False})
unique={tuple(offsets(q)) for q in range(2048)}
report={'status':'source_preflight_passed','maps':stats,'unique_columns':len(seen),'unique_column_raw_bytes':sum(map(len,seen)),'unique_column_rle_bytes':sum(len(encode_column(x)) for x in seen),'scaler_selectors':2048,'unique_scaler_rows':len(unique),'host_probe':'separate host_probe.c required; this script checks generated data only','rom_build':'not run','rom_fps':'not measured'}
a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
