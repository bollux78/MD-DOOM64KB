/* Bare-metal SSF2 level-select menu (no SGDK, no interrupts).
   Each map is a complete SGDK image linked at 0x080000 and mapped into
   slots 1..4 (512 KB each) by the SSF2 bank registers. */
#include "menu.h"
#include "maps.h"
#include "m14_sram.h"
#include "m14_tele.h"
/* freestanding build: the checkpoint struct copies in m14_sram.h need memcpy */
__attribute__((optimize("no-tree-loop-distribute-patterns")))
void *memcpy(void *d, const void *s, unsigned long n) {
    unsigned char *p = d; const unsigned char *q = s;
    while (n--) *p++ = *q++;
    return d;
}
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
#ifndef INTER_MUS_ADDR
#define INTER_MUS_ADDR 0x380000UL   /* bank 24 at slot 7 */
#endif
#define mus_base (*(const unsigned char * volatile *)0xFF0004)
#define mus_loop (*(volatile unsigned long *)0xFF0008)
static void music_start(void) {
    volatile int i;
    Z80_RST = 0x100; Z80_BUS = 0x100;      /* take the Z80 bus so the 68000 owns the YM2612 */
    while (Z80_BUS & 0x100) ;
    Z80_RST = 0x000; for (i = 0; i < 200; i++) ;   /* reset pulse (bus stays ours) */
    Z80_RST = 0x100; for (i = 0; i < 200; i++) ;
    music_silence();
    mus_base = intro_vgm; mus_loop = intro_vgm_loop; *(volatile unsigned char *)0xFF003C = 0;
    mus_p = intro_vgm;
}
/* intermission tune: LZ stream at 0x2F9600 (gen_inter_music.py), decoded on the fly through a 16 KB ring in RAM */
#define LZ_SRC0 ((const unsigned char *)INTER_MUS_ORG)
#define LZ_RING ((volatile unsigned char *)0xFF4000)
#define LZ_W 16384
struct lzst { const unsigned char *src; unsigned long wpos; unsigned short mrem, moff; unsigned char fl, nb; const unsigned char *base; };
#define LZ ((volatile struct lzst *)0xFF0040)
#define mus_lz (*(volatile unsigned char *)0xFF003C)
static void lz_reset(void) { LZ->src = LZ->base; LZ->wpos = 0; LZ->mrem = 0; LZ->nb = 0; }
static unsigned char lz_next(void) {
    unsigned char b;
    if (!LZ->mrem) {
        if (!LZ->nb) { LZ->fl = *LZ->src++; LZ->nb = 8; }
        if (LZ->fl & 1) b = *LZ->src++;
        else {
            const unsigned char *s = LZ->src;
            LZ->moff = (((unsigned short)s[0] << 8) | s[1]) + 1; LZ->mrem = s[2] + 4; LZ->src = s + 3;
        }
        LZ->fl >>= 1; LZ->nb--;
        if (LZ->mrem) { b = LZ_RING[(LZ->wpos - LZ->moff) & (LZ_W - 1)]; LZ->mrem--; }
    } else { b = LZ_RING[(LZ->wpos - LZ->moff) & (LZ_W - 1)]; LZ->mrem--; }
    LZ_RING[LZ->wpos & (LZ_W - 1)] = b; LZ->wpos++;
    return b;
}
static void music_start_inter(void) {
    music_start();
    LZ->base = LZ_SRC0; lz_reset(); mus_lz = 1;
}
static void music_start_end(void) {
    music_start();
    LZ->base = (const unsigned char *)END_MUS_ORG; lz_reset(); mus_lz = 1;
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
    if (mus_lz) {
        for (;;) {
            u8 b = lz_next();
            if (b == 0x62) break;
            else if (b == 0x50) PSG_PORT = lz_next();
            else if (b == 0x52 || b == 0x53) { u8 r = lz_next(), v = lz_next(); ym_w(b - 0x52, r, v); }
            else if (b == 0x66) { lz_reset(); if (++guard > 1) break; }
            else break;
        }
        return;
    }
    for (;;) {
        u8 b = *p++;
        if (b == 0x62) break;
        else if (b == 0x50) PSG_PORT = *p++;
        else if (b == 0x52 || b == 0x53) { u8 r = p[0], v = p[1]; p += 2; ym_w(b - 0x52, r, v); }
        else if (b == 0x66) { p = mus_base + mus_loop; if (++guard > 1) break; }
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
/* full-screen picture n from the credits bank (slot 6): 0 title, 1 credits, 2 disclaimer, 3 end. blob = pal[64] attr[1120] tiles[1120*16] */
static void show_image(int n) {
    const u16 *ib; int i, r, c;
    *(volatile u8 *)0xA130FD = CREDITS_BANK;
    ib = (const u16 *)(0x300000UL + (u32)n * 38208UL);
    vreg(1, 0x04);
    vram_w(96 * 32); for (i = 0; i < 1120 * 16; i++) VDP_DATA = ib[64 + 1120 + i];
    cram_w(0); for (i = 0; i < 64; i++) VDP_DATA = ib[i];
    clear_plane();
    for (r = 0; r < 28; r++) for (c = 0; c < 40; c++) put_cell(c, r, ib[64 + r * 40 + c] | (96 + r * 40 + c));
    vreg(7, 0x00); vreg(1, 0x44);
}

static void set_banks(int mapbank, int xbank);
static void bank_test(int k) {
    int s, j, bad;
    const struct map_entry *mp = &maps[k];
    set_banks(mp->bank, mp->xbank);
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
static void set_banks(int mapbank, int xbank) {
#ifdef LAYOUT_PER_MAP   /* 10 MB layout: each map = 4 banks mapped at slots 1..4 */
    *(volatile u8 *)0xA130F3 = mapbank; *(volatile u8 *)0xA130F5 = mapbank + 1;
    *(volatile u8 *)0xA130F7 = mapbank + 2; *(volatile u8 *)0xA130F9 = mapbank + 3;
    return;
#endif
    *(volatile u8 *)0xA130F3 = 1; *(volatile u8 *)0xA130F5 = 2; *(volatile u8 *)0xA130F7 = 3;
    *(volatile u8 *)0xA130F9 = 4; *(volatile u8 *)0xA130FB = xbank;
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
    set_banks(m->bank, m->xbank);
    /* make the map's SGDK startup take the full cold-start path */
    *(volatile u8 *)0xA10009 = 0; *(volatile u8 *)0xA1000B = 0; *(volatile u8 *)0xA1000D = 0;
    __asm volatile("move.w #0x2700,%%sr\n"
                   "move.l #0,%%sp\n"
                   "jmp %c0\n" : : "i"(MAP_ENTRY));
    for (;;) ;
}

/* ================= test ROM "tele": SRAM telemetry viewer + benchmark ================= */
static u32 udiv(u32 n, u32 d) {      /* no libgcc: bitwise division */
    u32 q = 0, r = 0; int i;
    if (!d) return 0xFFFFFFFFUL;
    for (i = 31; i >= 0; i--) { r = (r << 1) | ((n >> i) & 1); if (r >= d) { r -= d; q |= 1UL << i; } }
    return q;
}
static void numr(int col, int row, u32 v, int w, int pal) {
    char b[12]; int i = w; b[w] = 0;
    do { u32 q = udiv(v, 10); b[--i] = (char)('0' + (v - (q << 3) - (q << 1))); v = q; } while (v && i > 0);
    while (i > 0) b[--i] = ' ';
    text(col, row, b, pal);
}
static void f10(int col, int row, u32 v, int w, int pal) {   /* v is value*10 */
    char b[12]; int i = w; u32 q = udiv(v, 10); b[w] = 0;
    b[--i] = (char)('0' + (v - (q << 3) - (q << 1))); b[--i] = '.';
    do { u32 q2 = udiv(q, 10); b[--i] = (char)('0' + (q - (q2 << 3) - (q2 << 1))); q = q2; } while (q && i > 0);
    while (i > 0) b[--i] = ' ';
    text(col, row, b, pal);
}
static void hex4(int col, int row, u16 v, int pal) {
    char b[5]; int i;
    for (i = 3; i >= 0; i--) { u16 d = v & 15; b[i] = (char)(d < 10 ? '0' + d : 'A' + d - 10); v >>= 4; }
    b[4] = 0; text(col, row, b, pal);
}
static void wait_release(void) { while (pad_read() & 0xFF) wait_vblank(); }
static int is_pal(void) { return (*(volatile u8 *)0xA10001) & 0x40; }
static void setup_text_pal(void) { set_color(0, 0x0000); set_color(32 + 1, 0x0EEE); set_color(48 + 1, 0x00EE); set_color(48 + 15, 0x0000); }

/* canary / boot counter: proves whether the cart's SRAM really keeps data across power-off */
static int canary_boot(void) {   /* returns boot count (0 = no persistence / write failed) */
    m14_tele_rec r, v; m14_sram_guard g; int ok;
    g = m14_sram_enter(1);
    m14t_read(M14T_CANARY, &r);
    if (m14t_valid(&r)) { if (r.w[T_SESS] < 0xFFFF) r.w[T_SESS]++; r.w[3] = 1; }   /* w3 = a valid record existed before this boot */
    else { int i; for (i = 0; i < 32; i++) r.w[i] = 0; r.w[T_MAGIC] = M14T_MAGIC; r.w[T_VER] = M14T_VER; r.w[T_SESS] = 1; r.w[3] = 0; }
    m14t_write(M14T_CANARY, &r);
    m14t_read(M14T_CANARY, &v);
    ok = m14t_valid(&v) && v.w[T_SESS] == r.w[T_SESS];
    m14_sram_leave(g);
    return ok ? (int)r.w[T_SESS] : 0;
}
#define canary_prev (*(volatile u16 *)0xFF0024)   /* menu has no .bss: ROM-linked statics would be lost */
static int canary_peek(void) {
    m14_tele_rec r; m14_sram_guard g;
    g = m14_sram_enter(0); m14t_read(M14T_CANARY, &r); m14_sram_leave(g);
    canary_prev = r.w[3];
    return m14t_valid(&r) ? (int)r.w[T_SESS] : -1;
}

/* ---- benchmark ---- */
#define NBENCH 10
static const char *const bench_name[NBENCH] = {
    "WRAM LER", "WRAM ESCREVER", "ROM LER", "JANELA ABRE/FECHA Z80 RETIDO", "JANELA ABRE/FECHA Z80 LIVRE",
    "SRAM LER", "SRAM ESCREVER", "SRAM>WRAM 1KB", "WRAM>WRAM 1KB", "WRAM>SRAM 1KB" };
static const signed char bench_ref[NBENCH] = { -1, -1, 0, -1, -1, 0, 1, 8, -1, 8 };
static const u8 bench_sh[NBENCH] = { 6, 6, 6, 4, 4, 6, 6, 9, 9, 9 };   /* log2(ops per call) */
#define bsink (*(volatile u16 *)0xFF0026)
static void bench_once(int id) {
    volatile u16 *w = (volatile u16 *)0xFF8000; volatile u16 *w2 = (volatile u16 *)0xFFA000;
    volatile u16 *sr = M14_SRAM_WORDS + M14T_SCRATCH;
    int i; u16 acc = 0;
    switch (id) {
    case 0: for (i = 0; i < 64; i++) acc += w[i]; break;
    case 1: for (i = 0; i < 64; i++) w[i] = (u16)i; break;
    case 2: { volatile u16 *rm = (volatile u16 *)0x1000; for (i = 0; i < 64; i++) acc += rm[i]; } break;
    case 3: case 4: for (i = 0; i < 16; i++) { m14_sram_guard g = m14_sram_enter(0); m14_sram_leave(g); } break;
    case 5: for (i = 0; i < 64; i++) acc += sr[i]; break;
    case 6: for (i = 0; i < 64; i++) sr[i] = (u16)i; break;
    case 7: for (i = 0; i < 512; i++) w2[i] = sr[i & 255]; break;
    case 8: for (i = 0; i < 512; i++) w2[i] = w[i]; break;
    case 9: for (i = 0; i < 512; i++) sr[i & 255] = w[i]; break;
    }
    bsink = acc;
}
/* returns kilo-ops/second over 20 video frames */
static u32 bench_run(int id) {
    u32 reps = 0, ops; int frames = 0; u16 prev;
    m14_sram_guard g; int win = (id >= 5 && id != 8 && id != 3 && id != 4) || id == 7 || id == 9;
    if (id == 3) { int to = 300; Z80_BUS = 0x0100; while ((Z80_BUS & 0x0100) && --to) { } }
    if (id == 4) Z80_BUS = 0;
    if (win) g = m14_sram_enter(id == 6 || id == 9);
    while (VDP_CTRL & 8) { }
    while (!(VDP_CTRL & 8)) { }
    prev = 1;
    for (;;) {
        u16 v;
        bench_once(id); reps++;
        v = VDP_CTRL & 8;
        if (v && !prev) { if (++frames >= 20) break; }
        prev = v;
    }
    if (win) m14_sram_leave(g);
    if (id == 3) Z80_BUS = 0;
    ops = reps << bench_sh[id];               /* ops in 20 frames */
    ops = is_pal() ? ((ops << 2) + ops) >> 1 : (ops << 1) + ops;   /* x2.5 (50 Hz) or x3 (60 Hz) = ops per second */
    return udiv(ops, 1000);
}
static void bench_row(int i, u32 kops, const u16 *all) {
    int r = 6 + i;
    text(1, r, bench_name[i], 2);
    numr(29, r, kops, 6, 3);
    if (bench_ref[i] >= 0 && kops) f10(36, r, udiv(((u32)all[(int)bench_ref[i]]) * 10, kops), 4, 2);
}
/* pattern readback: write 256 words, verify, then the complement. returns number of bad words, details in *firstbad */
static int pattern_test(u16 *exp, u16 *got, int *at) {
    int i, pass, bad = 0; m14_sram_guard g;
    *at = -1; *exp = 0; *got = 0;
    g = m14_sram_enter(1);
    for (pass = 0; pass < 2; pass++) {
        u16 a = 0;
        for (i = 0; i < 256; i++) { u16 pv = a ^ 0xA5A5; a += 0x9E37; M14_SRAM_WORDS[M14T_SCRATCH + i] = pass ? (u16)~pv : pv; }
        a = 0;
        for (i = 0; i < 256; i++) {
            u16 pv = a ^ 0xA5A5; u16 e = pass ? (u16)~pv : pv; u16 gv = M14_SRAM_WORDS[M14T_SCRATCH + i]; a += 0x9E37;
            if (gv != e) { if (!bad) { *exp = e; *got = gv; *at = i; } bad++; }
        }
    }
    m14_sram_leave(g);
    return bad;
}
static void bench_screen(void) {
    u16 all[NBENCH]; int i, bad, at; u16 e, gv;
    m14_tele_rec rec; m14_sram_guard g;
    music_stop();
    vreg(1, 0x04); clear_plane(); setup_text_pal();
    text(8, 1, "BENCHMARK DE SRAM", 3);
    text(8, 3, is_pal() ? "CONSOLE PAL 50 HZ" : "CONSOLE NTSC 60 HZ", 2);
    text(1, 5, "TESTE", 3); text(29, 5, "KOPS/S", 3); text(36, 5, "REL", 3);
    vreg(1, 0x44);
    for (i = 0; i < NBENCH; i++) {
        text(1, 24, "TESTE", 3); numr(7, 24, (u32)(i + 1), 2, 3); text(10, 24, "DE 10", 3); text(1, 26, "SE TRAVAR, ANOTE O NUMERO DO TESTE", 2);
        all[i] = 0;
        { u32 k = bench_run(i); all[i] = k > 0xFFFF ? 0xFFFF : (u16)k; bench_row(i, k, all); }
    }
    for (i = 0; i < NBENCH; i++) bench_row(i, all[i], all);   /* redraw: ratios need later tests */
    bad = pattern_test(&e, &gv, &at);
    text(1, 24, "                                        ", 2); text(1, 26, "                                        ", 2);
    text(1, 17, "PADRAO 256 PALAVRAS (+COMPLEMENTO)", 3);
    if (!bad) text(1, 18, "LEITURA IGUAL A ESCRITA: OK", 2);
    else {
        text(1, 18, "ERRO EM", 3); numr(9, 18, (u32)bad, 4, 3); text(14, 18, "PALAVRAS", 3);
        text(1, 19, "1O ERRO NO INDICE", 3); numr(19, 19, (u32)at, 3, 3);
        text(1, 20, "ESPERADO", 3); hex4(10, 20, e, 3); text(16, 20, "LIDO", 3); hex4(21, 20, gv, 3);
    }
    /* persist results */
    g = m14_sram_enter(1);
    for (i = 0; i < 32; i++) rec.w[i] = 0;
    rec.w[T_MAGIC] = M14T_MAGIC; rec.w[T_VER] = M14T_VER; rec.w[T_SESS] = is_pal() ? 1 : 0;
    for (i = 0; i < NBENCH; i++) rec.w[3 + i] = all[i];
    rec.w[14] = (u16)bad;
    m14t_write(M14T_BENCH, &rec);
    m14_sram_leave(g);
    text(1, 22, "RESULTADOS SALVOS NA SRAM", 2);
    text(1, 25, "B OU START: VOLTAR", 2);
    wait_release();
    for (;;) { wait_vblank(); if (pad_read() & 0xB0) break; }
    wait_release();
}

/* ---- telemetry viewer ---- */
static void diag_screen(void) {
    m14_tele_rec rec[9], bn; int ok[9], bnok, page = 0, i, boots; m14_sram_guard g; u16 last = 0xFFFF, pad; int redraw = 1;
    vreg(1, 0x04); setup_text_pal();
    g = m14_sram_enter(0);
    for (i = 0; i < 9; i++) { m14t_read(M14T_BASE + i * M14T_STRIDE, &rec[i]); ok[i] = m14t_valid(&rec[i]); }
    m14t_read(M14T_BENCH, &bn); bnok = m14t_valid(&bn);
    m14_sram_leave(g);
    boots = canary_peek();
    for (;;) {
        if (redraw) {
            vreg(1, 0x04); clear_plane(); redraw = 0;
            if (page == 0) {
                text(1, 1, "TELEMETRIA - RESUMO", 3);
                text(1, 3, "MAPA", 3); text(7, 3, "MED", 3); text(12, 3, "PIOR", 3); text(18, 3, "FOLGA", 3); text(24, 3, "TRIP", 3); text(28, 3, "PROF", 3); text(33, 3, "SES", 3); text(37, 3, "MIN", 3);
                for (i = 0; i < 9; i++) {
                    static const char nm[9][5] = {"E1M1","E1M2","E1M3","E1M4","E1M5","E1M6","E1M7","E1M8","E1M9"};
                    int r = 4 + i;
                    text(1, r, nm[i], 2);
                    if (!ok[i]) { text(6, r, "--", 1); continue; }
                    {
                        u32 fr = ((u32)rec[i].w[T_FH] << 16) | rec[i].w[T_FL];
                        u32 tk = ((u32)rec[i].w[T_TH] << 16) | rec[i].w[T_TL];
                        u32 fr3 = (fr << 11) + (fr << 9) + (fr << 8) + (fr << 7) + (fr << 5) + (fr << 4) + (fr << 3);   /* x3000 */
                        u32 mn = rec[i].w[T_DTMAX] ? udiv(3000, rec[i].w[T_DTMAX]) : 0;
                        u32 gap = 65536UL - rec[i].w[T_STK] - rec[i].w[T_HEAP];
                        f10(6, r, udiv(fr3, tk), 5, 2);
                        f10(12, r, mn, 5, 2);
                        numr(18, r, gap, 5, 2);
                        numr(24, r, rec[i].w[T_TRIPS], 4, rec[i].w[T_TRIPS] ? 3 : 2);
                        numr(29, r, rec[i].w[T_DEPTH], 3, 2);
                        numr(33, r, rec[i].w[T_SESS], 3, 2);
                        numr(37, r, udiv(tk, 18000), 3, 2);
                    }
                }
                text(1, 14, "MED/PIOR = FPS MEDIO / PIOR QUADRO", 2);
                text(1, 15, "FOLGA = BYTES LIVRES HEAP-PILHA", 2);
                text(1, 16, "TRIP = CORTES POR FALTA DE PILHA", 2);
                text(1, 17, "PROF = NIVEL MAX DE PORTAIS", 2);
                text(1, 18, "SES = SESSOES   MIN = MINUTOS JOGADOS", 2);
            } else if (page == 1) {
                text(1, 1, "TELEMETRIA - % QUADROS POR FAIXA", 3);
                text(1, 3, "MAPA  >=30 >=20 >=15 >=10  <10", 3);
                for (i = 0; i < 9; i++) {
                    static const char nm[9][5] = {"E1M1","E1M2","E1M3","E1M4","E1M5","E1M6","E1M7","E1M8","E1M9"};
                    int r = 4 + i, b;
                    u32 tot = 0;
                    text(1, r, nm[i], 2);
                    if (!ok[i]) { text(6, r, "--", 1); continue; }
                    for (b = 0; b < 5; b++) tot += rec[i].w[T_B0 + b];
                    for (b = 0; b < 5; b++) { u32 c = rec[i].w[T_B0 + b]; numr(6 + b * 5, r, udiv((c << 6) + (c << 5) + (c << 2), tot), 3, 2); }
                }
                text(1, 14, "FAIXAS = FPS INSTANTANEO DO QUADRO", 2);
            } else {
                text(1, 1, "BENCHMARK SALVO", 3);
                if (!bnok) text(1, 3, "SEM RESULTADOS - USE DIREITA NO MENU", 1);
                else {
                    u16 all[NBENCH];
                    text(1, 3, bn.w[T_SESS] ? "PAL 50 HZ" : "NTSC 60 HZ", 2);
                    text(1, 5, "TESTE", 3); text(29, 5, "KOPS/S", 3); text(36, 5, "REL", 3);
                    for (i = 0; i < NBENCH; i++) all[i] = bn.w[3 + i];
                    for (i = 0; i < NBENCH; i++) bench_row(i, all[i], all);
                    if (bn.w[14]) { text(1, 17, "PADRAO COM ERROS:", 3); numr(19, 17, bn.w[14], 4, 3); }
                    else text(1, 17, "PADRAO DE LEITURA/ESCRITA: OK", 2);
                }
            }
                        if (boots > 0) {
                text(1, 21, "BOOT NUMERO", 3); numr(13, 21, (u32)boots, 4, 2);
                text(1, 22, canary_prev ? "DADOS DO BOOT ANTERIOR: ENCONTRADOS" : "DADOS DO BOOT ANTERIOR: NENHUM", canary_prev ? 2 : 3);
            } else text(1, 21, "SRAM SEM REGISTRO", 3);
            text(1, 24, "A: PAGINA   B OU START: VOLTAR", 2);
            vreg(1, 0x44);
        }
        wait_vblank();
        pad = pad_read();
        if (pad != last) {
            if (pad & 0x40) { page = page == 2 ? 0 : page + 1; redraw = 1; }
            if (pad & 0xB0) break;
        }
        last = pad;
    }
    wait_release();
}
static void splash(void) {
    int n, lim = is_pal() ? 750 : 900;
    vreg(1, 0x04); clear_plane(); setup_text_pal();
#ifdef BUILD_TAG
    text(2, 4, BUILD_TAG, 3);
#endif
    text(2, 7, "TESTE: TELEMETRIA E SRAM", 3);
    text(2, 9, "O JOGO GRAVA NA SRAM: FPS, PILHA,", 2);
    text(2, 10, "HEAP E CORTES DE PILHA, POR FASE.", 2);
    text(2, 12, "MENU: ESQ=TELEMETRIA DIR=BENCH SRAM", 2);
    text(2, 13, "JOGUE NORMAL; USE PAUSA (START).", 2);
    text(2, 16, "APERTE START OU AGUARDE 15 SEGUNDOS", 3);
    vreg(7, 0x00); vreg(1, 0x44);
    wait_release();
    for (n = 0; n < lim; n++) { wait_vblank(); if (pad_read() & 0x80) break; }
    wait_release();
}

int main(void) {
    int i, sel = 0, prev;
    u16 pad, last = 0xFFFF;
    /* START in game leaves a magic + map id in work RAM: open on the level list with that map selected */
    volatile u32 *rb = (volatile u32 *)0xFF0010;
    int skip_title = 0;
#ifdef TEST_END
    rb[0] = 0x45584954UL; rb[1] = 0x4C560007UL;
#endif
    if (rb[0] == 0x4D454E55UL && (rb[1] >> 16) == 0x4C56 && (rb[1] & 0xFFFF) < MAP_COUNT) { skip_title = 1; sel = rb[1] & 0xFFFF; }
    int inter = 0, inter_next = -1;
    if (rb[0] == 0x45584954UL && (rb[1] >> 16) == 0x4C56 && (rb[1] & 0xFF) < MAP_COUNT) {
        /* level exit: intermission screen, then the next map. E1M3 secret -> E1M9, E1M9 -> E1M4, E1M8 -> list */
        static const signed char next_map[9] = { 1, 2, 3, 4, 5, 6, 7, -1, 3 };
        int done = rb[1] & 0xFF, secret = (rb[1] >> 8) & 1;
        inter = 1; skip_title = 1;
        inter_next = (done == 2 && secret) ? 8 : next_map[done];
        sel = inter_next >= 0 ? inter_next : 0;
    }
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
    if (inter) {
        const u16 *ib = (const u16 *)INTER_ORG;   /* pal[64] | attr[1120] | tiles[1120*16 words] */
        for (i = 0; i < 1120 * 16; i++) VDP_DATA = ib[64 + 1120 + i];
        cram_w(0);
        for (i = 0; i < 64; i++) VDP_DATA = ib[i];
    }

    if (inter) {
        const u16 *ib = (const u16 *)INTER_ORG;
        int r, c;
        clear_plane();
        for (r = 0; r < 28; r++) for (c = 0; c < 40; c++) put_cell(c, r, ib[64 + r * 40 + c] | (96 + r * 40 + c));
        vreg(7, 0x00);
        vreg(1, 0x44);
        music_start_inter();
        while (pad_read() & 0xFF) wait_vblank();
        delay(60);
        for (;;) { wait_vblank(); if (pad_read() & 0xF0) break; }
        while (pad_read() & 0xFF) wait_vblank();
        if (inter_next >= 0) { vreg(1, 0x04); launch(inter_next); }
        /* episode end: closing text with the ending tune, then the end picture, then the level list */
        vreg(1, 0x04); clear_plane(); setup_text_pal();
        {
            static const char *const ln[] = {
                "DEPOIS DE ACABAR COM OS CHEFOES E",
                "LIMPAR A BASE LUNAR, VOCE DEVIA",
                "GANHAR, NAO E? NAO E?",
                "CADE A SUA RECOMPENSA E O BILHETE",
                "DE VOLTA PARA CASA?",
                "",
                "QUE DIABOS E ISSO? NAO DEVIA",
                "TERMINAR ASSIM!",
                "CHEIRA A CARNE PODRE, MAS PARECE",
                "A BASE PERDIDA DE DEIMOS...",
                "PARECE QUE VOCE ESTA PRESO NAS",
                "MARGENS DO INFERNO. A UNICA SAIDA",
                "E ATRAVES DELE." };
            int k;
            for (k = 0; k < 13; k++) text(3, 5 + k, ln[k], 2);
        }
        vreg(7, 0x00); vreg(1, 0x44);
        music_start_end();
        while (pad_read() & 0xFF) wait_vblank();
        delay(60);
        for (;;) { wait_vblank(); if (pad_read() & 0xF0) break; }
        while (pad_read() & 0xFF) wait_vblank();
        show_image(3);
        while (pad_read() & 0xFF) wait_vblank();
        for (;;) { wait_vblank(); if (pad_read() & 0xF0) break; }
        while (pad_read() & 0xFF) wait_vblank();
    }
    if (!skip_title && !inter) { canary_boot(); splash(); }
    /* title screen */
    if (!skip_title) {
    show_image(0);
    music_start();
    while (pad_read() & 0xFF) wait_vblank();
    for (;;) { wait_vblank(); if (pad_read() & 0xC0) break; }
    } else { vreg(7, 0x3F); clear_plane(); vreg(1, 0x44); music_start(); }   /* wait_vblank needs the display on */
    while (pad_read() & 0xFF) wait_vblank();

    /* level menu */
    set_color(32 + 1, 0x0EEE); set_color(48 + 1, 0x00EE); set_color(48 + 15, 0x0000);   /* text palettes (also after the intermission) */
    for (;;) {
      menu_draw:
        set_color(0, 0x0000); set_color(32 + 1, 0x0EEE); set_color(48 + 1, 0x00EE); set_color(48 + 15, 0x0000);
        vreg(7, 0x3F);
        clear_plane();
        text(9, 4, "MANIFOLD DOOM - E1M1..E1M9", 3);
#ifdef BUILD_TAG
        text(2, 1, BUILD_TAG, 2);
#endif
        text(13, 6, "SELECIONE A FASE", 3);
        for (;;) {
        for (i = 0; i <= MAP_COUNT; i++) {
            text(10, 9 + i * 1, i == sel ? "> " : "  ", 3);
            text(12, 9 + i * 1, i < MAP_COUNT ? maps[i].name : "CREDITS", i == sel ? 3 : 2);
        }
        text(8, 19, "B: CARREGAR CHECKPOINT", 2);
        text(8, 20, "A: TESTE DE BANCOS", 2);
        text(4, 22, "ESQ: TELEMETRIA  DIR: BENCH SRAM", 3);
        text(8, 24, "CIMA/BAIXO: ESCOLHER", 2);
        text(8, 25, "START: JOGAR", 2);
        text(8, 27, "START NO JOGO VOLTA AQUI", 2);
        vreg(1, 0x44);
        wait_vblank();
        pad = pad_read();
        if (pad != last) {
            prev = sel;
            if (pad & 1) sel = sel ? sel - 1 : MAP_COUNT;
            if (pad & 2) sel = (sel < MAP_COUNT) ? sel + 1 : 0;
            if (pad & 0x40 && sel < MAP_COUNT) { vreg(1, 0x04); bank_test(sel); }
            if (pad & 4) { diag_screen(); last = 0xFFFF; goto menu_draw; }
            if (pad & 8) { bench_screen(); music_start(); last = 0xFFFF; goto menu_draw; }
            if (pad & 0x10) { /* B: load saved level after full power-off. */
                m14_checkpoint saved;
                if (m14_sram_load(&saved) && saved.w[3] < MAP_COUNT &&
                    m14_sram_request(saved.w[3])) {
                    vreg(1, 0x04);
                    launch(saved.w[3]); /* Restore checkpoint after SGDK startup */
                }
                text(8, 19, "SEM SAVE VALIDO", 3);
            }
            if (pad & 0xA0) {
                if (sel < MAP_COUNT) { vreg(1, 0x04); launch(sel); }
                else {   /* CREDITS: DoomCREDIT10 -> Disclaimer and Credits -> EndMD2 -> level menu; any button advances */
                    static const unsigned char order[3] = { 1, 2, 3 };
                    for (i = 0; i < 3; i++) {
                        while (pad_read() & 0xFF) wait_vblank();
                        show_image(order[i]);
                        for (;;) { wait_vblank(); if (pad_read() & 0xF0) break; }
                    }
                    while (pad_read() & 0xFF) wait_vblank();
                    last = 0xFFFF; goto menu_draw;
                }
            }
            (void)prev;
        }
        last = pad;
        }
    }
}
