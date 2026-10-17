#!/usr/bin/env python3
from pathlib import Path
import os,subprocess
r=Path(__file__).resolve().parents[2];e=r/'dist/r22/evidence';e.mkdir(parents=True,exist_ok=True)
# Reuse the existing CPU-harness boot/link contract; not a MegaDrive game.
old=r/'scripts/lab/gen_r20g_probe.py'
# The established generator produces boot and linker files without invoking GCC.
subprocess.run(['python3',str(old)],check=True)
for n in ['probe-boot.s','probe.ld']:(e/n).write_bytes((r/'dist/r20g/evidence'/n).read_bytes())
code=r'''
#include <stdint.h>
#include "r22_pixel4.h"
static struct {uint32_t a;uint8_t fb[R22_FB_BYTES];uint32_t b;} mem;
int main(void){
 uint32_t errors=0;*(volatile uint16_t*)0xA00000=0;
 for(uint16_t p=0;p<256;p++){
  uint32_t q=R22_ExpandPair((uint8_t)p);
  for(uint16_t x=0;x<8;x++)if(((q>>(28-4*x))&15)!=(uint32_t)(x<4?p>>4:p&15))errors++;
 }
 mem.a=mem.b=0x2244AA55;
 for(uint16_t y=0;y<R22_H;y++)for(uint16_t x=0;x<R22_W;x++)R22_Put(mem.fb,x,y,(uint8_t)((x+3*y)&15));
 for(uint16_t y=0;y<R22_H;y++)for(uint16_t x=0;x<R22_W;x++){
  uint8_t p=mem.fb[y*R22_PITCH+(x>>1)];p=(x&1)?p&15:p>>4;
  if(p!=((x+3*y)&15))errors++;
 }
 if(mem.a!=0x2244AA55 || mem.b!=0x2244AA55)errors++;
 *(volatile uint16_t*)0xA00002=errors?1:0;*(volatile uint16_t*)0xA00004=0;
 return 0;
}
'''
(e/'pixel4-probe.c').write_text(code)
g=Path(os.path.expanduser(os.environ.get('DOOM_MD_GDK','~/mars/m68k-elf')));gcc=g/'bin/m68k-elf-gcc';libgcc=subprocess.check_output([str(gcc),'-m68000','-print-libgcc-file-name'],text=True).strip()
subprocess.run([str(gcc),'-m68000','-O3','-ffreestanding','-fno-builtin','-nostdlib','-Isrc',str(e/'probe-boot.s'),str(e/'pixel4-probe.c'),libgcc,'-Wl,-T,'+str(e/'probe.ld'),'-o',str(e/'pixel4-probe.elf')],cwd=r,check=True)
subprocess.run([str(g/'bin/m68k-elf-objcopy'),'-O','binary','-j','.text',str(e/'pixel4-probe.elf'),str(e/'pixel4-probe.raw')],check=True)
for n in ['memory_base.h','dma.h','vdp.h','config.h']:
 p=g/'inc'/n
 if p.exists():(e/('sgdk-'+n+'.txt')).write_bytes(p.read_bytes())
print('READY MC68000 packed4x4 primitive probe, runtime emulation required')
