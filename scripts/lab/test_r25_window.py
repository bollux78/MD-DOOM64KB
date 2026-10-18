#!/usr/bin/env python3
"""Exercise production mapper windows, compact nodes, block heads and cache copies."""
from pathlib import Path
import tempfile,subprocess
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
    p=Path(td)
    (p/'compiler.h').write_text('')
    (p/'i_system.h').write_text('void I_Error(const char*,...);')
    (p/'globdata.h').write_text('typedef struct mobj_s {struct mobj_s *bnext;} mobj_t;')
    (p/'r_defs.h').write_text('''#include <stdint.h>
#include "r23_mapmem.h"
#pragma pack(push,2)
typedef struct {uint16_t validcount,r_validcount;int16_t r_flags,special;} linedata_t;
typedef struct {uint32_t sector;int16_t textureoffset;int8_t toptexture,bottomtexture,midtexture;} side_t;
typedef struct {uint32_t id;} sector_t;
extern sector_t *_g_sectors;
typedef struct {uint32_t m_sector,m_thing,m_tprev,m_tnext,m_sprev,m_snext;int16_t visited;} msecnode_t;
#pragma pack(pop)
''')
    for name in ['r23_mapmem.h','r22_blocklinks.h']:(p/name).write_bytes((ROOT/'src'/name).read_bytes())
    (p/'mock.h').write_text('''#include <stdint.h>
#include <assert.h>
extern int bank;extern uint8_t bytes[65536];
static inline uint8_t *access_byte(uint32_t a){assert(bank==1 && (a&1) && a>=0x200000 && a<0x210000);return bytes+a-0x200000;}
#define R22_SRAM_BYTE(a) (*access_byte(a))
#define R22_SRAM_ENABLE() (bank=1)
#define R22_SRAM_DISABLE() (bank=0)
''')
    for f in ['r22_blocklinks.c','r23_mapmem.c']:(p/f).write_bytes((ROOT/'src'/f).read_bytes())
    draw=(ROOT/'src/r_draw.c').read_text()
    cache=draw.split('#else\nstatic void SramCacheCopyTo(uint16_t slot, const byte* src, uint16_t size)')[1].split('\n#endif\n\n#if defined(DOOM_SRAM_HOT_SLOTS)')[0]
    cache='static void SramCacheCopyTo(uint16_t slot, const byte* src, uint16_t size)'+cache
    cache=cache.replace('(volatile uint8_t*)(DOOM_SRAM_FIRST + ((uint32_t)slot << 8))','(bytes+0xF001+((uint32_t)slot<<8))').replace('(volatile const uint8_t*)(DOOM_SRAM_FIRST + ((uint32_t)slot << 8))','(bytes+0xF001+((uint32_t)slot<<8))')
    (p/'test.c').write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r_defs.h"
#include "r22_blocklinks.h"
typedef uint8_t byte;
uint8_t bytes[65536];int bank;
static sector_t sectors[250];sector_t *_g_sectors=sectors;
void I_Error(const char *s,...){fprintf(stderr,"%s\\n",s);exit(2);}
'''+cache+'''
int main(void){
 memset(bytes,0xC3,sizeof bytes);R22_BlockInit(52,56);assert(!bank);
 for(unsigned i=0;i<2912;i++){assert(!R22_BlockHead(i));assert(!bank);}
 R23_MapMemoryInit(1352,805,1748);assert(!bank);
 linedata_t *line=(void*)0x210000;R23_SET(line,special,127);assert(!bank);assert(R23_GET(line,special)==127 && !bank);
 side_t *side=(void*)0x220000;R23_SET(side,sector,0xE0FF1234);assert(!bank);assert(R23_GET(side,sector)==0xE0FF1234 && !bank);
 for(unsigned i=0;i<405;i++){
  msecnode_t *node=R23_NodeAlloc();assert(!bank);
  R23_SET(node,m_sector,(uint32_t)(uintptr_t)&sectors[i%250]);assert(!bank);
  R23_SET(node,m_thing,0xE0FF1000u+i*114);assert(!bank);
  R23_SET(node,m_tprev,i?0x230000u+(i-1)*sizeof(msecnode_t):0);assert(!bank);
  R23_SET(node,visited,i&1);assert(!bank);
  assert(R23_GET(node,m_sector)==(uint32_t)(uintptr_t)&sectors[i%250] && !bank);
  assert(R23_GET(node,m_thing)==0xE0FF1000u+i*114 && !bank);
  assert(R23_GET(node,m_tprev)==(i?0x230000u+(i-1)*sizeof(msecnode_t):0) && !bank);
  assert(R23_GET(node,visited)==(int)(i&1) && !bank);
 }
 for(unsigned i=0;i<405;i++)R23_NodeFree((void*)(uintptr_t)(0x230000+i*sizeof(msecnode_t)));
 for(int i=404;i>=0;i--){assert((uintptr_t)R23_NodeAlloc()==0x230000+i*sizeof(msecnode_t));assert(!bank);}
 byte in[128],out[128];
 for(unsigned slot=0;slot<16;slot++){
  for(unsigned i=0;i<128;i++)in[i]=i^slot;
  SramCacheCopyTo(slot,in,128);assert(!bank);memset(out,0,128);
  SramCacheCopyFrom(slot,out,128);assert(!bank);assert(!memcmp(in,out,128));
 }
 for(unsigned i=0;i<65536;i+=2)assert(bytes[i]==0xC3);
 puts("PASS SRAM windows: block heads, map fields, 405 compact nodes/freelist, 16 cache columns; mapper restored, even lanes untouched");
 return 0;
}
''')
    subprocess.run(['cc','-O2','-no-pie','-I'+str(p),'-include',str(p/'mock.h'),'-DDOOM_R25_MUSIC','-DDOOM_R24_EPISODE','-DDOOM_R23_MAPMEM','-DDOOM_R22_SRAM_BLOCKLINKS','-Wno-pointer-to-int-cast','-Wno-int-to-pointer-cast',str(p/'r22_blocklinks.c'),str(p/'r23_mapmem.c'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
