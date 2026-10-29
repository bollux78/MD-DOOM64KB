#!/usr/bin/env python3
"""Differential cache, clipping, map ABI and SRAM tests for R89 candidates."""
from pathlib import Path
import os,sys,tempfile,subprocess,shutil,ctypes,random,json
ROOT=Path(__file__).resolve().parents[2]
MODES=('control','cull','clip','cache','rom','map','spatial','video','all')
def fn(s,name):
 a=s.index(name);i=s.index('{',a);j=i+1;n=1
 while n:n+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[a:j]
def run(cmd,**kw):return subprocess.run(cmd,check=True,**kw)
def prepare(base):
 shutil.copytree(ROOT,base,ignore=shutil.ignore_patterns('.git','dist','__pycache__'))
 for f,e in [('apply_r81.py',{}),('apply_r80_performance.py',{'R80_EXPERIMENTS':'P1+F1'}),('apply_r83.py',{'R83_CANDIDATE':'sprites'}),('apply_r85.py',{'R85_CANDIDATE':'all'}),('apply_r88.py',{'R88_CANDIDATE':'ai'}),('apply_r89.py',{})]:
  run(['python3','scripts/lab/'+f],cwd=base,env={**os.environ,**e},stdout=subprocess.DEVNULL)
def cache_lib(d,out):
 s=(d/'src/r_draw.c').read_text();pool=[];offsets=[]
 # 32 textures force collisions/evictions; half-height, holes and complete columns.
 for t in range(32):
  for x in [0,4]:
   if t%3==0:
    offsets.append(len(pool));pool.extend((t*17+x*3+y)&255 for y in range(128))
   else:offsets.append(0xffffffff)
 pre='''#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#define __far
#define _fmemcpy memcpy
#define DOOM_R23_MAPMEM 1
#define DOOM_R39C_REUSE_CACHE 1
#define MAX_CACHE_ENTRIES 16
#define MAX_CACHE_TRIES 4
typedef uint8_t byte;
typedef struct {byte topdelta,length,pad;} column_t;
typedef struct {int16_t width,height,leftoffset,topoffset;uint32_t columnofs[8];byte posts[8][132];} patch_t;
typedef struct {int16_t originx,originy,patch_num,width;} texpatch_t;
typedef struct {uint16_t widthmask;int16_t height;uint8_t patchcount;texpatch_t patches[1];} texture_t;
static byte tmpCache[128],slots[16][128];static uint16_t columnCacheEntries[16],r39c_tmpEntry;static uint8_t r39c_tmpValid;
static patch_t fixtures[32];static texture_t textures[32];
static const void *W_GetLumpByNum(int n){return fixtures+n;}
static void SramCacheCopyTo(uint16_t k,const byte *p,uint16_t n){assert(n<=128);memcpy(slots[k],p,n);}
static void SramCacheCopyFrom(uint16_t k,byte *p,uint16_t n){assert(n<=128);memcpy(p,slots[k],n);}
'''
 if 'r89_rom_pending' in s:pre+='static const byte *r89_rom_pending;\n'
 pre+='static const uint8_t r84_pixels[]={'+','.join(map(str,pool))+'};\n'
 pre+='static const uint32_t r84_offsets[]={'+','.join(str(x)+'u' for x in offsets)+'};\n'
 pre+='static const uint16_t r84_starts[]={'+','.join(str(t*2) for t in range(32))+'};\n'
 pre+=fn(s,'static uint16_t CACHE_ENTRY(')+fn(s,'static void R_DrawColumnInCache(')+fn(s,'static uint16_t FindColumnCacheItem(')+fn(s,'static const byte __far* R_ComposeColumn(')
 pre+='''
void init(void){memset(slots,0xA5,sizeof slots);memset(tmpCache,0x5A,128);
 for(int t=0;t<32;t++){patch_t *p=fixtures+t;p->width=8;
 textures[t].widthmask=7;textures[t].height=t%3==2?64:128;textures[t].patchcount=1;textures[t].patches[0].patch_num=t;
 for(int x=0;x<8;x++){p->columnofs[x]=(byte*)p->posts[x]-(byte*)p;byte *c=p->posts[x];
 int start=t%3==0?0:7, len=t%3==0?128:23;
 c[0]=start;c[1]=len;for(int y=0;y<len;y++)c[3+y]=(t*17+x*3+y+start)&255;c[len+4]=255;
 }}}
void fetch(int t,int x,byte *out){memcpy(out,R_ComposeColumn(t,textures+t,x),128);}
void state(byte *out){memcpy(out,slots,sizeof slots);memcpy(out+sizeof slots,columnCacheEntries,sizeof columnCacheEntries);}
'''
 c=out.with_suffix('.c');c.write_text(pre);run(['cc','-shared','-fPIC','-O2',str(c),'-o',str(out)])
 lib=ctypes.CDLL(str(out));lib.init();return lib
with tempfile.TemporaryDirectory() as td:
 t=Path(td);base=t/'base';prepare(base);dirs={}
 for mode in MODES:
  d=t/mode;shutil.copytree(base,d);dirs[mode]=d
  run(['python3','scripts/lab/apply_r89_routes.py'],cwd=d,env={**os.environ,'R89_ROUTE':mode},stdout=subprocess.DEVNULL)
  m=(d/'src/m_text.c').read_text();b=(d/'scripts/lab/build_r71a12mul_hud.py').read_text()
  assert m.index('  quick_color,')<m.index('  selectlevel,')
  assert '{2,"Color mode:", M_ChangeColorMode}' in m and '&MainDef,options,' in m
  assert repr((mode,0)) in b and "(('pl','play'),)" in b
  assert (d/'src/p_enemy2.c').read_bytes()==(base/'src/p_enemy2.c').read_bytes()
 libs={m:cache_lib(dirs[m],t/(m+'.so')) for m in ('control','cache','rom','all')}
 rng=random.Random(8929);seq=[]
 for i in range(20000):
  tx=rng.randrange(32);x=rng.randrange(-256,257);seq.extend([(tx,x)]*rng.randrange(1,5))
 outputs={m:(ctypes.c_ubyte*128)() for m in libs};states={m:(ctypes.c_ubyte*2080)() for m in libs}
 for i,(tx,x) in enumerate(seq):
  for m,lib in libs.items():lib.fetch(tx,x,outputs[m]);lib.state(states[m])
  for m in ('cache','rom','all'):
   assert bytes(outputs[m])==bytes(outputs['control']),(i,m,tx,x,'pixels')
   assert bytes(states[m])==bytes(states['control']),(i,m,tx,x,'SRAM/replacement')
 print('PASS',len(seq),'actual C cache requests: repeats, collisions, evictions, partial columns and short copies; identical pixels/SRAM/tags')
 # All nine maps: align once, retain every field and every other lump.
 sys.path.insert(0,str(ROOT/'scripts/lab'))
 from convert_r24_episode import apply_all,read_wad
 from r89_align_maps import align
 blob,_=apply_all(json.loads((ROOT/'assets/r24-episode.json').read_text()),(ROOT/'scripts/doom64.wad').read_bytes())
 aligned=align(blob);a=read_wad(blob,True);b=read_wad(aligned,True)
 assert len(a)==len(b)
 for (n,x),(nn,y) in zip(a,b):
  assert n==nn
  if n=='LINEDEFS':assert b''.join(y[i:i+31] for i in range(0,len(y),32))==x
  else:assert x==y,n
 h=(dirs['map']/'src/r_defs.h').read_text();a=h.index('typedef struct line_s');b=h.index('typedef char assertLineSize',a)
 c=t/'abi.c';c.write_text('#include <stdint.h>\n#include <stddef.h>\n#include <assert.h>\ntypedef struct __attribute__((packed)){int16_t x,y;}vertex16_t;\n'+h[a:b]+'''int main(void){assert(sizeof(line_t)==32);assert(offsetof(line_t,tag)==26);assert(offsetof(line_t,const_special)==30);return 0;}''')
 run(['cc',str(c),'-o',str(t/'abi')]);run([str(t/'abi')]);print('PASS 9 maps aligned, all fields unchanged, line ABI 32 bytes; ROM growth',len(aligned)-len(blob))
 # Production SRAM helper with byte-lane mocks and preservation of adjacent fields.
 s=(dirs['spatial']/'src/r23_mapmem.c').read_text()
 c=t/'sram.c';c.write_text('''#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <string.h>
#define R22_SRAM_BASE 0x200000u
static uint8_t mem[65536];static unsigned opens,closes;
#define R25_SRAM_BEGIN() (++opens)
#define R25_SRAM_END() (++closes)
typedef struct{uint16_t validcount,r_validcount;uint8_t flags,special;}linedata_t;
static uint16_t line_base=7000;
static uint16_t R39C_MovepRead16(uint32_t a){a-=R22_SRAM_BASE;assert(a<65532 && (a&1));return mem[a]*256u+mem[a+2];}
static void R39C_MovepWrite16(uint32_t a,uint16_t v){a-=R22_SRAM_BASE;mem[a]=v>>8;mem[a+2]=v;}
'''+fn(s,'int R89_VisitLine(')+'''int main(void){memset(mem,0xA5,sizeof mem);for(int i=0;i<2048;i++){void *p=(void*)(uintptr_t)(0x210000u+i*6);uint32_t a=1+2*(line_base+i*6);for(int t=0;t<5;t++){uint16_t v=(uint16_t)(i*31+t);assert(R89_VisitLine(p,v));assert(!R89_VisitLine(p,v));assert(mem[a+4]==0xA5 && mem[a+6]==0xA5 && mem[a+8]==0xA5 && mem[a+10]==0xA5);}}assert(opens==closes);return 0;}''')
 run(['cc','-O2',str(c),'-o',str(t/'sram')]);run([str(t/'sram')]);print('PASS SRAM visit test-and-set: 2048 lines, repeated visits, adjacent fields and balanced mapper windows')

 # Actual sprite clipping code: compare visible clips and masked-wall draw order.
 sprite_libs={}
 for mode in ('control','clip'):
  s=(dirs[mode]/'src/r_draw.c').read_text()
  code=r"""#include <stdint.h>
#include <stddef.h>
#include <string.h>
#define DOOM_R57_CROP16 1
#define VIEWWINDOWWIDTH 76
#define VIEWWINDOWHEIGHT 44
#define FRACBITS 16
#define SIL_BOTTOM 1
#define SIL_TOP 2
#define R57_CROP_ACTIVE 1
#define R57_XMIN crop_lo
#define R57_XEND crop_hi
typedef int32_t fixed_t;
typedef struct{int16_t x1,x2;int32_t scale,gx,gy,gz;int16_t patch_topoffset;}vissprite_t;
typedef struct{int16_t x1,x2;int32_t scale1,scale2;unsigned silhouette;int maskedtexturecol;int curline;int32_t bsilheight,tsilheight;int16_t sprbottomclip[76],sprtopclip[76];}drawseg_t;
static drawseg_t _s_drawsegs[64],*ds_p;
static int16_t floorclip[76],ceilingclip[76],*mfloorclip,*mceilingclip;
static int crop_lo,crop_hi;static uint32_t order_hash;static int16_t *result;
static int R_PointOnSegSide(int32_t x,int32_t y,int line){return (x^y^line)&1;}
static void R_RenderMaskedSegRange(const drawseg_t*d,int l,int r){for(int x=l;x<=r;x++)if(x>=crop_lo && x<crop_hi)order_hash=order_hash*31u+(unsigned)(d-_s_drawsegs)*76u+x;}
static void R_DrawVisSprite(const vissprite_t*s){for(int x=s->x1;x<=s->x2;x++)if(x>=crop_lo && x<crop_hi){result[x*2]=floorclip[x];result[x*2+1]=ceilingclip[x];}}
static uint32_t rng;
static unsigned next(void){rng=rng*1664525u+1013904223u;return rng>>8;}
"""+fn(s,'static void R_DrawSprite (')+r"""
uint32_t check(uint32_t seed,int lo,int hi,int16_t*out){rng=seed;crop_lo=lo;crop_hi=hi;result=out;memset(out,0,304);order_hash=0;
 vissprite_t spr={0};spr.x1=next()%76;spr.x2=spr.x1+next()%(76-spr.x1);spr.scale=next()%100;spr.gx=next();spr.gy=next();spr.gz=(int32_t)(next()%128)*65536;spr.patch_topoffset=next()%64;
 unsigned n=next()%65;ds_p=_s_drawsegs+n;
 for(unsigned i=0;i<n;i++){drawseg_t*d=_s_drawsegs+i;d->x1=next()%76;d->x2=d->x1+next()%(76-d->x1);d->scale1=next()%100;d->scale2=next()%100;d->silhouette=next()%4;d->maskedtexturecol=next()%2;d->curline=next();d->bsilheight=(int32_t)(next()%192)*65536;d->tsilheight=(int32_t)(next()%192)*65536;
 for(int x=0;x<76;x++){d->sprbottomclip[x]=next()%45;d->sprtopclip[x]=(int)(next()%45)-1;}}
 R_DrawSprite(&spr);return order_hash;}
"""
  c=t/('sprite-'+mode+'.c');so=c.with_suffix('.so');c.write_text(code)
  run(['cc','-shared','-fPIC','-O2',str(c),'-o',str(so)]);sprite_libs[mode]=ctypes.CDLL(str(so));sprite_libs[mode].check.restype=ctypes.c_uint32
 aa=(ctypes.c_int16*152)();bb=(ctypes.c_int16*152)()
 for i in range(5000):
  lo,hi=((0,76),(2,74),(6,72),(10,68),(14,64))[i%5]
  x=sprite_libs['control'].check(i,lo,hi,aa);y=sprite_libs['clip'].check(i,lo,hi,bb)
  assert x==y and bytes(aa)==bytes(bb),(i,'sprite clipping/masked draw order')
 print('PASS 5000 actual C sprite clipping scenes, 0..64 drawsegs: visible clips and masked-wall ordering identical')
 # Coordinate equivalence for all horizontal crop pairs and source row addresses.
 for crop in (False,True):
  for lo,hi in ((0,76),(2,74),(6,72),(10,68),(14,64)):
   for x1 in range(76):
    for x2 in range(x1,76):
     left=max(x1,lo) if crop else x1;right=min(x2,hi-1) if crop else x2
     assert set(range(left,right+1))==set(range(x1,x2+1)).intersection(range(lo,hi) if crop else range(76))
 for fb in (0xff0000,0xff1000,0xffe000):
  for first,end in ((1,22),(3,20),(5,18)):
   for xmin in range(0,8):
    a=fb+152+(first-1)*152+xmin*2;b=a+76
    for y in range(first,end):
     word=(a>>1)+(y-first)*76
     assert word==((a+(y-first)*152)>>1)
     assert word+38==((b+(y-first)*152)>>1)
     assert (word>>16)==((word+38)>>16)==(a>>17)
 print('PASS crop intersections and Pair-V DMA source stepping; quick colors and AI invariance for all 9 variants')
