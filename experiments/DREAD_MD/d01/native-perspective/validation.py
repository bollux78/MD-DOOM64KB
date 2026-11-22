from pathlib import Path
import ctypes as C,sys,subprocess,json,hashlib
import numpy as np
from PIL import Image
from libretro_runner import Emulator
import os
ROOT=Path(os.environ['DREAD_TEST_ROOT']);(ROOT/'shots').mkdir(exist_ok=True)
CORE=Path(os.environ['DREAD_TEST_CORE'])
NM=Path(os.environ['DREAD_TEST_NM'])
class Game:
 def __init__(self,variant):
  self.name=variant;self.syms={}
  for line in subprocess.check_output([NM,'-S',ROOT/variant/'EPISODE.elf'],text=True).splitlines():
   c=line.split()
   if len(c)==4:self.syms[c[3]]=(int(c[0],16)&65535,int(c[1],16))
  self.e=Emulator(CORE,ROOT/variant/'EPISODE.bin')
  C.c_uint.in_dll(self.e.core,'retro_sram_block').value=1
  self.e.step(90,capture=True)
 def rd(self,name,size=2):return int.from_bytes(self.raw(name,size),'big')
 def raw(self,name,size=None):
  off,n=self.syms[name];return self.bytes(off,n if size is None else size)
 def bytes(self,off,n):
  b=C.string_at(self.e.ram+off,n);return b''.join(b[i:i+2][::-1] for i in range(0,n,2))
 def put(self,name,value,size=2):
  b=value.to_bytes(size,'big');C.memmove(self.e.ram+self.syms[name][0],b''.join(b[i:i+2][::-1] for i in range(0,size,2)),size)
 def press(self,button,after=40):self.e.step(40,button);self.e.step(after,capture=True)
 def play(self,map_index=0):
  self.press(3)
  if map_index:
   self.press(5);self.press(8)
   for _ in range(map_index):self.press(5)
  self.press(3,160)
  self.put('fcap',0)
  assert self.rd('selected_map')==map_index
 def shot(self,label):self.e.screenshot().save(ROOT/'shots'/f'{self.name}-{label}.png')
 def image(self,b):
  # Decode the existing byte layout, with two separate palette colours per byte.
  rom=(ROOT/self.name/'EPISODE.bin').read_bytes()
  syms={}
  for line in subprocess.check_output([NM,str(ROOT/self.name/'EPISODE.elf')],text=True).splitlines():
   c=line.split()
   if len(c)==3:syms[c[2]]=int(c[0],16)
  p=syms['md_palette'];pal=np.frombuffer(rom[p:p+32],dtype='>u2')
  dac=np.array([0,52,87,116,144,172,206,255],dtype='uint8')
  pal=np.stack([dac[(pal>>1)&7],dac[(pal>>5)&7],dac[(pal>>9)&7]],axis=1)
  data=np.frombuffer(b,dtype='uint8').reshape(40,72,4).transpose(1,0,2).reshape(72,160)
  colors=np.stack([data>>4,data&15],axis=-1).reshape(72,320)
  return Image.fromarray(np.repeat(pal[colors],2,axis=0))
 def route(self):
  self.put('bench_req',1);samples={};wanted={1,20,45,70,95,120,150,250,312};prev=0
  for tick in range(15000):
   self.e.step(1,capture=True);n=self.rd('bench_frames',4)
   if n!=prev and n in wanted:
    fb=self.bytes(self.syms['fbuf'][0]+((self.rd('cur_buf')^1)*11520),11520)
    samples[str(n)]=fb
    self.image(fb).save(ROOT/'shots'/f'{self.name}-route-{n:03d}.png')
   prev=n
   if self.rd('bench_done')>=1:break
  assert set(samples)==set(map(str,wanted)),(self.name,list(samples))
  result=dict(commit=self.name,frames=self.rd('bench_frames',4),vblanks=self.rd('bench_vints',4),samples={k:hashlib.sha256(v).hexdigest() for k,v in samples.items()})
  self.e.step(25,capture=True);self.shot('benchmark')
  (ROOT/(self.name+'-route.json')).write_text(json.dumps(result,indent=2)+'\n')
  for k,b in samples.items():(ROOT/self.name/f'frame-{k}.raw').write_bytes(b)
  return result
 def fixed(self):
  self.put('bench_req',3);self.put('bench_done',3)
  self.e.step(500,capture=True)
  view=self.raw('view',12).hex()
  for _ in range(200):
   if self.rd('dma_src',4):break
   self.e.step(1,capture=True)
  off=self.rd('dma_src',4)&65535;assert off
  fb=self.bytes(off,11520)
  (ROOT/self.name/'fixed.raw').write_bytes(fb)
  self.image(fb).save(ROOT/'shots'/f'{self.name}-fixed-raw.png')
  return dict(variant=self.name,view=view,framebuffer_sha256=hashlib.sha256(fb).hexdigest(),mode=self.rd('mode'))
 def modes(self):
  self.play();self.press(3,20);results=[]
  for target in [1,0,2,3,2,0]:
   current=self.rd('mode')
   if (current^target)&2:self.press(7)
   if (current^target)&1:self.press(5);self.press(7);self.press(4)
   assert self.rd('mode')==target
   self.press(3,110);a=np.asarray(self.e.screenshot());nonblack=int(np.count_nonzero(a[20:150]));assert nonblack>1000
   self.shot('mode-'+str(target));results.append(dict(mode=target,nonblack_components=nonblack))
   self.press(3,20)
  self.press(3,60);return results
 def spin(self,map_index=0):
  self.play(map_index)
  trace=C.c_uint.in_dll(self.e.core,'retro_trace_active');count=C.c_uint.in_dll(self.e.core,'retro_trace_regs');count.value=0
  regs=np.ctypeslib.as_array((C.c_uint*(16384*4)).in_dll(self.e.core,'retro_trace_reg')).reshape(-1,4)
  C.c_uint.in_dll(self.e.core,'retro_hint_pc').value=int.from_bytes((ROOT/self.name/'EPISODE.bin').read_bytes()[0x70:0x74],'big')&0xffffff
  C.c_uint.in_dll(self.e.core,'retro_hint_hits').value=0;C.c_ulonglong.in_dll(self.e.core,'retro_hint_cycles').value=0
  start=self.raw('view',12);trace.value=1
  self.e.step(1500 if map_index==0 else 300,6,capture=True);trace.value=0
  times=regs[:count.value,0].astype(np.int64);assert len(times)>5
  # Name-table flips mark the presentation of complete frames in row mode.
  intervals=np.diff(times);self.shot('spin-E1M'+str(map_index+1))
  return dict(map='E1M'+str(map_index+1),video_frames=1500 if map_index==0 else 300,intervals=len(intervals),vblanks=int(times[-1]-times[0]),fps=float(60*len(intervals)/(times[-1]-times[0])),interval_histogram={str(int(k)):int(v) for k,v in zip(*np.unique(intervals,return_counts=True))},start_view=start.hex(),end_view=self.raw('view',12).hex(),sram=False,mode='H40 lines')
