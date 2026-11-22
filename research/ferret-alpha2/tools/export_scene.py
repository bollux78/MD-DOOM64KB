"""Extract geometry/material assets only. Never reads a captured framebuffer for 3D pixels."""
from pathlib import Path
import sys,argparse,json,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reconstruction'))
from visibility import Memory,visible_list
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--still',type=Path,required=True);p.add_argument('--turn',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rom=a.rom.read_bytes();still=np.load(a.still/'geometry.npz');turn=np.load(a.turn/'geometry.npz');m=Memory(rom,bytes(still['memory'][0,0]));entry=next(x for x in still['events'] if x[0]==0 and x[1]==0x77402);records=visible_list(m,int(entry[14]))['records'];vb=m.u32(0xff1018);uvb=m.u32(0xff101c);walls=[];pointers=[]
for flag,w in records:
 p0=vb+m.s16(w+8);p1=vb+m.s16(w+10);uv=uvb+m.s16(w+24);t0=m.u32(w);t1=m.u32(w+4);pointers.extend([t0,t1]);walls.append({'xy':[m.s16(p0),m.s16(p0+2),m.s16(p1),m.s16(p1+2)],'heights':[m.s16(w+16+i*2) for i in range(4)],'uv':[m.s16(uv+4),m.s16(uv+6)],'colors':[m.u8(w+12),m.u8(w+13)],'variant':m.u8(w+14+(flag&1)),'tex':[t0,t1]})
active=[]
for w in walls:
 v=w['variant']
 if v<=3 or 9<=v<=11 or v>=15:active.append(w['tex'][0])
 if v in [1,3,5,8,11,14,17]:active.append(w['tex'][1])
base=min(active)-256;end=max(active)+8192+256;blob=rom[base:end];sky=b''.join(m.get(m.u32(0xff1da8+4*x),72) for x in range(128));samples=[];invalid=0
for q in range(2048):
 addr=0x21b1c+m.u32(0x6d4ae+q*4);row=[]
 for y in range(72):
  ip=addr+y*12+8
  if m.get(ip,2)!=b'\x1e\xea':invalid+=1
  row.append(m.s16(ip+2))
 samples.append(row)
poses=[Memory(rom,bytes(still['memory'][0,0]))]+[Memory(rom,bytes(x[0])) for x in turn['memory'][:15]]
cameras=[[v.s16(x) for x in [0xff1a32,0xff1a30,0xff1a2e,0xff1a2a,0xff1a2c]]+[((v.u32(0xff0fd6)&65535)-0x1da8)//4] for v in poses]
lines=['#include "scene.h"','const uint16_t scene_wall_count='+str(len(walls))+';','const Wall scene_walls[]={']
for w in walls:
 x,y,x1,y1=w['xy'];h=','.join(map(str,w['heights']));u,v=w['uv'];c0,c1=w['colors'];t0,t1=w['tex'];t0=t0 if t0>=base else base+256;t1=t1 if t1>=base else base+256;lines.append(f'{{{x},{y},{x1},{y1},{{{h}}},{u},{v},{c0},{c1},{w["variant"]},0,{t0-base},{t1-base}}},')
lines+=['};','const Camera scene_cameras[16]={'+','.join('{'+','.join(map(str,c))+'}' for c in cameras)+'};']
def array(declaration,rows):
 lines.append(declaration+'={')
 for row in rows:lines.append('{'+','.join(map(str,row))+'},')
 lines.append('};')
array('const int16_t sample_offsets[2048][72]',samples);array('const uint8_t sky_columns[128][72]',[sky[x*72:x*72+72] for x in range(128)])
lines.append('const uint8_t texture_blob[]={'+','.join(map(str,blob))+'};')
(a.out/'data.c').write_text('\n'.join(lines)+'\n');(a.out/'scene.json').write_text(json.dumps({'wall_count':len(walls),'texture_blob_bytes':len(blob),'texture_base':hex(base),'scaler_values':2048*72,'scaler_non_move_slots':invalid,'cameras':cameras,'limitations':'Fixed spawn-cell visibility, sky follows diagnostic pose; no actors/HUD generation; not a complete engine.'},indent=2)+'\n');print((a.out/'scene.json').read_text())
