#!/usr/bin/env python3
from pathlib import Path
import struct
from r84_texture_audit import audit
b=Path('scripts/doom64.wad').read_bytes(); n=struct.unpack_from('>h',b,4)[0]; d=struct.unpack_from('>I',b,8)[0]
lumps=[]
for i in range(n):
 o=d+i*16;p,z=struct.unpack_from('>IH',b,o);lumps.append((b[o+8:o+16].rstrip(b'\0').decode(),b[p:p+z]))
named=dict(lumps);tp=named['TEXTUREP'];nt=struct.unpack_from('>I',named['TEXTURE1'])[0]
cols=[];audit('scripts/doom64.wad',columns=cols);pool=bytearray();dedup={};lookup={}
for t,x,c in cols:
 if c not in dedup:dedup[c]=len(pool);pool.extend(c)
 lookup[t,x]=dedup[c]
starts=[];entries=[];simple_starts=[];simple=[];patches=[]
for t in range(nt):
 off=struct.unpack_from('>H',tp,t*2)[0];mask,w,h,over,count=struct.unpack_from('>HhhBB',tp,off)
 starts.append(len(entries));entries.extend(lookup.get((t,x),0xffffffff) for x in range(0,mask+1,4))
 simple_starts.append(len(simple));pn=struct.unpack_from('>h',tp,off+12)[0];patches.append(pn if count==1 and not over else -1)
 if count==1 and not over:
  patch=lumps[pn][1];simple.extend(struct.unpack_from('>I',patch,8+x*4)[0]+3 for x in range(mask+1))
def arr(typ,name,v):return 'static const '+typ+' '+name+'[]={'+','.join(str(x)+'u' if x>=0 else str(x) for x in v)+'};\n'
out=arr('uint8_t','r84_pixels',pool)+arr('uint32_t','r84_offsets',entries)+arr('uint16_t','r84_starts',starts)
out+=arr('uint16_t','r84_simple_starts',simple_starts)+arr('int16_t','r84_patches',patches)+arr('uint32_t','r84_simple_offsets',simple)
Path('src/r84_columns.h').write_text(out)
print('R84 columns:',len(pool),'payload bytes;',len(simple),'simple entries')
