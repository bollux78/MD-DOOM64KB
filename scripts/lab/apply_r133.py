#!/usr/bin/env python3
"""Insert a one-shot SSF2 bank test before Doom title (R133 only)."""
from pathlib import Path

p=Path("src/d_main.c")
s=p.read_text()
marker="static void D_DoomMainSetup(void)"
assert s.count(marker)==1
insertion=r'''
#if defined(DOOM_R133_SSF_BOOT)
#include <genesis.h>
/* The first 4MiB hold the Doom engine/data. Slot 7 is remapped
   ONLY during this boot check, before title/gameplay begins.
   Extra pages 8 and 9 contain synthetic distinct signatures. */
#define R133_SLOT7 (*(volatile uint16_t *)(0x380100ul))
#define R133_MAPREG (*(volatile uint8_t *)(0xA130FFul))
static uint32_t R133_Signature(uint16_t p)
{
    return 0xA1310000ul ^ ((uint32_t)p*0x10203ul) ^ ((uint32_t)p<<24);
}
static void R133_TestAndShow(void)
{
    uint16_t ok8=1, ok9=1, okstress=1, okrestore=1;
    uint32_t old_word=*(volatile uint32_t *)(0x380100ul);
    /* Do not read/write SRAM: no SRAM register is touched here. */
    R133_MAPREG=8;
    if(*(volatile uint32_t *)(0x380100ul)!=R133_Signature(8))ok8=0;
    R133_MAPREG=9;
    if(*(volatile uint32_t *)(0x380100ul)!=R133_Signature(9))ok9=0;
    for(uint16_t i=0;i<1024;i++)
    {
        uint16_t pg=(i&1u)?9u:8u;
        R133_MAPREG=(uint8_t)pg;
        if(*(volatile uint32_t *)(0x380100ul)!=R133_Signature(pg))okstress=0;
    }
    R133_MAPREG=7;
    if(*(volatile uint32_t *)(0x380100ul)!=old_word)okrestore=0;

    VDP_setScreenWidth320();
    VDP_clearPlane(BG_A,TRUE);
    VDP_clearPlane(BG_B,TRUE);
    PAL_setColor(0,RGB24_TO_VDPCOLOR(0x101020));
    PAL_setColor(15,RGB24_TO_VDPCOLOR(0xFFFFFF));
    VDP_setTextPalette(PAL0);
    VDP_drawText("DOOM MD / SSF2 5 MiB",5,3);
    VDP_drawText("BANK 8 (4.0 - 4.5 MiB)",2,7);
    VDP_drawText(ok8 ? "PASS" : "FAIL",31,7);
    VDP_drawText("BANK 9 (4.5 - 5.0 MiB)",2,9);
    VDP_drawText(ok9 ? "PASS" : "FAIL",31,9);
    VDP_drawText("1024 BANK SWITCHES",2,11);
    VDP_drawText(okstress ? "PASS" : "FAIL",31,11);
    VDP_drawText("RESTORE ORIGINAL BANK",2,13);
    VDP_drawText(okrestore ? "PASS" : "FAIL",31,13);
    VDP_drawText(ok8&&ok9&&okstress&&okrestore?"ALL BANK TESTS: PASS":"BANK TESTS: FAIL",5,18);
    VDP_drawText("STARTING DOOM...",10,22);
    for(uint16_t i=0;i<180;i++) VDP_waitVSync();
    /* The next normal Doom title draw owns the display from this point. */
}
#endif

'''
s=s.replace(marker,insertion+marker)
needle="    I_InitGraphics();"
assert s.count(needle)==1
s=s.replace(needle,needle+"\n#if defined(DOOM_R133_SSF_BOOT)\n    R133_TestAndShow();\n#endif")
p.write_text(s)
print("R133 boot mapper integration applied.")
