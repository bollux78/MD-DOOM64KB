from pathlib import Path
import sys,ctypes as C,numpy as np,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reconstruction'));from visibility import Memory,visible_list;from raster import render
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--rom',type=Path,required=True);parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--host-library',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
lib=C.CDLL(str(args.host_library.resolve()))
class Camera(C.Structure):_fields_=[(n,C.c_int16) for n in ['x','y','z','si','co','sky']]
lib.navigation_reset();cam=Camera.in_dll(lib,'navigation_camera');cell=C.c_uint16.in_dll(lib,'navigation_cell');sine=(C.c_int16*256).in_dll(lib,'map_sine');fb=(C.c_ubyte*11520)();rows=[]
rom=args.rom.read_bytes();snapshot=bytes(np.load(args.capture/'geometry.npz')['memory'][0,0])
for angle in range(0,256,8):
 cam.si=sine[angle];cam.co=sine[(angle+64)&255];cam.sky=(Camera.in_dll(lib,'map_spawn').sky+2*angle)&127
 m=Memory(rom,snapshot)
 for addr,value in zip([0xff1a32,0xff1a30,0xff1a2e,0xff1a2a,0xff1a2c],[cam.x,cam.y,cam.z,cam.si,cam.co]):m.put(addr,value,2)
 m.put(0xff0fd6,0xe0ff1da8+4*cam.sky,4);m.ram[0x1b84:0x1d84]=bytes([1])*512;sb=m.u32(0xff1008);vis=visible_list(m,m.u32(sb+14*cell.value));pix,cov,stats=render(m,vis['records']);lib.render_view(fb,C.byref(cam),cell.value);diff=sum(a!=b for a,b in zip(bytes(fb),pix));rows.append({'angle':angle,'cell':cell.value,'different_bytes':diff,**stats})
print('rotation comparisons',len(rows),'mismatches',sum(r['different_bytes'] for r in rows),'unwritten',sum(r['uncovered_bytes'] for r in rows));print([r for r in rows if r['different_bytes'] or r['uncovered_bytes']][:3]);assert all(not r['different_bytes'] and not r['uncovered_bytes'] for r in rows)
lib.navigation_reset()
for _ in range(100):lib.navigation_update(2,6)
print('back collision',cam.x/8,cam.y/8,cell.value);back_y=cam.y;assert cam.y>=-208*8
lib.navigation_reset();cells=set()
for _ in range(60):lib.navigation_update(1,6);cells.add(cell.value)
print('forward cells',len(cells),'pos',cam.x/8,cam.y/8);assert len(cells)>3
(args.out/'model-validation.json').write_text(json.dumps({'rotation':rows,'forward_cells':sorted(cells),'back_collision_y_internal':back_y,'back_collision_wall_y':-224,'radius_world_units':16},indent=2)+'\n')
