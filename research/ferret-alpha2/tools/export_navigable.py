"""Extract the entire BSP, per-cell visibility and shared geometry; no scene pixels."""
from pathlib import Path
import argparse,sys,json,numpy as np,math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reconstruction'))
from visibility import Memory,visible_list
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rom=a.rom.read_bytes();snap=np.load(a.capture/'geometry.npz');m=Memory(rom,bytes(snap['memory'][0,0]));nb=m.u32(0xff100c);sb=m.u32(0xff1008);wb=m.u32(0xff1014);vb=m.u32(0xff1018);uvb=m.u32(0xff101c)
todo=[0];nodes=set();cells=set()
while todo:
 off=todo.pop()
 if off in nodes:continue
 nodes.add(off)
 for k in [8,10]:
  c=m.s16(nb+off+k)
  if c<0:cells.add(~c)
  else:todo.append(c)
assert nodes==set(range(0,max(nodes)+12,12)) and cells==set(range(max(cells)+1))
references=[];offsets=[0];floors=[];maxwall=0
for cell in range(len(cells)):
 t=Memory(rom,m.ram);t.ram[0x1b84:0x1d84]=bytes([1])*512
 records=visible_list(t,t.u32(sb+14*cell))['records']
 for flag,ptr in records:
  wi=(ptr-wb)//28;maxwall=max(maxwall,wi);references.append(wi|((flag&1)<<15))
 offsets.append(len(references));floors.append(m.s16(sb+14*cell+12))
wallrows=[];active=[];upper=lambda v:v<=3 or 9<=v<=11 or 15<=v<=17;lower=lambda v:v in [1,3,5,8,11,14,17]
for wi in range(maxwall+1):
 w=wb+28*wi;p0=vb+m.s16(w+8);p1=vb+m.s16(w+10);uv=uvb+m.s16(w+24);vs=[m.u8(w+14),m.u8(w+15)];tex=[m.u32(w),m.u32(w+4)]
 wallrows.append({'xy':[m.s16(p0),m.s16(p0+2),m.s16(p1),m.s16(p1+2)],'h':[m.s16(w+16+2*k) for k in range(4)],'uv':[m.s16(uv+4),m.s16(uv+6)],'colors':[m.u8(w+12),m.u8(w+13)],'variants':vs,'tex':tex})
 if any(upper(v) for v in vs if v<=17):active.append(tex[0])
 if any(lower(v) for v in vs if v<=17):active.append(tex[1])
base=min(active)-256;end=max(active)+8192+256;blob=rom[base:end]
lines=['#include "navigation.h"',f'const uint16_t scene_wall_count={len(wallrows)},map_node_count={len(nodes)},map_cell_count={len(cells)};','const Wall scene_walls[]={']
for w in wallrows:
 values=w['xy']+['{'+','.join(map(str,w['h']))+'}']+w['uv']+w['colors']+w['variants']+[v-base if v>=base else 256 for v in w['tex']]
 lines.append('{'+','.join(map(str,values))+'},')
lines+=['};','const MapNode map_nodes[]={']
for off in sorted(nodes):
 ptr=nb+off;children=[m.s16(ptr+k) for k in [8,10]];children=[c if c<0 else c//12 for c in children];d=int.from_bytes(m.get(ptr+4,4),'big',signed=True)
 lines.append('{'+','.join(map(str,[m.s16(ptr),m.s16(ptr+2),d]))+',{'+','.join(map(str,children))+'}},')
lines+=['};']
def flat(decl,values):lines.append(decl+'={'+','.join(map(str,values))+'};')
def rows(decl,values):lines.append(decl+'={\n'+',\n'.join('{'+','.join(map(str,v))+'}' for v in values)+'\n};')
flat('const uint16_t map_cell_walls[]',references);flat('const uint32_t map_cell_offsets[]',offsets);flat('const int16_t map_cell_floor[]',floors)
flat('const int16_t map_sine[256]',[m.s16(0xff2d12+2*((i-64)&255)) for i in range(256)])
camera=[m.s16(x) for x in [0xff1a32,0xff1a30,0xff1a2e,0xff1a2a,0xff1a2c]]+[((m.u32(0xff0fd6)&65535)-0x1da8)//4]
lines.append('const Camera map_spawn={'+','.join(map(str,camera))+'};')
sky=[m.get(m.u32(0xff1da8+4*x),72) for x in range(128)];rows('const uint8_t sky_columns[128][72]',sky)
samples=[]
for q in range(2048):
 addr=0x21b1c+m.u32(0x6d4ae+q*4);row=[]
 for y in range(72):
  assert m.get(addr+12*y+8,2)==b'\x1e\xea';row.append(m.s16(addr+12*y+10))
 samples.append(row)
rows('const int16_t sample_offsets[2048][72]',samples);flat('const uint8_t texture_blob[]',blob)
# A small grid indexes original segments for radius-based collision, not render geometry.
minx=min(min(w['xy'][0],w['xy'][2]) for w in wallrows)//128;maxx=max(max(w['xy'][0],w['xy'][2]) for w in wallrows)//128
miny=min(min(w['xy'][1],w['xy'][3]) for w in wallrows)//128;maxy=max(max(w['xy'][1],w['xy'][3]) for w in wallrows)//128
width=maxx-minx+1;height=maxy-miny+1;grid=[[] for _ in range(width*height)]
for wi,w in enumerate(wallrows):
 x0,y0,x1,y1=w['xy']
 for gy in range(min(y0,y1)//128,max(y0,y1)//128+1):
  for gx in range(min(x0,x1)//128,max(x0,x1)//128+1):grid[(gy-miny)*width+gx-minx].append(wi)
goff=[0];grefs=[]
for bucket in grid:grefs+=bucket;goff.append(len(grefs))
lines.append(f'const int16_t collision_origin_x={minx*128},collision_origin_y={miny*128};\nconst uint16_t collision_width={width},collision_height={height};')
flat('const uint32_t collision_offsets[]',goff);flat('const uint16_t collision_walls[]',grefs)
(a.out/'navigation_data.c').write_text('\n'.join(lines)+'\n')
meta={'nodes':len(nodes),'cells':len(cells),'walls':len(wallrows),'visibility_references':len(references),'texture_bytes':len(blob),'collision_grid':[width,height],'collision_references':len(grefs),'spawn':camera,'source':'ROM geometry and metadata; no framebuffer pixels','all_visibility_conditions_enabled':True}
(a.out/'navigation.json').write_text(json.dumps(meta,indent=2)+'\n');print(meta)
