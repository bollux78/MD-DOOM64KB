#!/usr/bin/env python3
"""Exercise production SRAM map byte I/O with the 68000 structure sizes."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 (p/'compiler.h').write_text('')
 (p/'i_system.h').write_text('void I_Error(const char*,...);\n')
 (p/'r_defs.h').write_text('#include <stdint.h>\n#include "r23_mapmem.h"\n#pragma pack(push,2)\ntypedef struct {uint16_t validcount,r_validcount;int16_t r_flags,special;} linedata_t;\ntypedef struct {uint32_t sector;int16_t textureoffset;int8_t toptexture,bottomtexture,midtexture;} side_t;\ntypedef struct {uint32_t m_sector,m_thing,m_tprev,m_tnext,m_sprev,m_snext;int16_t visited;} msecnode_t;\n#pragma pack(pop)\n')
 (p/'r23_mapmem.h').write_bytes((root/'src/r23_mapmem.h').read_bytes())
 (p/'r22_blocklinks.h').write_text('#include <stdint.h>\n#define R22_SRAM_BASE 0x200000UL\nextern uint8_t bytes[65536];\n#define R22_SRAM_BYTE(a) bytes[((a)-R22_SRAM_BASE)&65535]\n#define R22_SRAM_ENABLE() ((void)0)\n')
 (p/'prod.c').write_bytes((root/'src/r23_mapmem.c').read_bytes())
 (p/'test.c').write_text('''#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "r_defs.h"
uint8_t bytes[65536];
void I_Error(const char *s,...){fprintf(stderr,"%s\\n",s);exit(2);}
int main(void){
 assert(sizeof(side_t)==10 && sizeof(linedata_t)==8);
 memset(bytes,0xC3,sizeof bytes);R23_MapMemoryInit(1033,691,1302);
 for(unsigned i=0;i<5208*2;i++)assert(bytes[i]==0xC3);
 for(unsigned i=0;i<1033;i++){
  linedata_t *l=(void*)(uintptr_t)(0x210000+i*8);
  R23_SET(l,validcount,i*31);R23_SET(l,r_validcount,i*19);R23_SET(l,r_flags,256|(i&31));R23_SET(l,special,-(int)i);
 }
 for(unsigned i=0;i<691;i++){
  side_t *s=(void*)(uintptr_t)(0x220000+i*10);
  R23_SET(s,sector,0xE0FF1000u+i*56);R23_SET(s,textureoffset,-(int)i*11);
  R23_SET(s,toptexture,i%125);R23_SET(s,bottomtexture,-1);R23_SET(s,midtexture,124-i%125);
 }
 for(unsigned i=0;i<1033;i++){
  linedata_t *l=(void*)(uintptr_t)(0x210000+i*8);
  assert(R23_GET(l,validcount)==(uint16_t)(i*31));assert(R23_GET(l,r_validcount)==(uint16_t)(i*19));assert(R23_GET(l,r_flags)==(int)(256|(i&31)));assert(R23_GET(l,special)==-(int)i);
 }
 for(unsigned i=0;i<691;i++){
  side_t *s=(void*)(uintptr_t)(0x220000+i*10);
  assert(R23_GET(s,sector)==0xE0FF1000u+i*56);assert(R23_GET(s,textureoffset)==-(int)i*11);
  assert(R23_GET(s,toptexture)==(int)(i%125));assert(R23_GET(s,bottomtexture)==-1);assert(R23_GET(s,midtexture)==(int)(124-i%125));
 }
 for(unsigned i=0;i<65536;i+=2)assert(bytes[i]==0xC3);
 puts("PASS production SRAM fields: all 1033 lines/691 sides, signed values, pointer bits, boundaries, even-lane preservation");return 0;
}
''')
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-int-to-pointer-cast','-Wno-pointer-to-int-cast','-fsanitize=undefined','-DDOOM_R23_MAPMEM','-DDOOM_R22_SRAM_BLOCKLINKS',str(p/'prod.c'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
