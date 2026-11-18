#!/usr/bin/env python3
"""Compile convex rooms and explicit portals. BSP is used offline only."""
from pathlib import Path
from fractions import Fraction as F
import sys,struct,math,json,hashlib
from doom_wad import directory,load_map
import doom_textures

def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return a[0]-b[0],a[1]-b[1]
def clean(p):
 q=[]
 for v in p:
  if not q or v!=q[-1]:q.append(v)
 if len(q)>1 and q[-1]==q[0]:q.pop()
 return q

def clip(poly,a,d,sign):
 out=[]
 if not poly:return out
 for p,q in zip(poly,poly[1:]+poly[:1]):
  u=sign*cross(d,sub(p,a));v=sign*cross(d,sub(q,a))
  if u>=0:out.append(p)
  if (u<0 and v>0) or (u>0 and v<0):
   t=u/(u-v);out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
 return clean(out)

def area(p):return sum(cross(a,b) for a,b in zip(p,p[1:]+p[:1]))
def key(a,b):return tuple(sorted((a,b)))
def split(polys):
 points=set(v for p,s in polys for v in p)
 out=[]
 for poly,sector in polys:
  q=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   d=sub(b,a);length=d[0]*d[0]+d[1]*d[1]
   on=[]
   for v in points:
    dv=sub(v,a);dot=d[0]*dv[0]+d[1]*dv[1]
    if 0<=dot<length and cross(d,dv)==0:on.append((dot,v))
   q.extend(v for _,v in sorted(on))
  out.append((clean(q),sector))
 return out

def union(a,b):
 edges={key(x,y):(x,y) for x,y in zip(a,a[1:]+a[:1])}
 for x,y in zip(b,b[1:]+b[:1]):
  k=key(x,y)
  if k in edges:del edges[k]
  else:edges[k]=(x,y)
 nxt={x:y for x,y in edges.values()}
 if len(nxt)!=len(edges):return None
 start=next(iter(nxt));p=[start];v=nxt[start]
 while v!=start and len(p)<=len(edges):p.append(v);v=nxt.get(v,start)
 if v!=start or len(p)!=len(edges):return None
 if any(cross(sub(p[(i+1)%len(p)],p[i]),sub(p[(i+2)%len(p)],p[(i+1)%len(p)]))<0 for i in range(len(p))):return None
 return p

def main():
 wad=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
 digest=hashlib.sha256(wad.read_bytes()).hexdigest()
 if digest!='1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771':
  raise ValueError('This prototype expects the unmodified Doom 1.9 shareware WAD')
 entries=directory(wad.read_bytes());data=load_map(entries,'E1M1')
 vertices,sectors,segs,leaves,nodes,root,spawn=data
 raw=dict(entries[next(i for i,e in enumerate(entries) if e[0]=='E1M1')+1:][:10])
 lines=list(struct.iter_unpack('<7H',raw['LINEDEFS']));sides=list(struct.iter_unpack('<hh8s8s8sH',raw['SIDEDEFS']))
 box=[(F(-1024),F(-5120)),(F(4096),F(-5120)),(F(4096),F(-1792)),(F(-1024),F(-1792))]
 cells=[]
 def walk(n,p):
  if n&32768:
   first,count=leaves[n&32767];sector=segs[first][2]
   for a,b,_,_ in segs[first:first+count]:p=clip(p,vertices[a],sub(vertices[b],vertices[a]),-1)
   if len(p)>=3 and area(p)>0:cells.append((p,sector))
   return
  x,y,dx,dy,children,bounds=nodes[n]
  for side in range(2):walk(children[side],clip(p,(x,y),(dx,dy),-1 if side==0 else 1))
 walk(root,box);initial=len(cells);cells=split(cells)
 while True:
  owners={};changed=False
  for i,(poly,sector) in enumerate(cells):
   for a,b in zip(poly,poly[1:]+poly[:1]):
    k=key(a,b)
    if k in owners:
     j=owners[k]
     if cells[j][1]==sector:
      merged=union(cells[j][0],poly)
      if merged is not None:
       cells[j]=(merged,sector);cells.pop(i);changed=True;break
    else:owners[k]=i
   if changed:break
  if not changed:break
 # Retain all junction points for reciprocal portal edges/material changes.
 cells=split(cells)
 owners={}
 for i,(p,s) in enumerate(cells):
  for a,b in zip(p,p[1:]+p[:1]):owners.setdefault(key(a,b),[]).append(i)
 images,unused=doom_textures.materials(entries,'E1M1');ids={name:i+1 for i,(name,*_) in enumerate(images)}
 output=['#include "neodoom.h"'];wallrows=[];roomrows=[];jsonrooms=[]
 for ri,(p,sector) in enumerate(cells):
  first=len(wallrows);jp=[]
  for a,b in zip(p,p[1:]+p[:1]):
   adjacent=[j for j in owners[key(a,b)] if j!=ri]
   assert len(adjacent)<=1
   neighbor=adjacent[0] if adjacent else 65535
   # Synthetic partitions carry no material; original lines determine textures.
   match=None
   mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
   for li,l in enumerate(lines):
    va,vb=vertices[l[0]],vertices[l[1]];d=sub(vb,va);v=sub(mid,va)
    if cross(d,v)!=0 or not 0<=d[0]*v[0]+d[1]*v[1]<=d[0]*d[0]+d[1]*d[1]:continue
    if not l[2]&4:neighbor=65535
    for side in (0,1):
     si=l[5+side]
     if si!=65535 and sides[si][-1]==sector:match=(li,l,side,sides[si]);break
    if match:break
   ax,ay=round(a[0]*4),round(a[1]*4);bx,by=round(b[0]*4),round(b[1]*4);dx,dy=bx-ax,by-ay
   if not(dx or dy):continue
   length=math.hypot(dx,dy);nx=round(dy*256/length);ny=round(-dx*256/length)
   middle=upper=lower=xoff=yoff=flags=uaxisx=uaxisy=uorigin=0
   if match:
    li,l,direction,side=match;xoff,yoff=side[:2];upper,lower,middle=[ids.get(doom_textures.name(n),0) for n in side[2:5]];flags=l[2]
    va,vb=(vertices[l[0]],vertices[l[1]]) if direction==0 else (vertices[l[1]],vertices[l[0]])
    d=sub(vb,va);ll=math.hypot(*d);uaxisx=round(d[0]*256/ll);uaxisy=round(d[1]*256/ll);uorigin=4*(va[0]*uaxisx+va[1]*uaxisy)
   wallrows.append((ax,ay,bx,by,nx,ny,nx*ax+ny*ay,neighbor,middle,upper,lower,xoff,yoff,flags,uaxisx,uaxisy,uorigin))
   jp.append([ax,ay,bx,by,neighbor])
  floor,ceiling=sectors[sector];roomrows.append((first,len(wallrows)-first,floor,ceiling,sector));jsonrooms.append(dict(sector=sector,edges=jp))
 xs=[v for e in wallrows for v in (e[0],e[2])];ys=[v for e in wallrows for v in (e[1],e[3])]
 assert max(xs)-min(xs)+max(ys)-min(ys)<32768,'relative rotations must fit signed 16 bits'
 def init(r):return '{'+','.join(map(str,r))+'}'
 output+=['const NdEdge nd_edges[]={'+','.join(map(init,wallrows))+'};','const NdRoom nd_rooms[]={'+','.join(map(init,roomrows))+'};',f'const uint16_t nd_room_count={len(cells)};']
 # Poses: original spawn plus interior points of spread-out walkable rooms.
 poses=[(spawn[0],spawn[1],spawn[2])]
 for p,s in cells:
  if sectors[s][1]-sectors[s][0]>=56:
   x=round(sum(v[0] for v in p)/len(p));y=round(sum(v[1] for v in p)/len(p))
   if all(math.hypot(x-a,y-b)>160 for a,b,_ in poses):poses.append((x,y,(len(poses)*67)%360))
  if len(poses)>=16:break
 output+=['const NdPose nd_poses[]={'+','.join(init((x*4,y*4,round(angle*256/360)%256)) for x,y,angle in poses)+'};',f'const uint16_t nd_pose_count={len(poses)};']
 for i,(name,w,h,pixels) in enumerate(images,1):
  # 64x64 texels, fixed strides and no arbitrary-width modulo in the 68000 loop.
  small=bytes(pixels[((x*w)//64)*h+(y*h)//64] for x in range(64) for y in range(64))
  output+=['static const uint8_t tex%d[4096]={%s};'%(i,','.join(map(str,small)))]
 output+=['const uint16_t nd_tex_width[]={64,'+','.join(str(w) for _,w,h,p in images)+'};', 'const uint16_t nd_tex_height[]={64,'+','.join(str(h) for _,w,h,p in images)+'};', 'const uint8_t *const nd_textures[]={0,'+','.join('tex%d'%i for i in range(1,len(images)+1))+'};','const uint16_t nd_palette[16]={'+','.join(map(str,doom_textures.COLORS))+'};',
 'const int16_t nd_sines[256]={'+','.join(str(round(256*math.sin(i*math.tau/256))) for i in range(256))+'};']
 (dest/'map_data.c').write_text('\n'.join(output)+'\n')
 report=dict(name='NeoDoom P0',map='E1M1',wad_sha256=hashlib.sha256(wad.read_bytes()).hexdigest(),original_bsp_leaves=len(leaves),nonempty_cells=initial,convex_rooms=len(cells),directed_edges=len(wallrows),directed_portals=sum(e[7]!=65535 for e in wallrows),textures=len(images),poses=len(poses),runtime_bsp_nodes=0)
 (dest/'map.json').write_text(json.dumps(dict(report=report,rooms=jsonrooms,edges=wallrows,room_records=roomrows,poses=poses),indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
