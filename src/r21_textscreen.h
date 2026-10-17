/* R21 F1: result/error text screens without VDP_init(), and an optional
 * probe of the SGDK heap at that moment. GPL-2.0-or-later.
 *
 * Why: SGDK VDP_init() -> VDP_resetScreen() -> VDP_loadDefaultFont(DMA)
 * unpacks the compressed default font into MEM_alloc(~3 KB). When the SGDK
 * heap cannot provide that block, VDP_resetScreen() stops in while(TRUE).
 * R20h control has ~3124 B free at the end of DEMO3; S5 and V2 used more.
 * The font is already in VRAM since boot (the HUD draws TILE_FONT_INDEX). */
#ifndef R21_TEXTSCREEN_H
#define R21_TEXTSCREEN_H
#include <stdint.h>
#if defined(DOOM_R21_NO_VDP_INIT) || defined(DOOM_R21_HEAP_PROBE)
/* Read these two words with the BlastEm debugger when a ROM hangs:
 * m68k-elf-nm rom.out | grep r21_heap_at_end  -> p/x <address> */
extern volatile uint16_t r21_heap_at_end_free, r21_heap_at_end_largest;
void I_R21_ProbeHeap(void);
#define R21_PROBE_HEAP() I_R21_ProbeHeap()
#else
#define R21_PROBE_HEAP() ((void)0)
#endif
#if defined(DOOM_R21_NO_VDP_INIT)
void I_R21_TextScreen(void);   /* replaces VDP_init() on text screens */
#define R21_TEXT_SCREEN() I_R21_TextScreen()
#else
#define R21_TEXT_SCREEN() VDP_init()
#endif
#endif
