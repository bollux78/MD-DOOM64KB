#!/usr/bin/env python3
"""Sample interrupted PCs after the first R39 scene starts; existing binary only."""
import pathlib,importlib.util,subprocess,collections,bisect,json,sys
p=pathlib.Path(__file__).with_name('r64a_rsp_capture.py');sp=importlib.util.spec_from_file_location('rsp',p);rsp=importlib.util.module_from_spec(sp);sp.loader.exec_module(rsp)
rom,elf=sys.argv[1:];s=rsp.symbols(elf)
def sym(n):
 if n in s:return s[n]
 m=[v for k,v in s.items() if k.startswith(n+'.')];assert len(m)==1,(n,m);return m[0]
nm=subprocess.run(['/home/dan/mars/m68k-elf/bin/m68k-elf-nm','-n',elf],capture_output=True,text=True,check=True).stdout
funcs=[(int(x[0],16),x[2]) for l in nm.splitlines() if len(x:=l.split())==3 and x[1] in ('t','T','w','W')];addrs=[x[0] for x in funcs]
def name(pc):
 i=bisect.bisect_right(addrs,pc)-1;return funcs[i][1] if i>=0 else '?'
g=rsp.RSP('/home/dan/Projetos/blastem64-1.0.0/blastem',rom,10000,120)
samples=[]
try:
 g.req('qSupported');begin=sym('R39M_BeginScene')&0xffffff;g.req('Z0,%x,2'%begin);g.cont();g.req('z0,%x,2'%begin)
 vint=int.from_bytes(pathlib.Path(rom).read_bytes()[0x78:0x7c],'big')&0xffffff;g.req('Z0,%x,2'%vint)
 for i in range(300):
  g.cont();regs=g.req('g');stack=int(regs[15*8:16*8],16)&0xffffff;f=g.readmem(stack,32);pc=int.from_bytes(f[2:6],'big')&0xffffff
  tic=int.from_bytes(g.readmem(sym('_g_gametic'),4),'big');vb=int.from_bytes(g.readmem(sym('_g_vblankCount'),4),'big')
  samples.append((pc,name(pc),tic,vb,hex(stack),f.hex()))
  if i<8:print('SAMPLE',samples[-1],flush=True)
 print('TOP',collections.Counter((hex(p),n) for p,n,*_ in samples).most_common(15),flush=True)
 print('LAST',samples[-1],flush=True)
 for n in ('r22_ready','r39m_scene_active','r39m_palette'):
  print(n,g.readmem(sym(n),2 if n=='r22_ready' else 1).hex(),flush=True)
finally:g.close()
