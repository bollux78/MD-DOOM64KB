from qa_support import *
results=[]
# Press a lift switch through the real B/use path.
g=fixture(1);i=w.find('E1M2');ld=w.idx(i+2);verts=w.idx(i+4);sectors=w.idx(i+8)
for j in range(0,len(ld),14):
 l=struct.unpack_from('<7H',ld,j)
 if l[3]!=62:continue
 ax,ay=struct.unpack_from('<hh',verts,l[0]*4);bx,by=struct.unpack_from('<hh',verts,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
 pose=((ax+bx)/2+dy/length*24,(ay+by)/2-dx/length*24,math.degrees(math.atan2(dx,-dy)))
 before=g.raw('floor_target');warp(g,*pose);g.e.step(40);g.e.step(40,0);g.e.step(50,capture=True);after=g.raw('floor_target')
 if after!=before:break
results.append({'case':'lift_B','changed_targets':sum(a!=b for a,b in zip(struct.unpack('>%dh'%(len(before)//2),before),struct.unpack('>%dh'%(len(after)//2),after)))})
g.shot('lift');g.e.close()
# Inspect a two-sided masked wall from nearby.
g=fixture(0);i=w.find('E1M1');ld=w.idx(i+2);verts=w.idx(i+4);l=struct.unpack_from('<7H',ld,298*14)
ax,ay=struct.unpack_from('<hh',verts,l[0]*4);bx,by=struct.unpack_from('<hh',verts,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
warp(g,(ax+bx)/2+dy/length*80,(ay+by)/2-dx/length*80,math.degrees(math.atan2(dx,-dy)));g.e.step(100,capture=True);g.shot('masked-wall')
results.append({'case':'masked_wall','queued':g.rd('nmasked'),'dropped_total':g.rd('r_mask_dropped')});g.e.close()
# Walk across an actual teleporter line from its front side.
g=fixture(4);g.put('bench_req',0);g.put('cheat_god',1);i=w.find('E1M5');ld=w.idx(i+2);verts=w.idx(i+4)
for j in range(0,len(ld),14):
 l=struct.unpack_from('<7H',ld,j)
 if l[3]!=97:continue
 ax,ay=struct.unpack_from('<hh',verts,l[0]*4);bx,by=struct.unpack_from('<hh',verts,l[1]*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy)
 x=(ax+bx)/2+dy/length*8;y=(ay+by)/2-dx/length*8
 warp(g,x,y,math.degrees(math.atan2(dx,-dy)));g.e.step(30);before=g.raw('view',12);g.e.step(25,4,capture=True);after=g.raw('view',12)
 x1,y1=struct.unpack_from('>ii',after);dist=math.hypot(x1/65536-x,y1/65536-y)
 if dist>128:break
results.append({'case':'teleport_walk','displacement':dist,'pass':dist>128});g.shot('teleport');g.e.close()
print(json.dumps(results,indent=2));(v.ROOT/'mechanism-results.json').write_text(json.dumps(results,indent=2))
