#!/usr/bin/env python3
"""Run the actual snapshot producer against A->B->A and mid-capture delivery.
Host test covers delta/hash invariants; BlastEm separately covers bus/endian ABI.
"""
import subprocess,tempfile
from pathlib import Path
source=Path(__file__).with_name('sub_world.c').resolve()
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)
    (d/'world_wire.h').write_text('#include <stdint.h>\n#define S2B_MAX_SECTORS 32\n#define S2B_MAX_SIDES 64\n#define S2B_SUB_WORLD 0x74000UL\n#define S2B_CAPACITY 32768\n#define S2B_MAGIC 0x53325742UL\n')
    (d/'world_values.h').write_text('''#include <stdint.h>
extern int _g_numsectors,_g_leveltime;
extern uint32_t live_sector[20][5],live_side[32][4];
static inline uint32_t S2B_Mix(uint32_t h,uint32_t v){return (((h<<5)|(h>>27))^v)+0x9e3779b9U;}
static inline void S2B_SectorValues(uint16_t i,uint32_t *v){for(int j=0;j<5;j++)v[j]=live_sector[i][j];}
static inline void S2B_SideValues(uint16_t i,uint32_t *v){for(int j=0;j<4;j++)v[j]=live_side[i][j];}
''')
    (d/'w_wad.h').write_text('typedef struct {char x[8];} mapsidedef_t;\nstatic int W_GetNumForName(const char *n){return 0;}\nstatic int W_LumpLength(int i){return 32*8;}\n')
    (d/'i_system.h').write_text('#include <stdlib.h>\nstatic void I_Error(const char *s){abort();}\n')
    c='''#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <stdio.h>
int _g_numsectors=20,_g_leveltime;
uint32_t live_sector[20][5],live_side[32][4],md_sector[20][5],md_side[32][4];
unsigned char staged[32768];int polls,deliver_at;
void M15_WorldDelivered(void);
static void apply(const unsigned char *b){
 const uint16_t *c=(const uint16_t *)(b+256);unsigned ns=c[2],nd=c[3];const unsigned char *p=b+272;
 for(unsigned j=0;j<ns;j++,p+=16){unsigned i=*(const uint16_t *)p;md_sector[i][0]=*(const uint32_t *)(p+4);md_sector[i][1]=*(const uint32_t *)(p+8);md_sector[i][2]=(int32_t)*(const int16_t *)(p+12);md_sector[i][3]=(int32_t)*(const int16_t *)(p+14);md_sector[i][4]=(int32_t)*(const int16_t *)(p+2);}
 for(unsigned j=0;j<nd;j++,p+=12){unsigned i=*(const uint16_t *)p;for(int k=0;k<4;k++)md_side[i][k]=(int32_t)*(const int16_t *)(p+2+k*2);}
}
void S2F_ClockPoll(void){if(++polls==deliver_at){apply(staged);M15_WorldDelivered();}}
#include "ACTUAL_SOURCE"
static uint32_t seed=1;
static uint32_t rnd(void){seed=seed*1664525U+1013904223U;return seed;}
static void verify(void){
 assert(!memcmp(md_sector,live_sector,sizeof md_sector));assert(!memcmp(md_side,live_side,sizeof md_side));
 uint32_t h=S2B_Mix(S2B_Mix(2166136261U,20),32);
 for(unsigned i=0;i<20;i++){uint32_t f=S2B_Mix(2166136261U,i);for(int k=0;k<5;k++)f=S2B_Mix(f,live_sector[i][k]);h^=f;}
 for(unsigned i=0;i<32;i++){uint32_t f=S2B_Mix(2166136261U,0x80000000U|i);for(int k=0;k<4;k++)f=S2B_Mix(f,live_side[i][k]);h^=f;}
 assert(h==*(const uint32_t *)(0x74000UL+264));
}
int main(void){
 assert(mmap((void *)0x74000,32768,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0)!=(void *)-1);
 for(int i=0;i<20;i++){live_sector[i][0]=-(i<<16);live_sector[i][1]=128<<16;live_sector[i][2]=-3;live_sector[i][3]=2;live_sector[i][4]=160;}
 for(int i=0;i<32;i++){live_side[i][0]=-32;live_side[i][1]=-1;live_side[i][2]=3;live_side[i][3]=-1;}
 S2B_Capture(0);S2B_Finish();apply((void *)0x74000);M15_WorldDelivered();verify();
 for(int t=0;t<400;t++){
  uint32_t old=live_sector[3][0];live_sector[3][0]+=65536;live_side[4][1]=7;
  S2B_Capture(0);S2B_Finish();memcpy(staged,(void *)0x74000,*(uint32_t *)0x74014);
  live_sector[3][0]=old;live_side[4][1]=-1;
  unsigned i=rnd()%20,k=rnd()%5;live_sector[i][k]=k<2?(rnd()%128)*65536:(int32_t)(int16_t)((rnd()%100)-3);
  i=rnd()%32;k=rnd()%4;live_side[i][k]=k==0?(int32_t)(int16_t)(rnd()%400-200):(int32_t)(int8_t)(rnd()%100-1);
  polls=0;deliver_at=(t%4)+1;
  S2B_Capture(0);S2B_Finish();if(polls<deliver_at){apply(staged);M15_WorldDelivered();}
  apply((void *)0x74000);M15_WorldDelivered();verify();
 }
 puts("M15 actual C producer: 400 asynchronous A->B->A delta/hash cases PASS");
}
'''.replace('ACTUAL_SOURCE',source.as_posix())
    (d/'test.c').write_text(c)
    subprocess.run(['gcc','-std=gnu11','-O2','-I'+str(d),str(d/'test.c'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
