"""Capture real Ferret Alpha 2 hardware state. ROM stays outside the repository."""
from pathlib import Path
import argparse,ctypes as C,json,hashlib,collections
import numpy as np
from PIL import Image
from libretro_runner import Emulator
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);p.add_argument('--core',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',type=int,default=1500);p.add_argument('--sram',type=int,default=1);p.add_argument('--turn',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
e=Emulator(a.core,a.rom);core=e.core
C.c_uint.in_dll(core,'retro_sram_block').value=a.sram
# Libretro Start=3, Mega Drive A=8, Left=6. Port 0 uses the standard libretro Mega Drive mapping.
e.step(120);e.step(20,3);e.step(40);e.step(20,8);e.step(40);e.step(20,8);e.step(60,capture=True)
def sw(v):return ((v&255)<<8)|(v>>8)
def words(fn,size):return b''.join(sw(fn(i)).to_bytes(2,'big') for i in range(0,size,2))
vr=core.retro_dread_vram_word;cr=core.retro_dread_cram_word;vs=core.retro_research_vsram_word;rr=core.retro_dread_vdp_reg
cpu=core.retro_research_cpu
for fn in (vr,cr,vs,rr,cpu):fn.argtypes=[C.c_uint];fn.restype=C.c_uint
names=[f'D{i}' for i in range(8)]+[f'A{i}' for i in range(8)]+['PC','SR','SP','USP','ISP']
def snapshot(label):
 folder=a.out/label;folder.mkdir(exist_ok=True);regs=[rr(i) for i in range(32)]
 data={'vram':words(vr,65536),'cram-packed':words(cr,128),'vsram':words(vs,80),'vdp-registers':bytes(regs)}
 cram=np.frombuffer(data['cram-packed'],dtype='>u2');wire=((cram&7)<<1)|((cram&0x38)<<2)|((cram&0x1c0)<<3)
 data['cram']=wire.astype('>u2').tobytes()
 for k,b in data.items():(folder/(k+'.bin')).write_bytes(b)
 ram=C.string_at(e.ram,65536);ram=b''.join(ram[i:i+2][::-1] for i in range(0,len(ram),2));(folder/'workram.bin').write_bytes(ram)
 cpu_regs={n:f'0x{cpu(i):08x}' for i,n in enumerate(names)}
 state={'vdp_registers':regs,'cpu':cpu_regs,'sha256':{k:hashlib.sha256(b).hexdigest() for k,b in data.items()},'plane_A':(regs[2]&56)<<10,'plane_B':(regs[4]&7)<<13,'SAT':(regs[5]&127)<<9,'window':(regs[3]&60)<<10,'cram_words':[f'{x:03X}' for x in wire]}
 (folder/'state.json').write_text(json.dumps(state,indent=2)+'\n');e.screenshot().save(folder/'screen.png')
 # Decode physical 4bpp tiles. No aspect correction; CRAM DAC levels follow common MD model.
 dac=np.array([0,52,87,116,144,172,206,255],dtype='uint8');palette=np.stack([dac[(wire>>1)&7],dac[(wire>>5)&7],dac[(wire>>9)&7]],1)
 raw=np.frombuffer(data['vram'],dtype='uint8');px=np.stack([raw>>4,raw&15],axis=-1).reshape(2048,8,8)
 atlas=px.reshape(64,32,8,8).transpose(0,2,1,3).reshape(512,256);Image.fromarray(palette[:16][atlas]).save(folder/'tiles-PAL0.png')
 width=[32,64,0,128][regs[16]&3];height=[32,64,0,128][regs[16]>>4&3];vw=np.frombuffer(data['vram'],dtype='>u2')
 for plane in ['A','B']:
  base=state['plane_'+plane];attrs=np.array([vw[((base//2)+i)%32768] for i in range(width*height)]).reshape(height,width)
  img=np.zeros((height*8,width*8,3),dtype='uint8')
  for y in range(height):
   for x in range(width):
    attr=int(attrs[y,x]);tile=px[attr&2047]
    if attr&0x800:tile=tile[:,::-1]
    if attr&0x1000:tile=tile[::-1]
    img[y*8:y*8+8,x*8:x*8+8]=palette[((attr>>13)&3)*16+tile]
  Image.fromarray(img).save(folder/('plane-'+plane+'.png'));(folder/('plane-'+plane+'-attributes.json')).write_text(json.dumps(attrs.tolist()))
 sat=state['SAT'];sprites=[];idx=0
 for _ in range(80):
  v=[int(vw[(sat//2+4*idx+j)%32768]) for j in range(4)];sprites.append({'index':idx,'words':v,'palette':v[2]>>13&3,'tile':v[2]&2047,'x':(v[3]&511)-128,'y':(v[0]&511)-128})
  idx=v[1]&127
  if not idx:break
 (folder/'sprites.json').write_text(json.dumps(sprites,indent=2)+'\n');return data
initial=snapshot('spawn');e.step(60,capture=True);later=snapshot('still-plus-60')
changed=[i for i,(x,y) in enumerate(zip(initial['vram'],later['vram'])) if x!=y];(a.out/'vram-difference.json').write_text(json.dumps({'changed_bytes':len(changed),'tiles':sorted(set(i//32 for i in changed))},indent=2)+'\n')
C.c_uint.in_dll(core,'retro_trace_dmas').value=0;C.c_uint.in_dll(core,'retro_trace_regs').value=0
C.c_uint.in_dll(core,'retro_trace_active').value=1;C.c_uint.in_dll(core,'retro_research_active').value=1
start=C.c_uint.in_dll(core,'retro_trace_frame').value
elapsed=0
while elapsed < a.frames:
 e.step(1,6 if a.turn else None,capture=True);elapsed+=1
 if C.c_uint.in_dll(core,'retro_research_captured').value:break
e.step(1,6 if a.turn else None,capture=True);elapsed+=1
snapshot('first-published')
e.step(a.frames-elapsed,6 if a.turn else None,capture=True)
C.c_uint.in_dll(core,'retro_research_active').value=0;C.c_uint.in_dll(core,'retro_trace_active').value=0
for key,nbytes in [('completed_source',11520),('completed_tiles',23040)]:
 (a.out/(key+'.bin')).write_bytes(bytes((C.c_ubyte*nbytes).in_dll(core,'retro_research_'+key)))
(a.out/'vdp-cpu-writes-scanlines.json').write_text(json.dumps(list((C.c_uint*313).in_dll(core,'retro_research_vdp_lines')))+'\n')
npb=C.c_uint.in_dll(core,'retro_research_probes').value
probes=np.ctypeslib.as_array((C.c_uint*(32768*22)).in_dll(core,'retro_research_probe')).reshape(-1,22)[:npb].copy()
(a.out/'probes.json').write_text(json.dumps(probes.tolist())+'\n')
(a.out/'framebuffer-last.bin').write_bytes(bytes((C.c_ubyte*11520).in_dll(core,'retro_research_buffer')))
n=C.c_uint.in_dll(core,'retro_trace_dmas').value;d=np.ctypeslib.as_array((C.c_uint*(32768*6)).in_dll(core,'retro_trace_dma')).reshape(-1,6)[:n].copy()
nr=C.c_uint.in_dll(core,'retro_trace_regs').value;r=np.ctypeslib.as_array((C.c_uint*(16384*4)).in_dll(core,'retro_trace_reg')).reshape(-1,4)[:nr].copy()
cycles=np.ctypeslib.as_array((C.c_ulonglong*1048576).in_dll(core,'retro_research_cycles')).copy();hits=np.ctypeslib.as_array((C.c_uint*1048576).in_dll(core,'retro_research_hits')).copy()
np.savez_compressed(a.out/'profile.npz',cycles=cycles,hits=hits)
(a.out/'dma-scanlines.json').write_text(json.dumps(list((C.c_uint*32768).in_dll(core,'retro_research_dma_lines'))[:n])+'\n')
(a.out/'dmas.json').write_text(json.dumps(d.tolist())+'\n');(a.out/'register2-writes.json').write_text(json.dumps(r.tolist())+'\n')
top=np.argsort(cycles)[-80:][::-1];total=int(cycles.sum());(a.out/'hot-pcs.json').write_text(json.dumps([{'pc':f'0x{i*2:06x}','master_cycles':int(cycles[i]),'instructions':int(hits[i]),'percent':round(100*int(cycles[i])/total,4)} for i in top],indent=2)+'\n')
summary={'rom_sha256':hashlib.sha256(a.rom.read_bytes()).hexdigest(),'rom_size':a.rom.stat().st_size,'core_sha256':hashlib.sha256(a.core.read_bytes()).hexdigest(),'region':'NTSC','video_frames':a.frames,'trace_start_video_frame':start,'sram_mode':a.sram,'turn':a.turn,'dma_count':n,'register2_write_count':nr,'dma_lengths_words':dict(collections.Counter(map(int,d[:,4]))),'dma_sources':dict(collections.Counter(hex(int(x)) for x in d[:,2])),'dma_destinations':dict(collections.Counter(hex(int(x)) for x in d[:,3])),'instruction_master_cycles':total,'sram_access_counts':[int(x) for x in (C.c_ulonglong*4).in_dll(core,'retro_sram_counts')]}
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');snapshot('end');print(json.dumps(summary));print('HOT',[(hex(int(i)*2),round(int(cycles[i])*100/total,2)) for i in top[:15]]);e.close()
