#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,shutil
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 for n in ['r81_save.h','r81_save_io.h','r81_save_codec.inc']:shutil.copyfile(ROOT/'src'/n,p/n)
 (p/'test.c').write_text('''#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <limits.h>
typedef struct {int x;} mobj_t;typedef struct {int x;} thinker_t;
typedef struct {int x;} sector_t;typedef struct {int x;} line_t;
typedef struct {int x;} mapsidedef_t;typedef struct {int x;} mapsector_t;
static sector_t _g_sectors[256];static uint8_t ram[32768];
#define R81_SAVE_HOST_TEST 1
#include "r81_save_codec.inc"
uint8_t R81_SramRead(uint16_t p){assert(p<32768);return ram[p];}
void R81_SramWrite(uint16_t p,uint8_t v){assert(p>=R81_SAVE_BASE+16 && p<32768);ram[p]=v;}
int main(void){
 uint32_t rnd=1;
 for(unsigned trial=0;trial<1000;trial++){
  int32_t values[100];uint32_t uns[100];
  for(unsigned i=0;i<100;i++){
   rnd=rnd*1664525u+1013904223u;values[i]=(int32_t)rnd;uns[i]=rnd;
   if(i%4==0)values[i]=(int32_t)((uint32_t)values[i]<<(8*(trial%4)));
   if(i%5==0)values[i]=0;
  }
  values[1]=INT32_MIN;values[2]=INT32_MAX;values[3]=-65536;values[4]=0x20000000;
  r81_io_t out={0};out.mode=R81_WRITE;out.limit=R81_SAVE_CAPACITY-16;out.crc=65535;
  for(unsigned i=0;i<100;i++){assert(R81_N(&out,values[i])==values[i]);assert(R81_U(&out,uns[i])==uns[i]);}
  R81_Flush(&out);assert(!out.error);
  r81_io_t in={0};in.mode=R81_VALIDATE;in.limit=out.pos;in.crc=65535;
  for(unsigned i=0;i<100;i++){assert(R81_N(&in,0)==values[i]);assert(R81_U(&in,0)==uns[i]);}
  assert(!in.error && !in.zero_run && in.pos==in.limit && in.crc==out.crc);
 }
 r81_io_t out={0};out.mode=R81_WRITE;out.limit=R81_SAVE_CAPACITY-16;out.crc=65535;
 for(unsigned i=0;i<1024;i++)R81_N(&out,0);R81_Flush(&out);assert(out.pos==10);
 r81_io_t in={0};in.mode=R81_LOAD;in.limit=out.pos;in.crc=65535;
 for(unsigned i=0;i<1024;i++)assert(R81_N(&in,0)==0);assert(!in.error&&!in.zero_run&&in.pos==10&&in.crc==out.crc);
 out=(r81_io_t){0};out.mode=R81_WRITE;out.limit=1;R81_U(&out,UINT32_MAX);R81_Flush(&out);assert(out.error&&out.pos<=1);
 in=(r81_io_t){0};in.mode=R81_VALIDATE;in.limit=0;R81_N(&in,0);assert(in.error);
 struct sample{int8_t a;int16_t b;int32_t c;uint8_t arr[4];} before={-128,-32768,INT32_MIN,{0,255,128,127}},after={0};
 const r81_field_t fs[]={R81_F(struct sample,a),R81_F(struct sample,b),R81_F(struct sample,c),R81_A(struct sample,arr,4)};
 out=(r81_io_t){0};out.mode=R81_WRITE;out.limit=R81_SAVE_CAPACITY-16;out.crc=65535;R81_Fields(&out,&before,fs,4);R81_Flush(&out);
 in=(r81_io_t){0};in.mode=R81_LOAD;in.limit=out.pos;in.crc=65535;R81_Fields(&in,&after,fs,4);assert(!in.error&&after.a==before.a&&after.b==before.b&&after.c==before.c&&!memcmp(after.arr,before.arr,4));
 puts("PASS R81 codec: 100000 signed + unsigned values, extrema, zero RLE, field descriptors, bounds and CRC");
 return 0;
}''')
 subprocess.run(['gcc','-std=c99','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
