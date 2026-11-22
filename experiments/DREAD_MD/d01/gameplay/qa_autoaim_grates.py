from qa_support import *
def subat(mi,x,y):
 i=w.find('E1M'+str(mi+1));nd=w.idx(i+7);n=len(nd)//28-1
 while n<32768:
  nx,ny,dx,dy=struct.unpack_from('<4h',nd,n*28);children=struct.unpack_from('<2H',nd,n*28+24);n=children[0 if dy*(x-nx)>dx*(y-ny) else 1]
 return n&32767
# Autoaim from low floor to actual higher stair sector.
g=fixture(7);g.put('cheat_god',1);base=g.syms['actors'][0];n=g.syms['actors'][1]//22
for k in range(n):write(g,base+k*22+12,bytes([0,6]))
x,y=-16,-224;sub=subat(7,x,y);data=bytearray(g.bytes(base,22));struct.pack_into('>iiHh',data,0,x*65536,y*65536,sub,100);data[12]=0;data[13]=0;write(g,base,data)
# Lower the starting wall with real B first, then fire back at the stair monster.
warp(g,-128,-224,0);g.e.step(30);g.e.step(40,0);g.e.step(160);warp(g,200,-224,180);g.e.step(40);before=int.from_bytes(g.bytes(base+10,2),'big',signed=True);g.e.step(120,1);after=int.from_bytes(g.bytes(base+10,2),'big',signed=True);print('autoaim higher',sub,before,after,flush=True);g.shot('autoaim-higher');g.e.close()
# Inject an imp fireball immediately before an actual blocking grate on E1M9.
g=fixture(8);g.put('cheat_god',1);i=w.find('E1M9');ld=w.idx(i+2);sd=w.idx(i+3);vs=w.idx(i+4);sc=w.idx(i+8)
found=False
for k in range(len(ld)//14):
 a,b,flags,sp,tag,r,l=struct.unpack_from('<7H',ld,k*14)
 if l==65535 or not flags&1:continue
 mid=sd[r*30+20:r*30+28].rstrip(b'\0')
 if mid in (b'',b'-'):continue
 f=struct.unpack_from('<H',sd,r*30+28)[0];back=struct.unpack_from('<H',sd,l*30+28)[0];fh,fc=struct.unpack_from('<hh',sc,f*26);bh,bc=struct.unpack_from('<hh',sc,back*26);lo=max(fh,bh);hi=min(fc,bc)
 if hi-lo<50:continue
 ax,ay=struct.unpack_from('<hh',vs,a*4);bx,by=struct.unpack_from('<hh',vs,b*4);dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy);nx,ny=dy/length,-dx/length;x=(ax+bx)/2+nx*24;y=(ay+by)/2+ny*24
 if length<48:continue
 found=True;break
assert found
# Resolve the RAM projectile symbol, not the renderer function with the same static name.
for line in subprocess.check_output([v.NM,'-S',v.ROOT/VARIANT/'EPISODE.elf'],text=True).splitlines():
 c=line.split()
 if len(c)==4 and c[2]=='b' and c[3]=='proj':pa=int(c[0],16)&65535
for n in range(g.syms['actors'][1]//22):write(g,g.syms['actors'][0]+n*22+12,bytes([0,6]))
warp(g,x+nx*160,y+ny*160,0);g.e.step(20)
# x,y,vx,vy,z,vz,zfrac,sub,kind,state,tics,frame; projectile speed 2 map units / VBlank.
b=struct.pack('>iiiihhhHBBBB',round(x*65536),round(y*65536),round(-nx*2*65536),round(-ny*2*65536),lo+32,0,0,subat(8,round(x),round(y)),0,0,0,0);write(g,pa,b);g.put('bench_req',0);g.e.step(35,capture=True);out=g.bytes(pa,28);xx,yy=struct.unpack_from('>ii',out);side=(xx/65536-(ax+bx)/2)*nx+(yy/65536-(ay+by)/2)*ny
print('imp grate',k,mid.decode(),'side',side,'state',out[25],'kind',out[24],flush=True);g.shot('imp-through-grate');g.e.close()
