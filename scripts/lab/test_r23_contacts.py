#!/usr/bin/env python3
"""Validate production sector-contact insert/delete against both linked threads."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
def fn(s,name):
 a=s.rfind('\n',0,s.index(name))+1;b=s.index('{',a);d=0
 for i in range(b,len(s)):
  if s[i]=='{':d+=1
  if s[i]=='}':
   d-=1
   if not d:return s[a:i+1]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'compiler.h').write_text('');(p/'i_system.h').write_text('void I_Error(const char*,...);');(p/'r23_mapmem.h').write_bytes((r/'src/r23_mapmem.h').read_bytes())
 (p/'r_defs.h').write_text('''#include <stdint.h>
#include "r23_mapmem.h"
#define __far
#define false 0
#pragma pack(push,2)
typedef struct {uint16_t validcount,r_validcount;int16_t r_flags,special;} linedata_t;
typedef struct {uint32_t sector;int16_t textureoffset;int8_t toptexture,bottomtexture,midtexture;} side_t;
typedef struct msecnode_s msecnode_t;
typedef struct {msecnode_t *touching_thinglist;} sector_t;
typedef struct {int id;} mobj_t;
struct msecnode_s {sector_t *m_sector;mobj_t *m_thing;msecnode_t *m_tprev,*m_tnext,*m_sprev,*m_snext;int16_t visited;};
#pragma pack(pop)
''');(p/'r22_blocklinks.h').write_text('''#include <stdint.h>
#define R22_SRAM_BASE 0x200000UL
extern uint8_t bytes[65536];
#define R22_SRAM_BYTE(a) bytes[((a)-R22_SRAM_BASE)&65535]
#define R22_SRAM_ENABLE() ((void)0)
''');(p/'prod.c').write_bytes((r/'src/r23_mapmem.c').read_bytes());src=(r/'src/p_map.c').read_text()
 code='''#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r_defs.h"
uint8_t bytes[65536];
static sector_t sectors[5];static mobj_t things[30];static msecnode_t *heads[30],*_s_sector_list;
void I_Error(const char*s,...){fprintf(stderr,"%s\\n",s);exit(2);}
static msecnode_t *P_GetSecnode(void){return R23_NodeAlloc();}
static void P_PutSecnode(msecnode_t *p){R23_NodeFree(p);}
'''+fn(src,'static void P_AddSecnode(')+'\n'+fn(src,'static msecnode_t __far* P_DelSecnode(')+'''
static void check(void){
 int seen[30][5]={{0}};
 for(int t=0;t<30;t++){
  msecnode_t *prev=NULL;int guard=0;
  for(msecnode_t *n=heads[t];n;n=R23_GET(n,m_tnext)){
   assert(++guard<=5);assert(R23_GET(n,m_tprev)==prev);assert(R23_GET(n,m_thing)==&things[t]);
   int s=R23_GET(n,m_sector)-sectors;assert(s>=0&&s<5);assert(!seen[t][s]++);prev=n;
  }
 }
 for(int s=0;s<5;s++){
  msecnode_t *prev=NULL;int guard=0;
  for(msecnode_t *n=sectors[s].touching_thinglist;n;n=R23_GET(n,m_snext)){
   assert(++guard<=30);assert(R23_GET(n,m_sprev)==prev);assert(R23_GET(n,m_sector)==&sectors[s]);
   int t=R23_GET(n,m_thing)-things;assert(t>=0&&t<30);assert(seen[t][s]==1);seen[t][s]=0;prev=n;
  }
 }
 for(int t=0;t<30;t++)for(int s=0;s<5;s++)assert(!seen[t][s]);
}
int main(void){
 R23_MapMemoryInit(1033,691,1302);
 unsigned rng=12345;
 for(unsigned k=0;k<10000;k++){
  rng=rng*1664525u+1013904223u;unsigned t=(rng>>16)%30;
  rng=rng*1664525u+1013904223u;unsigned s=(rng>>16)%5;
  _s_sector_list=heads[t];P_AddSecnode(&sectors[s],&things[t]);P_AddSecnode(&sectors[s],&things[t]);heads[t]=_s_sector_list;
  if(k%3==0){
   unsigned v=(t+7)%30;msecnode_t *n=heads[v];
   for(unsigned skip=(rng>>8)%5;skip&&n;skip--)n=R23_GET(n,m_tnext);
   if(n){msecnode_t *next=P_DelSecnode(n);if(n==heads[v])heads[v]=next;}
  }
  check();
 }
 for(int t=0;t<30;t++)while(heads[t])heads[t]=P_DelSecnode(heads[t]);check();
 for(unsigned i=0;i<65536;i+=2)assert(bytes[i]==0);
 puts("PASS 10000 production SRAM contact insert/dedup/unlink cycles; both thread/backlink invariants and freelist reuse");return 0;
}
''';(p/'test.c').write_text(code)
 subprocess.run(['cc','-O2','-no-pie','-fsanitize=undefined','-fno-sanitize-recover=undefined','-Wno-pointer-to-int-cast','-Wno-int-to-pointer-cast','-DDOOM_R23_MAPMEM','-DDOOM_R22_SRAM_BLOCKLINKS',str(p/'prod.c'),str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
