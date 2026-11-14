/* Bare-metal SSF2 level-select menu (no SGDK, no interrupts).
   Each map is a complete SGDK image linked at 0x080000 and mapped into
   slots 1..4 (512 KB each) by the SSF2 bank registers. */
#include "menu.h"
#include "maps.h"
#ifndef NSLOT
#define NSLOT 7
#endif
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned long u32;
#define VDP_DATA  (*(volatile u16 *)0xC00000)
#define VDP_CTRL  (*(volatile u16 *)0xC00004)
#define VDP_CTRL32 (*(volatile u32 *)0xC00004)
#define PAD_DATA  (*(volatile u8 *)0xA10003)
#define PAD_CTRL  (*(volatile u8 *)0xA10009)

static void vreg(u8 r, u8 v) { VDP_CTRL = 0x8000 | (r << 8) | v; }
static void vram_w(u16 a) { VDP_CTRL32 = 0x40000000UL | ((u32)(a & 0x3FFF) << 16) | ((a & 0xC000) >> 14); }
static void cram_w(u16 a) { VDP_CTRL32 = 0xC0000000UL | ((u32)a << 16); }
/* ---- title music: r25-intro.vgm played straight from the 68000 (1 VGM frame per vblank) ---- */
extern const unsigned char intro_vgm[];
extern const unsigned short intro_vgm_loop;
#define Z80_BUS (*(volatile u16 *)0xA11100)
#define Z80_RST (*(volatile u16 *)0xA11200)
#define YM_ST   (*(volatile u8 *)0xA04000)
#define PSG_PORT (*(volatile u8 *)0xC00011)
/* the menu has no .bss/.data (ROM only): the player pointer lives at the bottom of work RAM */
#define mus_p (*(const unsigned char * volatile *)0xFF0000)
static void ym_w(int part, u8 reg, u8 val) {
    volatile u8 *p = (volatile u8 *)(0xA04000 + part * 2);
    while (YM_ST & 0x80) ;
    p[0] = reg;
    while (YM_ST & 0x80) ;
    p[1] = val;
}
static void music_silence(void) {
    int c;
    PSG_PORT = 0x9F; PSG_PORT = 0xBF; PSG_PORT = 0xDF; PSG_PORT = 0xFF;
    for (c = 0; c < 8; c++) if (c != 3 && c != 7) ym_w(0, 0x28, c);   /* key off */
    ym_w(0, 0x2B, 0);                                                /* DAC off */
}
static void music_start(void) {
    volatile int i;
    Z80_RST = 0x100; Z80_BUS = 0x100;      /* take the Z80 bus so the 68000 owns the YM2612 */
    while (Z80_BUS & 0x100) ;
    Z80_RST = 0x000; for (i = 0; i < 200; i++) ;   /* reset pulse (bus stays ours) */
    Z80_RST = 0x100; for (i = 0; i < 200; i++) ;
    music_silence();
    mus_p = intro_vgm;
}
static void music_stop(void) {
    if (!mus_p) return;
    mus_p = 0;
    music_silence();
    Z80_RST = 0x000; Z80_BUS = 0x000;      /* power-on-like Z80 state for the game's own init */
}
static void music_tick(void) {
    const unsigned char *p = mus_p;
    int guard = 0;
    if (!p) return;
    for (;;) {
        u8 b = *p++;
        if (b == 0x62) break;
        else if (b == 0x50) PSG_PORT = *p++;
        else if (b == 0x52 || b == 0x53) { u8 r = p[0], v = p[1]; p += 2; ym_w(b - 0x52, r, v); }
        else if (b == 0x66) { p = intro_vgm + intro_vgm_loop; if (++guard > 1) break; }
        else break;   /* unknown command: stop this frame */
    }
    mus_p = p;
}

static void wait_vblank(void) {
    while (VDP_CTRL & 8) ;      /* leave current vblank */
    while (!(VDP_CTRL & 8)) ;   /* wait for next one */
    music_tick();
}
static void delay(int n) { while (n--) wait_vblank(); }

static u16 pad_read(void) {   /* bit set = pressed: 0 U,1 D,2 L,3 R,4 B,5 C,6 A,7 START */
    u16 r;
    PAD_DATA = 0x40; __asm volatile("nop\n nop\n nop\n nop");
    r = (~PAD_DATA) & 0x3F;
    PAD_DATA = 0x00; __asm volatile("nop\n nop\n nop\n nop");
    r |= ((~PAD_DATA) & 0x30) << 2;   /* A=bit4->6, START=bit5->7 */
    return r;
}

#define PLANE_A 0xC000
static void put_cell(int col, int row, u16 attr) {
    vram_w(PLANE_A + (row * 64 + col) * 2);
    VDP_DATA = attr;
}
static void text(int col, int row, const char *s, int pal) {
    vram_w(PLANE_A + (row * 64 + col) * 2);
    while (*s) { VDP_DATA = (pal << 13) | (*s - 32); s++; }
}
static void clear_plane(void) {
    int i; vram_w(PLANE_A);
    for (i = 0; i < 64 * 32; i++) VDP_DATA = 0;
}
static void set_color(int idx, u16 c) { cram_w(idx * 2); VDP_DATA = c; }

static void set_banks(int mapbank);
static void bank_test(int k) {
    int s, j, bad;
    const struct map_entry *mp = &maps[k];
    set_banks(mp->bank);
    clear_plane();
    text(8, 4, "TESTE DE BANCOS (SSF2)", 3);
    text(8, 6, mp->name, 2);
    for (s = 1; s <= NSLOT; s++) {
        bad = 0;
        for (j = 0; j < 8; j++)
            if (*(volatile u32 *)(0x80000UL * (u32)s + (u32)j * 0x10000UL + 0x1230UL) != bank_expect[k][s - 1][j]) bad++;
        text(8, 9 + s, "SLOT", 2);
        text(13, 9 + s, s == 1 ? "1" : s == 2 ? "2" : s == 3 ? "3" : s == 4 ? "4" : s == 5 ? "5" : s == 6 ? "6" : "7", 2);
        text(16, 9 + s, bad == 0 ? "OK" : "ERRO", bad == 0 ? 2 : 3);
        if (bad) text(22, 9 + s, "AMOSTRAS RUINS", 3);
    }
    #ifndef LAYOUT_PER_MAP
    text(8, 20, "SLOTS 1-5 COMUM, 6-7 FASE", 2);
#endif
    text(8, 22, "START NO JOGO VOLTA AQUI", 2);
    vreg(1, 0x44);
    for (;;) wait_vblank();
}
/* slots 1..5 (0x080000-0x2FFFFF) = banks 1..5: the common code/data block shared by every map;
   slots 6..7 (0x300000-0x3FFFFF) = the selected map's own block */
static void set_banks(int mapbank) {
#ifdef LAYOUT_PER_MAP   /* 10 MB layout: each map = 4 banks mapped at slots 1..4 */
    *(volatile u8 *)0xA130F3 = mapbank; *(volatile u8 *)0xA130F5 = mapbank + 1;
    *(volatile u8 *)0xA130F7 = mapbank + 2; *(volatile u8 *)0xA130F9 = mapbank + 3;
    return;
#endif
    *(volatile u8 *)0xA130F3 = 1; *(volatile u8 *)0xA130F5 = 2; *(volatile u8 *)0xA130F7 = 3;
    *(volatile u8 *)0xA130F9 = 4; *(volatile u8 *)0xA130FB = 5;
    *(volatile u8 *)0xA130FD = mapbank; *(volatile u8 *)0xA130FF = mapbank + 1;
}
static void launch(int k) {
    int i;
    const struct map_entry *m = &maps[k];
    /* black screen, clear VRAM so the map starts from a clean VDP */
    music_stop();
    vreg(1, 0x04);
    vram_w(0); for (i = 0; i < 32768; i++) VDP_DATA = 0;
    cram_w(0); for (i = 0; i < 64; i++) VDP_DATA = 0;
    set_banks(m->bank);
    /* make the map's SGDK startup take the full cold-start path */
    *(volatile u8 *)0xA10009 = 0; *(volatile u8 *)0xA1000B = 0; *(volatile u8 *)0xA1000D = 0;
    __asm volatile("move.w #0x2700,%%sr\n"
                   "move.l #0,%%sp\n"
                   "jmp %c0\n" : : "i"(MAP_ENTRY));
    for (;;) ;
}

int main(void) {
    int i, sel = 0, prev;
    u16 pad, last = 0xFFFF;
    /* START in game leaves a magic + map id in work RAM: open on the level list with that map selected */
    volatile u32 *rb = (volatile u32 *)0xFF0010;
    int skip_title = 0;
    if (rb[0] == 0x4D454E55UL && (rb[1] >> 16) == 0x4C56 && (rb[1] & 0xFFFF) < MAP_COUNT) { skip_title = 1; sel = rb[1] & 0xFFFF; }
    rb[0] = 0; rb[1] = 0;

    /* after a RESET the game leaves VDP state/VRAM behind: put every register in a
       known state, then wipe VRAM, CRAM and VSRAM (cold boot has them zeroed) */
#ifndef WIPE_MODE
#define WIPE_MODE 2   /* hardware: bit0 (regs) da tela preta; so bit1 funciona. bit0 = reset VDP regs, bit1 = wipe VRAM/CRAM/VSRAM (0 = neither) */
#endif
#if WIPE_MODE & 1
    vreg(1, 0x04);
    vreg(6, 0); vreg(8, 0); vreg(9, 0); vreg(14, 0);
    vreg(19, 0); vreg(20, 0); vreg(21, 0); vreg(22, 0); vreg(23, 0);   /* no DMA fill/copy pending */
    vreg(15, 2);
#endif
#if WIPE_MODE & 2
    vreg(15, 2);
    vram_w(0); for (i = 0; i < 32768; i++) VDP_DATA = 0;
    cram_w(0); for (i = 0; i < 64; i++) VDP_DATA = 0;
    VDP_CTRL32 = 0x40000010UL; for (i = 0; i < 40; i++) VDP_DATA = 0;   /* VSRAM */
#endif
    vreg(0, 0x04); vreg(1, 0x04); vreg(2, PLANE_A >> 10); vreg(3, 0); vreg(4, 0x07);
    vreg(5, 0); vreg(7, 0x00); vreg(10, 0); vreg(11, 0); vreg(12, 0x81);
    vreg(13, 0x2C); vreg(15, 2); vreg(16, 0x01); vreg(17, 0); vreg(18, 0);
    PAD_CTRL = 0x40;
#ifdef AUTO_LAUNCH
    music_stop(); launch(AUTO_LAUNCH - 1);
#endif

    /* tiles: font at 0..95, title at 96.. */
    vram_w(0);
    for (i = 0; i < 96 * 8; i++) { VDP_DATA = font_tiles[i] >> 16; VDP_DATA = font_tiles[i]; }
    for (i = 0; i < 1120 * 8; i++) { VDP_DATA = title_tiles[i] >> 16; VDP_DATA = title_tiles[i]; }
    cram_w(0);
    for (i = 0; i < 32; i++) VDP_DATA = title_pal[i];
    for (i = 0; i < 32; i++) VDP_DATA = 0;
    set_color(32 + 1, 0x0EEE);   /* palette 2: white text   */
    set_color(48 + 1, 0x00EE);   /* palette 3: yellow (selected/heading) */
    set_color(48 + 15, 0x0000);  /* backdrop (R7 = pal 3 idx 15) */

    /* title screen */
    if (!skip_title) {
    clear_plane();
    { int r, c; for (r = 0; r < 28; r++) for (c = 0; c < 40; c++) put_cell(c, r, title_attr[r * 40 + c] | (96 + r * 40 + c)); }
    text(14, 25, "PRESS START", 2);
    vreg(7, 0x00);   /* title: backdrop = palette 0 colour 0 (same as picture colour 0) */
    vreg(1, 0x44);
    music_start();
    while (pad_read() & 0xFF) wait_vblank();
    for (;;) { wait_vblank(); if (pad_read() & 0xC0) break; }
    } else { vreg(7, 0x3F); clear_plane(); vreg(1, 0x44); music_start(); }   /* wait_vblank needs the display on */
    while (pad_read() & 0xFF) wait_vblank();

    /* level menu */
    vreg(7, 0x3F);
    clear_plane();
    text(9, 4, "MANIFOLD DOOM - E1M1..E1M9", 3);
#ifdef BUILD_TAG
    text(2, 1, BUILD_TAG, 2);
#endif
    text(13, 6, "SELECIONE A FASE", 3);
    for (;;) {
        for (i = 0; i < MAP_COUNT; i++) {
            text(10, 9 + i * 1, i == sel ? "> " : "  ", 3);
            text(12, 9 + i * 1, maps[i].name, i == sel ? 3 : 2);
        }
        text(8, 23, "CIMA/BAIXO: ESCOLHER", 2);
        text(8, 25, "START: JOGAR", 2);
        text(8, 27, "START NO JOGO VOLTA AQUI", 2);
        text(8, 21, "A: TESTE DE BANCOS", 2);
        vreg(1, 0x44);
        wait_vblank();
        pad = pad_read();
        if (pad != last) {
            prev = sel;
            if (pad & 1) sel = sel ? sel - 1 : MAP_COUNT - 1;
            if (pad & 2) sel = (sel + 1 < MAP_COUNT) ? sel + 1 : 0;
            if (pad & 0x40) { vreg(1, 0x04); bank_test(sel); }
            if (pad & 0xA0) { vreg(1, 0x04); launch(sel); }
            (void)prev;
        }
        last = pad;
    }
}
