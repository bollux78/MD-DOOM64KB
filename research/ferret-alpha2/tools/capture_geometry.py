"""Capture list/column jobs at real instruction boundaries, not inferred video timing."""
from pathlib import Path
import argparse,ctypes as C,json,hashlib
import numpy as np
from libretro_runner import Emulator
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--core',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--turn',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
e=Emulator(a.core,a.rom);C.c_uint.in_dll(e.core,'retro_sram_block').value=1
e.step(120);e.step(20,3);e.step(40);e.step(20,8);e.step(40);e.step(20,8);e.step(60,capture=True)
C.c_uint.in_dll(e.core,'retro_phase2_active').value=1
for frame in range(1000):
 e.step(1,6 if a.turn else None,capture=True)
 if not C.c_uint.in_dll(e.core,'retro_phase2_active').value:break
else:raise RuntimeError('Geometry capture did not complete')
n=C.c_uint.in_dll(e.core,'retro_phase2_scenes').value;ne=C.c_uint.in_dll(e.core,'retro_phase2_events').value
raw=np.ctypeslib.as_array((C.c_ubyte*(16*3*65536)).in_dll(e.core,'retro_phase2_memory')).reshape(16,3,65536)[:n].copy()
events=np.ctypeslib.as_array((C.c_uint*(16384*24)).in_dll(e.core,'retro_phase2_event')).reshape(-1,24)[:ne].copy()
np.savez_compressed(a.out/'geometry.npz',memory=raw,events=events)
(a.out/'events.json').write_text(json.dumps(events.tolist())+'\n');(a.out/'capture.json').write_text(json.dumps({'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),'core_sha256':hashlib.sha256(a.core.read_bytes()).hexdigest(),'scenes':n,'events':ne,'video_frames':frame+1,'turn_left':a.turn,'sram':'disabled','snapshot_indices':['list_entry','list_return','walls_return'],'event_fields':['scene','pc','video_frame','master_cycles','D0..D7','A0..A7','SR','scale_step_word','scale_end_word','width_word']},indent=2)+'\n')
e.screenshot().save(a.out/'end.png');print(n,ne,frame+1);e.close()
