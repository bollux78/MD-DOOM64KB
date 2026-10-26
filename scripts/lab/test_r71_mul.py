#!/usr/bin/env python3
"""R71-MUL: verify the REAL extracted tangent helper on host against a 68000 MULS.W model.
On the native host the guarded asm is disabled; the linked 68000 ROM is separately checked
by objdump and by full DEMO3 pixel captures. This test is an arithmetic oracle, not 68000 execution.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'src/r_draw.c').read_text()
sig="static inline int16_t R20_TanMulU16(int16_t a, uint16_t b)"
begin=s.index(sig)
br=s.index("{",begin)
depth=0
for i in range(br,len(s)):
    if s[i]=="{":depth+=1
    elif s[i]=="}":
        depth-=1
        if not depth:break
fn=s[begin:i+1]
assert fn.count('muls.w %1,%0')==1 and fn.count('__m68k__')==1
assert 'int16_t hi' in fn and 'hi += a' in fn
c=r"""
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
/* Real source body is spliced here, including its opt-in 68k asm. */
""" + fn + r"""
/* Reference for the exact 68000 signed MULS.W result and high-half correction. */
static int16_t model(int16_t a,uint16_t b) {
    int32_t p=(int32_t)a*(int32_t)(int16_t)b;
    int16_t hi=(int16_t)(p>>16);
    if(b & 0x8000u)hi+=a;
    return hi;
}
static uint32_t seed=0x7116a812u;
static uint32_t next(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
    uint32_t tested=0;
    const int16_t av[]={-32768,-32767,-30000,-16384,-257,-256,-255,-2,-1,0,1,2,255,256,257,16384,30000,32766,32767};
    const uint16_t bv[]={0,1,2,3,127,255,256,257,1023,1024,16383,16384,32767,32768,32769,49152,65533,65534,65535};
    for(unsigned ai=0;ai<sizeof av/sizeof *av;ai++)
      for(unsigned bi=0;bi<sizeof bv/sizeof *bv;bi++){
        int16_t got=R20_TanMulU16(av[ai],bv[bi]),want=model(av[ai],bv[bi]);
        if(got!=want){fprintf(stderr,"EDGE FAIL a=%d b=%u got=%d want=%d\n",av[ai],bv[bi],got,want);return 1;}
        tested++;
      }
    /* For each possible a, test all important tangent magnitudes and signs. */
    for(int32_t a=-32768;a<=32767;a++) {
      uint16_t bset[]={0,1,127,255,256,32767,32768,32769,49152,65535};
      for(unsigned bi=0;bi<sizeof bset/sizeof *bset;bi++){
        uint16_t b=bset[bi];
        if(R20_TanMulU16((int16_t)a,b)!=model((int16_t)a,b))return 2;
        tested++;
      }
    }
    for(uint32_t k=0;k<2000000;k++){
      int16_t a=(int16_t)next();uint16_t b=(uint16_t)next();
      int16_t got=R20_TanMulU16(a,b),want=model(a,b);
      if(got!=want){fprintf(stderr,"RNG FAIL k=%u a=%d b=%u got=%d want=%d\n",k,a,b,got,want);return 3;}
      tested++;
    }
    printf("PASS R71-MUL: %u cases (signed extremes, all 65536 distances, full u16 highbit, random) model exact\\n",tested);
}
"""
for label,flags in [("baseline",[]),("flag-on-host",["-DDOOM_R71_MUL_ASM=1"])]:
    with tempfile.TemporaryDirectory(prefix="mul71-") as d:
        p=Path(d)/"test.c";p.write_text(c)
        exe=Path(d)/"test"
        subprocess.run(["cc","-std=gnu11","-O2","-Wall","-Wextra","-fsanitize=undefined",
                        "-fno-sanitize-recover=all",*flags,str(p),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        print("PASS "+label,flush=True)
