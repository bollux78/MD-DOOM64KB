#!/usr/bin/env python3
"""Convert original shareware E1M2 to the Doom64KB big-endian ROM format."""
from pathlib import Path
import argparse,base64,collections,hashlib,json,math,struct,zlib
R=Path(__file__).resolve().parents[2]
SOURCE_SHA='1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771'
TARGET_ORDER=['THINGS','LINEDEFS','SIDEDEFS','SEGS','SSECTORS','NODES','SECTORS','REJECT','BLOCKMAP']
def read_wad(b,be=False):
 e='>' if be else '<';n=struct.unpack_from(e+('h' if be else 'i'),b,4)[0];o=struct.unpack_from(e+'i',b,8)[0];out=[]
 assert b[:4]==b'IWAD' and 0<n<32768
 for i in range(n):
  j=o+16*i;p=struct.unpack_from(e+'i',b,j)[0];s=struct.unpack_from(e+('H' if be else 'i'),b,j+4)[0];name=b[j+8:j+16].split(b'\0')[0].decode('ascii');assert 0<=p<=len(b) and p+s<=len(b);out.append((name,b[p:p+s]))
 return out
def map_at(l,name,original=False):
 i=next(i for i,x in enumerate(l) if x[0]==name);return dict(l[i+1:i+(11 if original else 10)])
def recs(b,fmt):
 s=struct.calcsize(fmt);assert len(b)%s==0;return list(struct.iter_unpack(fmt,b))
def texnames(b):
 n=struct.unpack_from('>i',b)[0];return [b[o:o+8].rstrip(b'\0').decode() for o in struct.unpack_from('>'+str(n)+'i',b,4)]
def pack_source(source,base):
 assert hashlib.sha256(source).hexdigest()==SOURCE_SHA
 src=read_wad(source);bm=read_wad(base,True);d=dict(src);bd=dict(bm);pal=[tuple(d['PLAYPAL'][3*i:3*i+3]) for i in range(256)];known={}
 for mn in ['E1M1','E1M8']:
  a=recs(map_at(src,mn,True)['SECTORS'],'<hh8s8s3h');b=recs(map_at(bm,mn)['SECTORS'],'>hhhhBbh')
  assert len(a)==len(b)
  for x,y in zip(a,b):known[(x[2].rstrip(b'\0').decode(),x[4])]=y[2];known[(x[3].rstrip(b'\0').decode(),x[4])]=y[3]
 m=map_at(src,'E1M2',True);colors=[];fallback=[]
 def color(name,light):
  name=name.rstrip(b'\0').decode()
  if name=='F_SKY1':return -2
  if name.startswith('NUKAGE'):return -3
  if (name,light) in known:return known[name,light]
  pixels=d[name];assert len(pixels)==4096
  rgb=[sum(pal[p][c] for p in pixels)*light/(4096*255) for c in range(3)]
  k=min(range(256),key=lambda i:sum((pal[i][c]-rgb[c])**2 for c in range(3)));fallback.append((name,light,k));return k
 for s in recs(m['SECTORS'],'<hh8s8s3h'):colors.append([color(s[2],s[4]),color(s[3],s[4])])
 return dict(version=1,source_sha256=SOURCE_SHA,map='E1M2',base_textures_sha256=hashlib.sha256(bd['TEXTURE1']).hexdigest(),raw={k:base64.b64encode(zlib.compress(v,9)).decode() for k,v in m.items()},raw_sha256={k:hashlib.sha256(v).hexdigest() for k,v in m.items()},flat_colors=colors,flat_fallback=sorted(set(fallback)))
def convert(payload,base):
 assert payload['source_sha256']==SOURCE_SHA and payload['map']=='E1M2'
 bd=dict(base);assert hashlib.sha256(bd['TEXTURE1']).hexdigest()==payload['base_textures_sha256']
 m={k:zlib.decompress(base64.b64decode(v)) for k,v in payload['raw'].items()}
 for k,v in m.items():assert hashlib.sha256(v).hexdigest()==payload['raw_sha256'][k]
 vertices=recs(m['VERTEXES'],'<hh');lines=recs(m['LINEDEFS'],'<7H');sides=recs(m['SIDEDEFS'],'<hh8s8s8sH');sectors=recs(m['SECTORS'],'<hh8s8s3h')
 assert len(sectors)<255 and len(lines)<2048
 tx={n:i for i,n in enumerate(texnames(bd['TEXTURE1']))};tx['-']=0
 def texture(n):
  n=n.rstrip(b'\0').decode().upper();assert n in tx,n;assert tx[n]<128;return tx[n]
 mutable={s for ln in lines if ln[3] for s in ln[5:7] if s!=65535}
 lookup={};dedup=[];side_index={}
 for i,s in enumerate(sides):
  key=(i,s) if i in mutable else (None,s)
  if key not in lookup:
   lookup[key]=len(dedup);x,y,top,bottom,mid,sec=s;assert 0<=sec<len(sectors);dedup.append(struct.pack('>hBbbbB',x,y&255,texture(top),texture(bottom),texture(mid),sec))
  side_index[i]=lookup[key]
 out={'SIDEDEFS':b''.join(dedup)};lineout=[]
 for i,(v1,v2,flags,special,tag,s0,s1) in enumerate(lines):
  x1,y1=vertices[v1];x2,y2=vertices[v2];dx=x2-x1;dy=y2-y1;assert -32768<=dx<32768 and -32768<=dy<32768
  slope=1 if not dx else 0 if not dy else 3 if (dx<0)!=(dy<0) else 2
  assert special<128 and flags<512 and tag<32768
  lineout.append(struct.pack('>hhhhHhhHHhhhhhBbb',x1,y1,x2,y2,i,dx,dy,side_index[s0],side_index[s1] if s1!=65535 else s1,max(y1,y2),min(y1,y2),min(x1,x2),max(x1,x2),tag,flags&255,slope,special))
 out['LINEDEFS']=b''.join(lineout);segout=[]
 for v1,v2,angle,li,sd,offset in recs(m['SEGS'],'<6H'):
  ln=lines[li];s0=ln[5+sd];s1=ln[6-sd];assert sd in [0,1] and s0!=65535
  x1,y1=vertices[v1];x2,y2=vertices[v2];assert offset<32768
  segout.append(struct.pack('>hhhhHHHHBB',x1,y1,x2,y2,offset,angle,side_index[s0],li,sides[s0][5],sides[s1][5] if s1!=65535 else 255))
 out['SEGS']=b''.join(segout)
 for name in ['SSECTORS','NODES','BLOCKMAP']:
  words=recs(m[name],'<H');out[name]=b''.join(struct.pack('>H',x[0]) for x in words)
 out['SECTORS']=b''.join(struct.pack('>hhhhBbh',s[0],s[1],f,c,s[4],s[5],s[6]) for s,(f,c) in zip(sectors,payload['flat_colors']))
 out['REJECT']=m['REJECT'];things=[];types=collections.Counter()
 for x,y,a,t,op in recs(m['THINGS'],'<5h'):
  if t in [2,3,4,11] or op&16:continue
  assert a%45==0 and op<128;things.append(struct.pack('>hhhbb',x,y,t,(a//45)%8,op));types[t]+=1
 out['THINGS']=b''.join(things)
 for name in TARGET_ORDER:assert len(out[name])<=65535,(name,len(out[name]))
 # Independent structural comparisons with source records.
 assert len(out['LINEDEFS'])//31==1033 and len(out['SECTORS'])//12==200 and len(things)==242
 for i,ln in enumerate(lines):
  z=struct.unpack_from('>hhhhHhhHHhhhhhBbb',out['LINEDEFS'],i*31);assert z[:4]==(*vertices[ln[0]],*vertices[ln[1]]) and z[4]==i and z[-1]==ln[3]
 for a,b in zip(recs(out['SEGS'],'>hhhhHHHHBB'),recs(m['SEGS'],'<6H')):assert a[:4]==(*vertices[b[0]],*vertices[b[1]]) and a[4]==b[5] and a[5]==b[2] and a[7]==b[3]
 report=dict(map='E1M2',things=len(things),linedefs=len(lines),sidedefs=len(dedup),sectors=len(sectors),segs=len(segout),subsectors=len(out['SSECTORS'])//4,nodes=len(out['NODES'])//28,thing_types=dict(types),skill_counts=[sum(t[2]==1 or (t[4]&bit)!=0 for t in recs(out['THINGS'],'>hhhbb')) for bit in [1,2,4]],blockmap=list(struct.unpack_from('>4h',out['BLOCKMAP'])),lumps={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in out.items()})
 return out,report

def associations(m):
 lines=recs(m['LINEDEFS'],'>hhhhHhhHHhhhhhBbb');sides=recs(m['SIDEDEFS'],'>hBbbbB');n=len(m['SECTORS'])//12;groups=[[] for _ in range(n)]
 for i,l in enumerate(lines):
  front=sides[l[7]][-1];back=sides[l[8]][-1] if l[8]!=65535 else None;groups[front].append(i)
  if back is not None and back!=front:groups[back].append(i)
 flat=[];offs=[0]
 for g in groups:flat.extend(g);offs.append(len(flat))
 return struct.pack('>'+str(len(flat))+'H',*flat),struct.pack('>'+str(len(offs))+'H',*offs)
def write_wad(l):
 b=bytearray(b'IWAD'+struct.pack('>hhI',len(l),0,0));entries=[];shared={}
 for name,data in l:
  if data in shared:
   entries.append((shared[data],len(data),name));continue
  while len(b)&3:b.append(0)
  p=len(b) if data else 0;b.extend(data);entries.append((p,len(data),name));shared[data]=p
 while len(b)&3:b.append(0)
 struct.pack_into('>I',b,8,len(b))
 for p,size,name in entries:assert size<=65535;b.extend(struct.pack('>IHH8s',p,size,0,name.encode().ljust(8,b'\0')))
 return bytes(b)
def apply(payload,basebytes):
 base=read_wad(basebytes,True);new,report=convert(payload,base);i=next(i for i,x in enumerate(base) if x[0]=='E1M2');base[i+1:i+10]=[(k,new[k]) for k in TARGET_ORDER]
 for num in [1,2,8]:
  a,b=associations(map_at(base,f'E1M{num}'));base.extend([(f'S{num}LINES',a),(f'S{num}OFFS',b)])
 out=write_wad(base);check=read_wad(out,True)
 for name in ['E1M1','E1M8']:assert map_at(check,name)==map_at(read_wad(basebytes,True),name)
 assert map_at(check,'E1M2')==new;report['converted_wad_sha256']=hashlib.sha256(out).hexdigest();report['wad_bytes']=len(out);return out,report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--payload',type=Path,required=True);p.add_argument('--base',type=Path,default=R/'scripts/doom64.wad');p.add_argument('--out',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
 if a.source:a.payload.write_text(json.dumps(pack_source(a.source.read_bytes(),a.base.read_bytes()),separators=(',',':'))+'\n')
 payload=json.loads(a.payload.read_text());out,report=apply(payload,a.base.read_bytes())
 if a.out:a.out.write_bytes(out)
 if a.report:a.report.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ['map','things','linedefs','sidedefs','sectors','subsectors','skill_counts','blockmap','wad_bytes']},indent=2))
