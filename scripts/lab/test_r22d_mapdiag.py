#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
def extract(s,name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);d=0
 for i in range(b,len(s)):
  if s[i]=='{':d+=1
  if s[i]=='}':
   d-=1
   if not d:return s[a:i+1]
z=(r/'src/z_zone.c').read_text();v=(r/'src/i_genesis.c').read_text()
code='''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define DOOM_R22_MAP_DIAG
#include "r22_mapdiag.h"
r22_map_entry r22_map_trace[16];
uint16_t r22_map_head,r22_map_count,r22_map_current,r22_map_stage,r22_map_request,r22_map_tag,r22_map_failed_stage;
uint32_t r22_map_need;
static uint32_t f,b;
static uint32_t Z_GetTotalFreeMemory(void){return f;}
static uint32_t Z_GetLargestFreeBlockSize(void){return b;}
static char screen[28][39];
static void VDP_drawText(const char *s,unsigned x,unsigned y){assert(x==1 && y<28 && strlen(s)<=38);strcpy(screen[y],s);}
'''+extract(z,'void R22_MapMark(')+'\n'+extract(v,'void R22_MapReport(')+'''
int main(void){
 for(unsigned s=0;s<14;s++){f=40000-s*1000;b=f-100;R22_MapMark(1,s);}
 for(unsigned s=0;s<=11;s++){f=30000-s*2000;b=f-200;R22_MapMark(8,s);}
 r22_map_request=2028;r22_map_need=2048;r22_map_tag=2;r22_map_failed_stage=11;
 R22_MapMark(8,14);assert(r22_map_count==16 && r22_map_current==8);
 unsigned seen_done=0,seen_pre=0,seen_post=0;
 for(unsigned i=0;i<16;i++){
  r22_map_entry *e=&r22_map_trace[(r22_map_head+16-r22_map_count+i)&15];
  if(e->map==1 && e->stage==13)seen_done++;
  if(e->map==8 && e->stage==0)seen_pre++;
  if(e->map==8 && e->stage==1)seen_post++;
 }
 assert(seen_done && seen_pre && seen_post);R22_MapReport();
 assert(strstr(screen[4],"MAP E1M8 STAGE 11"));assert(strstr(screen[5],"REQUEST 2028 NEED 2048 TAG 2"));
 r22_map_request=65535;r22_map_need=65552;r22_map_tag=255;R22_MapReport();
 char err[80];int n=sprintf(err,"Z_Malloc\\nREQ %u B\\nMAX %lu B\\nFREE %lu B",65535,4294967295ul,4294967295ul);assert(n<80);
 puts("PASS map trace: chronological ring, E1M1 DONE/E1M8 pre/post-free preserved, 38-column report and bounded malloc message");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'t.c';p.write_text(code);e=Path(d)/'t';subprocess.run(['cc','-O2','-fsanitize=undefined','-fno-sanitize-recover=undefined','-iquote'+str(r/'src'),str(p),'-o',str(e)],check=True);subprocess.run([str(e)],check=True)
