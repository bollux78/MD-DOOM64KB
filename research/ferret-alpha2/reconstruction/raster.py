"""Independent scalar raster model. Only decoded wall variants are supported."""
from projection import project,s16,truncdiv

def render(mem,records):
 out=bytearray(11520);coverage=bytearray(11520);cliptop=[0]*160;clipbottom=[72]*160;unsupported={}
 z=mem.s16(0xff1a2e)
 def write(x,y,c):
  if 0<=y<72:
   i=(x//2)*144+(x&1)+y*2;out[i]=c;coverage[i]=1
 for flag,wall in records:
  variant=mem.u8(wall+14+(flag&1));job=project(mem,wall,variant)
  if job['rejected']:continue
  if variant not in range(18):unsupported[variant]=unsupported.get(variant,0)+1;continue
  n=job['width'];heights=[mem.s16(wall+16+2*i) for i in range(4)]
  edge0=[(job['inv0']>>5)*(h-z)+9344 for h in heights]
  ds=[truncdiv((job['inv1']>>5)*(h-z)-(job['inv0']>>5)*(h-z),n) for h in heights]
  for j in range(n):
   x=job['x0']+j;top=cliptop[x];bottom=clipbottom[x]
   if top>=bottom:continue
   rows=[s16((a+d*j)>>8) for a,d in zip(edge0,ds)]
   inv=(job['inv0']+job['scale_step']*j)&65535
   def fill(lo,hi,color,sky=False):
    for y in range(max(top,lo),min(bottom,hi)):
     if sky:
      ptr=mem.u32(mem.u32(0xff0fd6)+4*x);c=mem.u8(ptr+y)
     else:c=color
     write(x,y,c)
   def texture(lo,hi,pointer):
    if not job['textured']:return
    u=(job['texture_start']+job['texture_step']*j)&0xffffffff
    if job['linear']:offset=u&0x1f80
    else:offset=(u//inv)&0x1f80
    tex=pointer+(z>>1)+offset
    scaler=0x21b1c+mem.u32(0x6d4ae+((inv>>3)&0x1ffc))
    for y in range(max(top,lo),min(bottom,hi)):
     disp=mem.s16(scaler+12*y+10)
     write(x,y,mem.u8(tex+disp))
   c0=mem.u8(wall+12);c1=mem.u8(wall+13)
   sky=variant in [2,3,12,13,14,15,16,17]
   ceiling=variant in [0,1,2,3,6,7,8,9,10,11,12,13,14,15,16,17]
   upper=variant in [0,1,2,3,9,10,11,15,16,17]
   lower=variant in [1,3,5,8,11,14,17]
   floor=variant in [0,1,2,3,4,5,7,8,10,11,13,14,16,17]
   if ceiling:fill(top,rows[0],c0,sky)
   if upper:texture(rows[0],rows[1],mem.u32(wall))
   lower_start=rows[1] if variant in [1,3] else rows[2]
   if lower:texture(lower_start,rows[3],mem.u32(wall+4))
   floor_start=rows[1] if variant in [0,2] else (rows[3] if lower else rows[2])
   if floor:fill(floor_start,bottom,c1)
   if variant in [0,1,2,3]:cliptop[x]=clipbottom[x]=0
   else:
    edge_top=rows[1] if upper else (rows[0] if ceiling else top)
    edge_bottom=lower_start if lower else (floor_start if floor else bottom)
    cliptop[x]=min(bottom,max(top,edge_top));clipbottom[x]=max(top,min(bottom,edge_bottom))

 return out,coverage,{'unsupported':unsupported,'uncovered_bytes':coverage.count(0),'open_columns':sum(t<b for t,b in zip(cliptop,clipbottom))}
