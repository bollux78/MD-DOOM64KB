"""Independent fixed-point vertex transform and frustum clipping, derived from observations."""
def s16(v):v&=65535;return v-65536 if v&32768 else v
def s32(v):v&=0xffffffff;return v-0x100000000 if v&0x80000000 else v
def truncdiv(a,b):
 if not b:raise ZeroDivisionError
 return (abs(a)//abs(b))*(-1 if (a<0) != (b<0) else 1)
def divs(a,b):
 q=truncdiv(s32(a),s16(b))
 if not -32768<=q<=32767:raise OverflowError(('DIVS',a,b,q))
 return q

def transform(mem,vertex):
 """Match 16-bit wrapping, signed MULS, left shift and SWAP selection."""
 cached=mem.s16(vertex+4)
 if cached:return cached,mem.s16(vertex+6)
 x=s16(s16(mem.s16(vertex)<<3)-mem.s16(0xff1a32));y=s16(s16(mem.s16(vertex+2)<<3)-mem.s16(0xff1a30))
 co=mem.s16(0xff1a2c);si=mem.s16(0xff1a2a)
 tx=s16(((x*co-y*si)<<2)>>16);tz=s16(((x*si+y*co)<<2)>>16)
 mem.put(vertex+4,tx,2);mem.put(vertex+6,tz,2)
 return tx,tz

def project(mem,wall,variant):
 vb=mem.u32(0xff1018);p0=vb+mem.s16(wall+8);p1=vb+mem.s16(wall+10)
 x0,z0=transform(mem,p0);x1,z1=transform(mem,p1);transformed=[x0,z0,x1,z1]
 table=0x76ec2+16*(variant&255);near=mem.s16(table+8);textured=bool(near&1)
 u0=u1=None
 if textured:
  uv=mem.u32(0xff101c)+mem.s16(wall+24);u0=mem.s16(uv+4);u1=mem.s16(uv+6)
 def result(rejected=False,**kw):return dict(transformed=transformed,rejected=rejected,textured=textured,variant=variant,**kw)
 l0=s16(x0+z0)
 if l0<0:
  l1=s16(x1+z1)
  if l1<0:return result(True)
  den=s16(l1-l0)
  if textured:u0=s16(u0-divs(s16(u1-u0)*l0,den))
  x0=s16(x0-divs(s16(x1-x0)*l0,den));z0=s16(-x0)
 r1=s16(z1-x1)
 if r1<0:
  r0=s16(z0-x0)
  if r0<0:return result(True)
  den=s16(r0-r1)
  x1=s16(x1-divs(s16(x0-x1)*r1,den))
  if textured:u1=s16(u1-divs(s16(u0-u1)*r1,den))
  z1=x1
 z0=s16(z0-near);z1=s16(z1-near)
 if z0<0:
  if z1<0:return result(True)
  den=s16(z0-z1)
  if textured:u0=s16(u0-divs(s16(u0-u1)*z0,den))
  x0=s16(x0-divs(s16(x0-x1)*z0,den));z0=0
 elif z1<0:
  den=s16(z0-z1)
  if textured:u1=s16(u1-divs(s16(u0-u1)*z1,den))
  x1=s16(x1-divs(s16(x0-x1)*z1,den));z1=0
 z0=s16(z0+near);z1=s16(z1+near)
 sx0=max(0,s16(divs(x0*80,z0)+80));sx1=min(160,s16(divs(x1*80,z1)+80));width=s16(sx1-sx0)
 if width<=0:return result(True)
 inv0=0x500000//(z0&65535);inv1=0x500000//(z1&65535)
 if inv0>65535 or inv1>65535:raise OverflowError(('DIVU',z0,z1))
 step=divs(inv1-inv0,width)
 job={}
 if textured:
  a=(u0<<7)&65535;b=(u1<<7)&65535;prod0=a*inv0;prod1=b*inv1
  mean_inv=(inv0+inv1)//2;mean_product=(prod0+prod1)//2;mean_u=(a+b)//2
  approximate=mean_product//mean_inv
  if approximate>65535:raise OverflowError('Mean DIVU')
  # BGE observes N==V, not merely the sign of the wrapped difference.
  error=(mean_u-approximate)&65535
  if s16(mean_u)<s16(approximate):error=(-error)&65535
  residual=(error-512)&65535
  linear=error<512
  if not linear:linear=residual<(10000000//mean_inv)
  left=a if linear else prod0;right=b if linear else prod1
  du=abs(right-left)//width
  if right<left:du=-du
  job=dict(texture_start=left&0xffffffff,texture_step=du&0xffffffff,linear=linear,texture=mem.u32(wall),kernel=mem.u32(table+(4 if linear else 0)))
 else:job=dict(kernel=mem.u32(table))
 return result(False,x0=sx0,x1=sx1,width=width,inv0=inv0,inv1=inv1,scale_step=step,u0=u0,u1=u1,depth0=z0,depth1=z1,**job)
