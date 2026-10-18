#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess
r=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'compiler.h').write_text('');(p/'i_system.h').write_text('void I_Error(const char*,...);');(p/'r23_mapmem.h').write_bytes((r/'src/r23_mapmem.h').read_bytes());(p/'prod.c').write_bytes((r/'src/r23_mapmem.c').read_bytes())
 (p/'r_defs.h').write_text('''#include <stdint.h>
#include "r23_mapmem.h"
#pragma pack(push,2)
typedef struct {uint16_t validcount,r_validcount;int16_t r_flags,special;} linedata_t;
typedef struct {uint32_t sector;int16_t textureoffset;int8_t toptexture,bottomtexture,midtexture;} side_t;
typedef struct {uint32_t id;} sector_t;
extern sector_t *_g_sectors;
typedef struct {uint32_t m_sector,m_thing,m_tprev,m_tnext,m_sprev,m_snext;int16_t visited;} msecnode_t;
#pragma pack(pop)
''');(p/'r22_blocklinks.h').write_text('''#include <stdint.h>
#define R22_SRAM_BASE 0x200000UL
extern uint8_t bytes[65536];
#define R22_SRAM_BYTE(a) bytes[((a)-R22_SRAM_BASE)&65535]
#define R22_SRAM_ENABLE() ((void)0)
''');(p/'test.c').write_text('''#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r_defs.h"
uint8_t bytes[65536];static sector_t sectors[250];sector_t *_g_sectors=sectors;
void I_Error(const char *s,...){fprintf(stderr,"%s\\n",s);exit(2);}
int main(void){
 assert(sizeof(msecnode_t)==26);memset(bytes,0xC3,sizeof bytes);R23_MapMemoryInit(1352,805,1748);
 for(unsigned i=0;i<405;i++){
  msecnode_t *p=R23_NodeAlloc();assert((uintptr_t)p==0x230000+i*26);
  R23_SET(p,m_sector,(uint32_t)(uintptr_t)&sectors[i%250]);R23_SET(p,m_thing,0xE0FF5000u+(i%217)*114);
  R23_SET(p,m_tprev,i?0x230000u+(i-1)*26:0);R23_SET(p,m_tnext,i<404?0x230000u+(i+1)*26:0);
  R23_SET(p,m_sprev,0);R23_SET(p,m_snext,0x230000);R23_SET(p,visited,i&1);
 }
 for(unsigned i=0;i<405;i++){
  msecnode_t *p=(void*)(uintptr_t)(0x230000+i*26);
  assert(R23_GET(p,m_sector)==(uint32_t)(uintptr_t)&sectors[i%250]);assert(R23_GET(p,m_thing)==0xE0FF5000u+(i%217)*114);
  assert(R23_GET(p,m_tprev)==(i?0x230000u+(i-1)*26:0));assert(R23_GET(p,m_tnext)==(i<404?0x230000u+(i+1)*26:0));
  assert(!R23_GET(p,m_sprev));assert(R23_GET(p,m_snext)==0x230000);assert(R23_GET(p,visited)==(int)(i&1));
 }
 for(unsigned i=1;i<405;i+=2)R23_NodeFree((void*)(uintptr_t)(0x230000+i*26));
 for(int i=403;i>0;i-=2)assert((uintptr_t)R23_NodeAlloc()==0x230000u+i*26);
 for(unsigned i=0;i<65536;i+=2)assert(bytes[i]==0xC3);
 for(unsigned i=0;i<25858*2;i++)assert(bytes[i]==0xC3);
 for(unsigned i=30720*2;i<65536;i++)assert(bytes[i]==0xC3);
 puts("PASS 405 E1M6 compact SRAM nodes: fields, pointers, NULL, freelist reuse, adjacent map/cache and even lanes preserved");return 0;
}
''');subprocess.run(['cc','-O2','-no-pie','-fsanitize=undefined','-fno-sanitize-recover=undefined','-Wno-pointer-to-int-cast','-Wno-int-to-pointer-cast','-DDOOM_R23_MAPMEM','-DDOOM_R22_SRAM_BLOCKLINKS','-DDOOM_R24_EPISODE',str(p/'prod.c'),str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
