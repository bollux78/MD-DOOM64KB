import sys,ctypes as C,struct,math,json,subprocess
from pathlib import Path
import os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native-perspective'));import validation as v
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'));from conv import Wad
(v.ROOT/'shots').mkdir(exist_ok=True)
VARIANT=os.environ.get('DREAD_GAME_VARIANT','game')
w=Wad(os.environ['DREAD_TEST_WAD']);results=[]
def write(g,addr,b):C.memmove(g.e.ram+addr,b''.join(b[i:i+2][::-1] for i in range(0,len(b),2)),len(b))
def warp(g,x,y,angle=0):write(g,g.syms['view'][0],struct.pack('>iihH',round(x*65536),round(y*65536),41,round(angle/360*65536)&65535))
def fixture(mapid):
 g=v.Game(VARIANT);g.play(mapid);g.put('bench_req',3);g.put('bench_done',3);return g
def things(mapid):
 i=w.find('E1M'+str(mapid+1));d=w.idx(i+1)
 return [struct.unpack_from('<5h',d,j) for j in range(0,len(d),10)]
