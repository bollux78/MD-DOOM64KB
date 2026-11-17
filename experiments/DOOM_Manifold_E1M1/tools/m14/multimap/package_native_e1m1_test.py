#!/usr/bin/env python3
"""Package a PRIVATE single-map M14 SRAM trial ROM from a genuine staged E1M1.

Builds NO Doom assets itself. It must be run on the user's self-hosted runner
after staging the PRIVATE WAD and compiling the real E1M1 SGDK map.

Only E1M1 is playable in this trial. The original Manifold 12MiB multi-map ROM
is unchanged. No copyrighted outputs are uploaded to GitHub.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import os
import struct
import subprocess
from PIL import Image

BASE = Path(__file__).resolve().parent
BANK=0x80000
ROM_SIZE = 12*1024*1024
MAP_FILE_ORG = 0x280000
COMMON_ORG = 0x10000
WPN_ORG = 0x200000
MAP_ENTRY = 0x300200

MENU_C = r'''
#include "m14_sram.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;
#define VDP_DATA (*(volatile u16 *)0xC00000)
#define VDP_CTRL (*(volatile u16 *)0xC00004)
#define VDP_CTRL32 (*(volatile u32 *)0xC00004)
#define PAD_DATA (*(volatile u8 *)0xA10003)
#define PAD_CTRL (*(volatile u8 *)0xA10009)
extern const u32 font_tiles[768];

static void vreg(u8 r,u8 v){VDP_CTRL=0x8000 | (r<<8) | v;}
static void vram_w(u16 a){VDP_CTRL32=0x40000000UL | ((u32)(a&0x3fff)<<16) | ((a&0xc000)>>14);}
static void cram_w(u16 a){VDP_CTRL32=0xc0000000UL|((u32)a<<16);}
static void puttext(u16 col,u16 row,const char *s,u16 pal){
    vram_w(0xC000 + (row*64 + col)*2);
    while (*s) { unsigned char c=*s++; VDP_DATA=(pal<<13) | (c>=32 && c<=127 ? c-32 : 0); }
}
static void wait_vblank(void){
    while (VDP_CTRL&8) {}
    while (!(VDP_CTRL&8)) {}
}
static u16 pad_read(void){
    u16 r;
    PAD_DATA=0x40;
    __asm volatile("nop\n nop\n nop\n nop");
    r=(~PAD_DATA)&0x3f;
    PAD_DATA=0x00;
    __asm volatile("nop\n nop\n nop\n nop");
    r|=((~PAD_DATA)&0x30)<<2;
    PAD_DATA=0x40;
    return r;
}
/* Mirror the known M14 mapper transition but launch only E1M1. */
static void launch(void){
    int i;
    vreg(1,0x04);
    vram_w(0);
    for(i=0;i<32768;i++) VDP_DATA=0;
    cram_w(0);
    for(i=0;i<64;i++) VDP_DATA=0;
    *((volatile u16*)0xA130F0)=0x8000;
    *((volatile u16*)0xA130F2)=1;
    *((volatile u16*)0xA130F4)=2;
    *((volatile u16*)0xA130F6)=3;
    *((volatile u16*)0xA130F8)=4;
    *((volatile u16*)0xA130FA)=5; /* SRAM driver also restores slot5 to 5 */
    *((volatile u16*)0xA130FC)=5; /* E1M1 data bank at file offset $280000 */
    *((volatile u16*)0xA130FE)=6;
    *((volatile u8*)0xA10009)=0;
    *((volatile u8*)0xA1000B)=0;
    *((volatile u8*)0xA1000D)=0;
    __asm volatile("move.w #0x2700,%%sr\n move.l #0,%%sp\n jmp 0x300200\n" ::: "memory");
    for(;;){}
}
int main(void) {
    u16 last=0xffff;
    int i;
    __asm volatile("move.w #0x2700,%sr");
    vreg(1,0x04); vreg(15,2);
    vram_w(0); for(i=0;i<32768;i++) VDP_DATA=0;
    cram_w(0); for(i=0;i<64;i++) VDP_DATA=0;
    VDP_CTRL32=0x40000010UL; for(i=0;i<40;i++) VDP_DATA=0;
    vreg(0,0x04);vreg(1,0x04);vreg(2,0x30);vreg(3,0);vreg(4,0x07);
    vreg(5,0);vreg(7,0);vreg(10,0);vreg(11,0);vreg(12,0x81);
    vreg(13,0x2c);vreg(15,2);vreg(16,1);vreg(17,0);vreg(18,0);
    PAD_CTRL=0x40; PAD_DATA=0x40;
    vram_w(0);
    for(i=0;i<768;i++) {
        VDP_DATA=font_tiles[i]>>16;
        VDP_DATA=font_tiles[i];
    }
    cram_w((2*16+1)*2);VDP_DATA=0x0eee;
    cram_w((3*16+1)*2);VDP_DATA=0x00ee;
    vreg(7,0x00);
    puttext(7,6,"MANIFOLD - NATIVE SAVE TEST",2);
    puttext(10,11,"E1M1 HANGAR  /  SSF",2);
    puttext(8,15,"START: INICIAR E1M1",2);
    puttext(8,18,"B: CARREGAR CHECKPOINT",2);
    puttext(8,23,"NO JOGO: START PAUSA",2);
    puttext(8,25,"A SAVE / B LOAD / C FASES",2);
    puttext(7,27,"TESTE EXPERIMENTAL - 1 FASE",3);
    vreg(1,0x44); /* display on, NO bare-menu VBlank IRQ */
    for(;;) {
        u16 pad;
        wait_vblank();
        pad=pad_read();
        if(pad != last) {
            if (pad & 0x10) {
                m14_checkpoint saved;
                if (m14_sram_load(&saved) && saved.w[3]==0 &&
                    m14_sram_request(0)) launch();
                puttext(8,19,"SAVE INEXISTENTE OU INVALIDO",3);
            }
            if(pad & 0xa0) launch(); /* C / Start -- C used only in game */
        }
        last=pad;
    }
}
'''.replace("0xa0) launch(); /* C / Start -- C used only in game */","0x80) launch(); /* Start */")

def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True)

def dump_sections(objcopy, elf, tmp):
    def section(name,sections):
        dst=tmp/(name+".bin")
        run([objcopy,"-O","binary",*[x for sec in sections for x in ("-j",sec)],str(elf),str(dst)],tmp)
        b=dst.read_bytes()
        if not b: raise RuntimeError("Empty compiled section "+name)
        return b
    return (section("common",[".common"]),
            section("map",[".maphead",".data",".mapobjs",".mapextra"]),
            section("wpn",[".wpndata"]))

def gen_font(font):
    img=Image.open(font).convert("RGB")
    if img.size!=(128,48):
        raise ValueError(f"Unexpected SGDK font image size: {img.size}")
    data=[]
    for ci in range(96):
        cx,cy=(ci%16)*8,(ci//16)*8
        for y in range(8):
            row=0
            for x in range(8):
                p=img.getpixel((cx+x,cy+y))
                row=(row<<4) | (1 if max(p)>127 else 0)
            data.append(row)
    assert len(data)==768
    return "typedef unsigned long u32;\nconst u32 font_tiles[768]={\n"+",".join("0x%08xUL"%x for x in data)+"\n};\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--map-elf",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--font",type=Path,required=True)
    ap.add_argument("--tool-prefix",required=True)
    ap.add_argument("--work",type=Path,required=True)
    a=ap.parse_args()
    a.work.mkdir(parents=True,exist_ok=True)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    tc=a.tool_prefix
    common,block,wpn=dump_sections(tc+"objcopy",a.map_elf.resolve(),a.work.resolve())
    if COMMON_ORG+len(common)>WPN_ORG: raise ValueError("Common text overlaps weapon bank")
    if len(wpn)>BANK: raise ValueError("Weapon bank exceeds 512 KiB")
    if len(block)>2*BANK: raise ValueError("E1M1 map block exceeds one MiB")
    src=a.work/"test_menu.c"
    src.write_text(MENU_C)
    (a.work/"font.c").write_text(gen_font(a.font))
    run([tc+"as","-m68000",str(BASE/"crt0.s"),"-o","crt0.o"],a.work)
    for stem in ("test_menu","font"):
        run([tc+"gcc","-m68000","-Os","-ffreestanding","-fno-pic","-fno-builtin","-nostdlib",
             "-I",str(BASE),"-c",stem+".c","-o",stem+".o"],a.work)
    run([tc+"ld","-T",str(BASE/"menu.ld"),"crt0.o","test_menu.o","font.o","-o","menu.elf"],a.work)
    run([tc+"objcopy","-O","binary","menu.elf","menu.bin"],a.work)
    menu=(a.work/"menu.bin").read_bytes()
    assert len(menu)<=0x10000,("Boot menu too large",len(menu))
    assert menu[0x100:0x110]==b"SEGA SSF        "
    assert menu[0x1b0:0x1b4]==bytes.fromhex("5241e020")
    assert menu[0x1b4:0x1bc]==bytes.fromhex("002c0000002c00ff")
    rom=bytearray(b"\xff")*ROM_SIZE
    rom[:len(menu)]=menu
    rom[COMMON_ORG:COMMON_ORG+len(common)]=common
    rom[WPN_ORG:WPN_ORG+len(wpn)]=wpn
    rom[MAP_FILE_ORG:MAP_FILE_ORG+len(block)]=block
    # Correct physical ROM end in standard Sega header.
    rom[0x1a4:0x1a8]=struct.pack(">I",ROM_SIZE-1)
    # Sanity check SGDK map image entry data at physical $280200.
    if rom[MAP_FILE_ORG+0x200:MAP_FILE_ORG+0x210]==b"\xff"*16:
        raise ValueError("Map SGDK entry unexpectedly blank")
    a.out.write_bytes(rom)
    print("NATIVE-SAVE E1M1 ONLY")
    print("PRIVATE_ROM_PATH=",a.out)
    print("SIZE=",len(rom))
    print("SHA256=",hashlib.sha256(rom).hexdigest())
    print("COMMON_KB=",len(common)//1024,
          "MAP_KB=",len(block)//1024,"WPN_KB=",len(wpn)//1024,
          "MENU_BYTES=",len(menu))
    print("SRAM_HEADER=",rom[0x1b0:0x1bc].hex())
    print("START load E1M1. START pauses, A saves, B loads, C returns to menu.")
    print("Use B in the text boot menu to resume a checkpoint after power-cycle.")

if __name__=="__main__":
    main()
