#!/usr/bin/env python3
"""Compile the real compact map-memory implementation against odd-lane SRAM."""
from pathlib import Path
import tempfile,subprocess,shutil
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'src').mkdir()
 for name in ('r23_mapmem.c','r_defs.h','doomdata.h','r81_save.h'):
  shutil.copyfile(ROOT/'src'/name,p/'src'/name)
 subprocess.run(['python3',str(ROOT/'scripts/lab/apply_r81_sram.py')],cwd=p,check=True)
 d=p/'src'
 (d/'compiler.h').write_text('#include <stdint.h>\n#include <stddef.h>\n')
 (d/'r_defs.h').write_text('''#include <stdint.h>
#include <stddef.h>
uint32_t R23_MapRead(const void*,uint16_t,uint16_t);
void R23_MapWrite(void*,uint16_t,uint16_t,uint32_t);
#define R23_GET(p,f) R23_MapRead((p),offsetof(__typeof__(*(p)),f),sizeof((p)->f))
#define R23_SET(p,f,v) R23_MapWrite((p),offsetof(__typeof__(*(p)),f),sizeof((p)->f),(uint32_t)(uintptr_t)(v))
typedef struct {uint16_t validcount,r_validcount;uint8_t r_flags;int8_t special;} linedata_t;
typedef struct {uint32_t sector;int16_t textureoffset;int8_t toptexture,bottomtexture,midtexture;uint8_t pad[6];} __attribute__((packed,aligned(2))) side_t;
typedef struct {int data[10];} sector_t;
static sector_t *_g_sectors=(sector_t*)(uintptr_t)0xE0FF6000UL;
typedef struct {uint32_t m_sector,m_thing,m_tprev,m_tnext,m_sprev,m_snext;uint8_t visited;} msecnode_t;
''')
 (d/'r22_blocklinks.h').write_text('''#define R22_SRAM_BASE 0x200000UL
static uint8_t ram[65536];
#define R22_SRAM_BYTE(a) ram[(a)-R22_SRAM_BASE]
#define R22_SRAM_ENABLE() ((void)0)
''')
 (d/'r39c_movep.h').write_text('''static uint16_t R39C_MovepRead16(uint32_t a){return ((uint16_t)R22_SRAM_BYTE(a)<<8)|R22_SRAM_BYTE(a+2);}
static uint32_t R39C_MovepRead32(uint32_t a){return ((uint32_t)R39C_MovepRead16(a)<<16)|R39C_MovepRead16(a+4);}
static void R39C_MovepWrite16(uint32_t a,uint16_t v){R22_SRAM_BYTE(a)=v>>8;R22_SRAM_BYTE(a+2)=v;}
static void R39C_MovepWrite32(uint32_t a,uint32_t v){R39C_MovepWrite16(a,v>>16);R39C_MovepWrite16(a+4,v);}
''')
 (d/'i_system.h').write_text('#include <stdlib.h>\nstatic void I_Error(const char *s){puts(s);abort();}\n')
 (d/'test.c').write_text('''#include <stdio.h>
#include <string.h>
#include <assert.h>
#define DOOM_R81_SAVE 1
#define DOOM_R23_MAPMEM 1
#define DOOM_R24_EPISODE 1
#define DOOM_R39C_MOVEP_MAP 1
#define DOOM_R22_SRAM_BLOCKLINKS 1
#define DOOM_R27_GROUP_SIDE 1
#define DOOM_R27_GROUP_LINE 1
#include "r23_mapmem.c"
int main(void){
 assert(sizeof(linedata_t)==6&&sizeof(side_t)==16);
 memset(ram,0xA5,sizeof(ram));R23_MapMemoryInit(1352,805,1748);
 assert(node_base==21544 && node_capacity==423);
 for(unsigned i=0;i<1352;i++){
  void *l=(void*)(uintptr_t)(0x210000+i*6);
  R23_MapWrite(l,0,2,i);R23_MapWrite(l,2,2,65535-i);
  R23_MapWrite(l,4,1,128|16);R23_MapWrite(l,5,1,(uint8_t)-23);
  assert(R23_MapRead(l,0,2)==i && R23_MapRead(l,4,1)==144);
  assert(R23_MapRead(l,2,4)==((65535u-i)<<16|144));
  R23_MapWrite(l,2,4,0xABCD0008);assert(R23_MapRead(l,2,4)==0xABCD0008);
  assert((int8_t)R23_MapRead(l,5,1)==-23);
  assert(R27_OrFlags(l,128)==136 && (int8_t)R23_MapRead(l,5,1)==-23);
 }
 for(unsigned i=0;i<805;i++){
  void *s=(void*)(uintptr_t)(0x220000+i*16);
  R23_MapWrite(s,0,4,0xE0FF6000+(i%250)*sizeof(sector_t));
  assert(R23_MapRead(s,0,4)==0xE0FF6000+(i%250)*sizeof(sector_t));
  R23_MapWrite(s,4,2,0xFF00+i);R23_MapWrite(s,6,1,0xA1);R23_MapWrite(s,7,1,0xB2);R23_MapWrite(s,8,1,0xC3);
  uint8_t bytes[5];R27_ReadBlock(s,4,5,bytes);
  assert(bytes[0]==((0xFF00+i)>>8&255)&&bytes[1]==(i&255)&&bytes[2]==0xA1&&bytes[3]==0xB2&&bytes[4]==0xC3);
 }
 for(unsigned i=0;i<node_capacity;i++){
  void *n=R23_NodeAlloc();R23_MapWrite(n,offsetof(msecnode_t,m_sector),4,0xE0FF6000+sizeof(sector_t)*17);
  R23_MapWrite(n,offsetof(msecnode_t,m_thing),4,0xE0FF2222);R23_MapWrite(n,offsetof(msecnode_t,visited),1,1);
  assert(R23_MapRead(n,offsetof(msecnode_t,m_sector),4)==0xE0FF6000+sizeof(sector_t)*17);
  assert(R23_MapRead(n,offsetof(msecnode_t,m_thing),4)==0xE0FF2222);
 }
 for(unsigned i=26624;i<32768;i++)assert(ram[1+2*i]==0xA5);
 R81_ResetMapLinks();assert(!node_used&&!node_free);
 for(unsigned i=26624;i<32768;i++)assert(ram[1+2*i]==0xA5);
 puts("PASS real SRAM code: 1352 lines, 805 sides, grouped reads/writes, 423 nodes, save region preserved");
}
''')
 subprocess.run(['gcc','-std=c99','-O2','-Wall','-Wextra','-Werror','-Wno-int-to-pointer-cast',str(d/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
