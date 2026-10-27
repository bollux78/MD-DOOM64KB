#!/usr/bin/env python3
"""Compile actual R35 loader against fake VDP ports; compare both PNGs exactly."""
from pathlib import Path
import json,runpy,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
g=runpy.run_path(str(ROOT/'scripts/lab/gen_r78_art.py'))
config=json.loads((ROOT/'assets/art/r78-palettes.json').read_text())
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp);decl=[];counts={}
    for key,spec in config.items():
        blobs,decoded,report=g['encode'](ROOT/'assets/art'/spec['file'],spec)
        (p/(key+'.rgb')).write_bytes(decoded.tobytes());counts[key]=report['tiles']
        for suffix,data in blobs.items():
            values=list(data) if suffix=='pack' else [int.from_bytes(data[i:i+2],'big') for i in range(0,len(data),2)]
            typ='u8' if suffix=='pack' else 'u16'
            decl.append('const '+typ+' r30_'+key+'_'+suffix+'[]={'+','.join(map(str,values))+'};')
    decl.extend(['const u8 r30_final_pack[32]={0};','const u16 r30_final_map[1120]={0};','const u16 r30_final_pal[64]={0};'])
    (p/'r30_static_manifest.h').write_text(f'#define R30_TITLE_TILES {counts["title"]}\n#define R30_INTER_TILES {counts["inter"]}\n#define R30_FINAL_TILES 1\n')
    (p/'r35_native4.inc').write_text((ROOT/'src/r35_native4.inc').read_text())
    pre='''#define _GNU_SOURCE
#include <sys/mman.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef int bool;
#define DOOM_R30_NATIVE 1
#define DOOM_R35_ART_RAW 1
#define DOOM_R47_PLANE_PAIR 1
#define DOOM_R48_PAIR_V 1
#define DOOM_R50_STATIC_MENU 1
#define DOOM_R78_ART 1
#define DOOM_R79_SHADOW 1
#define DOOM_R77_MENU 1
#define DOOM_R59_COLOR_VIEW 1
#define DOOM_R56_DUAL_COLOR 1
static uint8_t r77_last_palette=13,r59_color_dirty=1;
static const uint16_t test_pal0[14][16]={{2}},test_pal1[14][16]={{4}};
#define R79_PAL0 test_pal0
#define R79_PAL1 test_pal1
static int shadow_enabled=1;
static void VDP_setHilightShadow(int value){shadow_enabled=value;}
#define TRUE 1
#define FALSE 0
#define CPU 0
#define BG_A 0
#define BG_B 1
#define WINDOW 2
#define VDP_WRITE_VRAM_ADDR(a) (a)
static uint8_t vram[1440][32];static uint16_t map[3][1120],palette[64];
static int8_t r22_newpal,r22_queued_pal;
static uint8_t r22_overlay_dirty,r22_text_this_frame;
static uint16_t r22_front,r22_ready;
static void R20_StopVideo(void){}
static void VDP_setEnable(int a){(void)a;}
static void VDP_clearPlane(int a,int b){(void)b;memset(map[a],0,sizeof(map[a]));}
static void VDP_waitDMACompletion(void){}
static void VDP_setWindowHPos(int a,int b){(void)a;(void)b;}
static void VDP_setWindowVPos(int a,int b){(void)a;(void)b;}
static void VDP_setAutoInc(int a){(void)a;}
static void VDP_setHorizontalScroll(int a,int b){(void)a;(void)b;}
static void VDP_setVerticalScroll(int a,int b){(void)a;(void)b;}
static uint16_t R22_Lock(void){return 0;}
static void R22_Unlock(uint16_t a){(void)a;}
static void R47_LoadPairTiles(void){}
static void R47_ClearPairBuffer(void){}
static void R40B_ResetNativeText(void){}
static void VDP_loadTileData(const u32 *data,u16 index,u16 n,int method){
 (void)method;assert(n==1 && index>=16 && index<1440);memcpy(vram[index],data,32);
}
static void VDP_setTileMapDataRect(int plane,const u16*row,u16 x,u16 y,u16 w,u16 h,u16 pitch,int method){
 (void)pitch;(void)method;assert(x==0 && w==40 && h==1 && y<28);memcpy(map[plane]+y*40,row,80);
}
static void PAL_setColors(u16 index,const u16*pal,u16 n,int method){(void)method;memcpy(palette+index,pal,n*2);}
static int16_t W_GetNumForName(const char *s){return !strcmp(s,"TITLEPIC")?1:!strcmp(s,"WIMAP0")?2:3;}
'''
    main='''#include "r35_native4.inc"
static uint8_t nib(uint16_t attr,unsigned q){uint8_t v=vram[attr&0x7ff][q/2];return q%2?v&15:v>>4;}
int main(void){
 assert(mmap((void*)0xC00000,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED,-1,0)==(void*)0xC00000);
 const char *files[2]={"title.rgb","inter.rgb"};
 for(unsigned pic=0;pic<2;++pic){
  assert(R35_DrawNative4(pic+1));assert(shadow_enabled==0);FILE*f=fopen(files[pic],"rb");assert(f);
  for(unsigned y=0;y<224;++y)for(unsigned x=0;x<320;++x){
   unsigned t=(y/8)*40+x/8,q=(y%8)*8+x%8;
   uint16_t a=map[BG_A][t],b=map[BG_B][t];uint8_t ca=nib(a,q),cb=nib(b,q);
   uint16_t w=ca?palette[((a>>13)&3)*16+ca]:palette[((b>>13)&3)*16+cb];
   for(unsigned k=0;k<3;++k){unsigned c=(w>>(1+4*k))&7;assert(fgetc(f)==(int)((c<<5)|(c<<2)|(c>>1)));}
   assert(R35_NativeMapWord(x/8,y/8)==a);
  }
  assert(fgetc(f)==EOF);fclose(f);
 }
 assert(R35_DrawNative4(3));assert(memcmp(map[BG_A],map[BG_B],sizeof(map[0]))==0);
 r77_last_palette=13;r59_color_dirty=1;R35_LeaveNative4();
 assert(r35_native_active==-1 && r77_last_palette==0 && r59_color_dirty==0);
 assert(memcmp(palette,test_pal0[0],32)==0 && memcmp(palette+16,test_pal1[0],32)==0);
 assert(shadow_enabled==0);
}
'''
    (p/'test.c').write_text(pre+'\n'.join(decl)+'\n'+main)
    subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-function',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],cwd=p,check=True)
print('PASS R79 actual native loader: art RGB exact, shadow off on static screens, palette zero coherent after damage-tinted native exit')
