#!/usr/bin/env python3
import pathlib,random,re
out=pathlib.Path('dist/r20e/evidence');out.mkdir(parents=True,exist_ok=True)
r=random.Random(20261017)
ds={1,2,65535,65536,65537,0xfffffff,0x80000000,0xffffffff}
for k in range(32):
 for off in (-2,-1,0,1,2):
  d=((1<<k)+off)&0xffffffff
  if d: ds.add(d)
ds.update(r.randrange(1,0x100000000) for _ in range(4096))
products=[(r.randrange(-32768,32768),r.randrange(-65536,65536)) for _ in range(4096)]
products += [(a,b) for a in (-32768,-1,0,1,32767) for b in (-65536,-32768,-1,0,32768,65535)]
s='#include <stdint.h>\n#include "r20_scale_math.h"\n'
s+='static const uint32_t quot[][2]={\n'+','.join('{0x%xu,0x%xu}'%(d,0xffffffff//d) for d in sorted(ds))+'};\n'
s+='struct product {int16_t a;int32_t b;uint32_t result;};\nstatic const struct product prod[]={\n'+','.join('{%d,%d,0x%xu}'%(a,b,(a*b)&0xffffffff) for a,b in products)+'};\n'
# Extract the production flat writer, including its actual inline assembly.
video=pathlib.Path('src/i_genesisv.c').read_text()
a=video.index('R20_COLFN void R_DrawColumnFlat');brace=video.index('{',a);depth=0
for end in range(brace,len(video)):
 if video[end]=='{': depth+=1
 elif video[end]=='}':
  depth-=1
  if not depth: break
writer=video[a:end+1]
rowtable=re.search(r'static const uint16_t r20_rowofs\[28\] = \{.*?\};',video,re.S).group()
s+="""
#define VIEWWINDOWWIDTH 38
#define DOOM_R20_FLAT_UNROLL 1
#define DOOM_R19_FLAT_DBRA 1
#define R20_COLFN
#define R20_COUNT(i,n) ((void)0)
static uint16_t _s_screen[38*28],colorcell[256];
typedef struct {int16_t x,yl,yh;uint16_t fracstep;int32_t texturemid;
 const uint8_t *source,*colormap;} draw_column_vars_t;
"""+rowtable+'\n'+writer+'\n'
s+="""
static unsigned flat_probe(void) {
 unsigned errors=0;uint32_t rng=20261017u;
 for(unsigned i=0;i<256;i++)colorcell[i]=(uint16_t)(i*131u);
 for(unsigned test=0;test<512;test++) {
   rng=rng*1664525u+1013904223u;
   int16_t yl=(test<28)?0:(int16_t)(rng%28);
   int16_t count=(test<28)?(int16_t)(test+1):(int16_t)((rng>>8)%(29-yl));
   int16_t x=(int16_t)((rng>>16)%38); uint8_t color=(uint8_t)test;
   draw_column_vars_t d={x,yl,(int16_t)(yl+count-1),0,0,0,0};
   for(unsigned i=0;i<38*28;i++)_s_screen[i]=0xdead;
   R_DrawColumnFlat(color,&d);
   for(unsigned y=0;y<28;y++)for(unsigned xx=0;xx<38;xx++) {
     uint16_t want=(xx==(unsigned)x && y>=(unsigned)yl && y<(unsigned)(yl+count))?colorcell[color]:0xdead;
     if(_s_screen[y*38+xx]!=want) {++errors;goto next;}
   }
next: ;
 }
 return errors;
}
"""
s+="""
int main(void) {
 unsigned errors=0;
 *(volatile uint16_t*)0xA00000=0;
 errors+=flat_probe();
 for(unsigned i=0;i<sizeof(quot)/sizeof(*quot);i++)
   if(R20_ScaleReciprocal(quot[i][0])!=quot[i][1]) ++errors;
 for(unsigned i=0;i<sizeof(prod)/sizeof(*prod);i++)
   if((uint32_t)R20_ScaleProduct(prod[i].a,prod[i].b)!=prod[i].result) ++errors;
 *(volatile uint16_t*)0xA00002=(uint16_t)errors;
 *(volatile uint16_t*)0xA00004=0;
 for(;;){}
}
"""
(out/'math-probe.c').write_text(s)
(out/'math-boot.s').write_text('.section .text.boot,"ax"\n.long 0x00fffe00,entry\n.org 0x400\n .globl entry\nentry:\n jsr main\n bra entry\n')
(out/'math-probe.ld').write_text('ENTRY(entry)\nSECTIONS { . = 0; .text : { KEEP(*(.text.boot)) *(.text*) *(.rodata*) } . = 0xff0000; .bss : { *(.bss*) *(COMMON) } /DISCARD/ : { *(.comment*) *(.eh_frame*) } }\n')
print(f'Probe vectors: {len(ds)} reciprocal and {len(products)} product cases')
