#!/usr/bin/env python3
"""Exercise production odd-lane SRAM I/O and actual blockmap link routines."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
def fn(s,name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);d=0
 for i in range(b,len(s)):
  if s[i]=='{':d+=1
  if s[i]=='}':
   d-=1
   if not d:return s[a:i+1]
h=(r/'src/r22_blocklinks.h').read_text().replace('#include "globdata.h"','')
c=(r/'src/r22_blocklinks.c').read_text();p=(r/'src/p_maputl.c').read_text()
code=r'''
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
#include <setjmp.h>
#define DOOM_R22_SRAM_BLOCKLINKS
#define __far
#define MF_NOSECTOR 1
#define MF_NOBLOCKMAP 2
#define MAPBLOCKSHIFT 0
#define false 0
#define true 1
typedef int boolean;
typedef struct mobj_s mobj_t;
typedef struct {mobj_t *thinglist;} sector_t;
typedef struct {sector_t *sector;} subsector_t;
struct mobj_s {int32_t x,y;unsigned flags; mobj_t *bnext,**bprev,*snext,**sprev;subsector_t *subsector;void *touching_sectorlist;};
static mobj_t nodes[128];static sector_t sector;static subsector_t ss={&sector};
static int16_t _g_bmapwidth,_g_bmapheight;static int32_t _g_bmaporgx,_g_bmaporgy;
static subsector_t *R_PointInSubsector(int32_t x,int32_t y){(void)x;(void)y;return &ss;}
static void P_SetSeclist(void *p){(void)p;}
static void P_CreateSecNodeList(mobj_t *p){(void)p;}
static uint8_t sram[32768];static unsigned usable=16384,enables;
static volatile uint8_t *byte_at(uint32_t a){assert(a>=0x200000 && a<0x208000 && (a&1));return &sram[((((a-0x200000)>>1)%usable)<<1)+1];}
#define R22_SRAM_BYTE(a) (*byte_at(a))
#define R22_SRAM_ENABLE() (++enables)
static jmp_buf jump;static char error[80];
static void I_Error(const char *s){strcpy(error,s);longjmp(jump,1);}
'''+h+r'''
uint16_t r22_block_cells;
'''+fn(c,'void R22_BlockInit(')+'\n'+fn(p,'void P_UnsetThingPosition(')+'\n'+fn(p,'void P_SetThingPosition(')+'\n'+fn(p,'boolean P_BlockThingsIterator(')+r'''
static uint32_t rng=12345;
static uint32_t next(void){rng=rng*1664525u+1013904223u;return rng;}
static int slot[128];static unsigned iter_count,iter_sum;
static boolean visit(mobj_t *p){assert(p>=nodes && p<nodes+128);iter_count++;iter_sum+=(unsigned)(p-nodes);return 1;}
static void check(void){
 for(unsigned k=0;k<r22_block_cells;k++){
  unsigned n=0,sum=0,want=0,ws=0;mobj_t **prev=R22_BlockSlot(k);
  for(mobj_t *p=R22_BlockHead(k);p;p=p->bnext){assert(++n<=128);unsigned i=p-nodes;assert(i<128 && slot[i]==(int)k && p->bprev==prev && R22_LinkLoad(prev)==p);sum+=i;prev=&p->bnext;}
  for(unsigned i=0;i<128;i++)if(slot[i]==(int)k){want++;ws+=i;}
  assert(n==want && sum==ws);iter_count=iter_sum=0;assert(P_BlockThingsIterator(k%_g_bmapwidth,k/_g_bmapwidth,visit));assert(iter_count==want && iter_sum==ws);
 }
}
int main(void){
 assert((uintptr_t)nodes<0x100000000ULL);memset(sram,0xCC,sizeof(sram));
 if(!setjmp(jump)){R22_BlockInit(65,64);assert(0);}assert(strstr(error,"TOO LARGE"));
 usable=8192;if(!setjmp(jump)){R22_BlockInit(52,56);assert(0);}assert(strstr(error,"TOO SMALL"));
 usable=1;if(!setjmp(jump)){R22_BlockInit(36,23);assert(0);}assert(strstr(error,"SRAM"));
 usable=16384;if(setjmp(jump)){fprintf(stderr,"unexpected %s\n",error);return 1;}
 for(unsigned pass=0;pass<3;pass++){
  unsigned w=pass==0?36:pass==1?52:64,h=pass==0?23:pass==1?56:64;
  memset(sram,0xCC,sizeof(sram));R22_BlockInit(w,h);assert(r22_block_cells==w*h);
  for(unsigned i=0;i<r22_block_cells;i++)assert(!R22_BlockHead(i));
  for(unsigned i=0;i<32768;i+=2)assert(sram[i]==0xCC);
  for(unsigned i=r22_block_cells*8+1;i<32768;i+=2)assert(sram[i]==0xCC);
  for(unsigned i=0;i<10000;i++){unsigned k=next()%r22_block_cells;uint32_t v=next();uint32_t a=0x200000+k*8;R22_SramWrite32(a,v);assert(R22_SramRead32(a)==v);}
 }
 R22_BlockInit(52,56);_g_bmapwidth=52;_g_bmapheight=56;memset(nodes,0,sizeof(nodes));
 for(unsigned i=0;i<128;i++){slot[i]=-1;nodes[i].flags=MF_NOSECTOR;}
 for(unsigned i=0;i<3;i++){nodes[i].x=nodes[i].y=0;P_SetThingPosition(&nodes[i]);slot[i]=0;}check();
 P_UnsetThingPosition(&nodes[1]);slot[1]=-1;check(); /* middle */
 P_UnsetThingPosition(&nodes[2]);slot[2]=-1;check(); /* head */
 P_UnsetThingPosition(&nodes[0]);slot[0]=-1;check(); /* last */
 for(unsigned op=0;op<10000;op++){
  unsigned i=next()%128;
  if(slot[i]>=0){P_UnsetThingPosition(&nodes[i]);slot[i]=-1;}
  unsigned k=next()%2912;
  if(next()&1){nodes[i].x=k%52;nodes[i].y=k/52;P_SetThingPosition(&nodes[i]);slot[i]=k;}
  else{nodes[i].x=-1;nodes[i].y=0;P_SetThingPosition(&nodes[i]);assert(!nodes[i].bnext && !nodes[i].bprev);}
  if(op%100==0)check();
 }
 check();for(unsigned i=0;i<128;i++)if(slot[i]>=0){P_UnsetThingPosition(&nodes[i]);slot[i]=-1;}check();
 R22_BlockInit(36,23);for(unsigned i=0;i<828;i++)assert(!R22_BlockHead(i));
 puts("PASS odd-lane byte I/O,16KB capacity,8KB/absent rejection,32-bit values,10000 production insert/unlink/move operations and iterator/backlink invariants");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'t.c';p.write_text(code);e=Path(d)/'t';subprocess.run(['cc','-O2','-no-pie','-fsanitize=undefined','-fno-sanitize-recover=undefined',str(p),'-o',str(e)],check=True);subprocess.run([str(e)],check=True)
