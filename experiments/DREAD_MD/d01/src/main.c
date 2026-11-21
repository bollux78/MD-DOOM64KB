/* DREAD-MD D01: Dread-style renderer test on Mega Drive, Doom E1M1 (shareware WAD).
 *
 * Screen: H32, view 128x112 logical pixels (each 2x1 screen pixels), 4bpp tiles in RAM,
 * double-buffered: the CPU renders one RAM buffer while the VBlank interrupt DMAs the
 * previous one into the hidden VRAM copy, then flips plane A's name table. */
#include <genesis.h>
#include "render.h"
#include "game_hud.h"
#include "actors.h"
#ifndef DREAD_NO_MUSIC
#include "music.h"
#ifdef DREAD_EPISODE
static uint16_t selected_map;
static const uint8_t *const episode_music[] = {
    bgm_e1m1, bgm_e1m2, bgm_e1m3, bgm_e1m4, bgm_e1m5,
    bgm_e1m6, bgm_e1m7, bgm_e1m8, bgm_e1m9
};
#define MAP_MUSIC episode_music[selected_map]
#else
#define MAP_MUSIC bgm_e1m1
#endif
#endif
#ifndef START_MUSIC
#define START_MUSIC 1
#endif
static uint16_t music_on = START_MUSIC;

#ifndef ROM_NAME
#define ROM_NAME "DREAD-MD D01 SOM"
#endif
#ifndef DREAD_MAP_LABEL
#define DREAD_MAP_LABEL "E1M1 DOOM"
#endif
#ifndef START_MODE
#define START_MODE 0                           /* 0 H40 linhas, 1 H40 colunas, 2 H32 linhas, 3 H32 colunas */
#endif
/* SGDK 2.x VRAM: plane A name table at 0xE000 (flipped with 0xA000 when double-buffered), plane B 0xC000,
 * window 0xD000, font after the system tiles. Framebuffer tiles from 128 (up to 720 tiles in every mode):
 *   row-doubled: two RAM + two VRAM copies (W/4 x 9 tiles each); column-doubled: one of each (W/4 x 18). */
#define TILE_FB0   128
#define NT0        0xE000
#define VTOP       (VIEW_ROW0 * 8)
static uint16_t dma_chunk = 5632;              /* bytes per VBlank (H40 ~7.7 KB of VBlank DMA, H32 ~6.3 KB, minus the HUD) */
#define DMA_CHUNK  dma_chunk
static uint16_t nbuf, tile_fb1, nt1, view_trows, mode;
#define NBUF       nbuf
#define TCOLS      FB_TCOLS
#define TILE_FB1   tile_fb1
#define NT1        nt1

static uint8_t fbuf[FB_MAX];        /* view name table rows with per-tile palettes */
volatile uint16_t vints;
static const uint8_t *volatile dma_src;   /* buffer being sent, 0 = idle (the POINTER is volatile) */
static volatile uint16_t dma_pos;
static volatile uint8_t shown;            /* VRAM copy currently displayed */

/* bench: the test harness (or holding B on the title) drives a fixed input script */
volatile uint16_t bench_req;
volatile uint16_t bench_joy;
volatile uint32_t bench_frames, bench_vints;
volatile uint16_t bench_done;
volatile uint16_t cur_buf;
volatile uint16_t frame_segs, frame_nodes, frame_cols, frame_anchors;

static void vram_cmd(uint16_t addr) { *(volatile uint32_t *)0xC00004 = 0x40000000UL | ((uint32_t)(addr & 0x3FFF) << 16) | (addr >> 14); }

/* rows shown twice: hint.s scrolls plane A up by one row every 2 lines inside the view */
extern void hint_a(void), hint_b(void);
static volatile uint8_t hint_on;

static void vint_cb(void)
{
    vints++;
    *(volatile uint32_t *)0xC00004 = 0x40000010UL;
    *(volatile uint16_t *)0xC00000 = 0;
    if (hint_on) { SYS_setHIntCallback(hint_a); *(volatile uint16_t *)0xC00004 = 0x8014; }   /* H-int back on for the next frame */
    HUD_VBlank();
    if (dma_src) {
        const uint16_t n = (FB_BYTES - dma_pos) > DMA_CHUNK ? DMA_CHUNK : (FB_BYTES - dma_pos);
        const uint16_t dst = (shown ? TILE_FB0 : TILE_FB1) * 32 + dma_pos;
        DMA_doDma(DMA_VRAM, (void *)(dma_src + dma_pos), dst, n / 2, 2);
        dma_pos += n;
        if (dma_pos >= FB_BYTES) {
            shown ^= 1;
            *(volatile uint16_t *)0xC00004 = 0x8200 | ((shown ? NT1 : NT0) >> 10);
            dma_src = 0;
        }
    }
}

/* switch the screen mode (detail level): resolution H40/H32, row- or column-doubled view */
#ifndef START_CROP
#define START_CROP 0
#endif
static uint16_t crop = START_CROP;                         /* side crop: tiles removed on each side (0, 2, 4) */
static void set_mode(uint16_t m)
{
    while (dma_src) {}
    SYS_disableInts();
#ifdef DREAD_ROW_ONLY
    m &= ~1u;
#endif
    mode = m;
    const uint16_t h40 = !(m & 2), colb = (m & 1) ? 2 : 1;
    R_SetMode(colb, h40 ? 40 : 32, crop);
    if (h40) VDP_setScreenWidth320(); else VDP_setScreenWidth256();
    *(volatile uint16_t *)0xC00004 = 0x8F02;      /* auto-increment 2 */
    view_trows = VIEW_H / 8;
    nbuf = colb == 2 ? 1 : 2;
    tile_fb1 = nbuf == 2 ? TILE_FB0 + TCOLS * view_trows : TILE_FB0;
    nt1 = nbuf == 2 ? 0xA000 : 0xE000;
    /* palette 0: the view */
    *(volatile uint32_t *)0xC00004 = 0xC0000000UL;
    for (int i = 0; i < 16; i++) *(volatile uint16_t *)0xC00000 = md_palette[0][i];
    /* name tables: view rows point at the framebuffer tiles, column-major */
    for (int b = 0; b < 2; b++) {
        const uint16_t nt = b ? 0xA000 : NT0, base = (b && nbuf == 2) ? TILE_FB1 : TILE_FB0;
        for (int ty = 0; ty < 32; ty++) {
            vram_cmd(nt + ty * 128);
            for (int tx = 0; tx < 64; tx++) {
                uint16_t v = 0;
                const uint16_t r = colb == 2 ? ty - VIEW_ROW0 : ty - VIEW_ROW0;   /* row-doubled: tile rows 0..8 (vscroll repeats lines) */
                if (tx >= crop && tx < crop + TCOLS && ty >= VIEW_ROW0 && r < view_trows) v = base + (tx - crop) * view_trows + r;
                *(volatile uint16_t *)0xC00000 = v;
            }
        }
    }
    *(volatile uint32_t *)0xC00004 = 0x40000010UL;   /* VSRAM 0 */
    *(volatile uint16_t *)0xC00000 = 0;
    *(volatile uint16_t *)0xC00004 = 0x8200 | (NT0 >> 10);
    shown = 0; cur_buf = 0;
    hint_on = colb == 1;
    VDP_setHIntCounter(1);
    *(volatile uint16_t *)0xC00004 = hint_on ? 0x8014 : 0x8004;
    HUD_SetLayout(h40 ? 4 : 0, h40 ? 0 : -32);
    dma_chunk = h40 ? 5632 : 4608;
    SYS_enableInts();
}

/* ---- doors: B (or C+B) opens the door line in front; manual doors close again after ~4 s */
static int16_t door_target[64];
static uint16_t door_wait[64];
static uint8_t door_manual[64];
static uint16_t prev_joy;
static int door_index(uint16_t sector)
{
    for (int d = 0; d < map_ndoors && d < 64; d++) if (map_doors[d].sector == sector) return d;
    return -1;
}
static void door_open(int d, int manual)
{
    door_target[d] = map_doors[d].open_ceil;
    door_wait[d] = manual ? 4 * 60 : 0xFFFF;
    door_manual[d] = (uint8_t)manual;
}

static View view;
static int16_t cur_floor;

static int blocked(int16_t x, int16_t y)
{
    const int16_t R = 16;
    const MapSector *here = &map_sectors[map_subs[R_PointInSub(x, y)].sector];
    const int16_t gx = (int16_t)((x - map_bm[0]) >> 7), gy = (int16_t)((y - map_bm[1]) >> 7);
    if (gx < 0 || gy < 0 || gx >= map_bm[2] || gy >= map_bm[3]) return 1;
    const uint16_t cell = (uint16_t)(gy * map_bm[2] + gx);
    for (uint16_t k = map_bm_off[cell]; k < map_bm_off[cell + 1]; k++) {
        const MapLine *l = &map_lines[map_bm_list[k]];
        const int16_t ax = map_verts[l->v1][0], ay = map_verts[l->v1][1];
        const int16_t bx = map_verts[l->v2][0], by = map_verts[l->v2][1];
        if ((ax < bx ? ax : bx) > x + R || (ax > bx ? ax : bx) < x - R) continue;
        if ((ay < by ? ay : by) > y + R || (ay > by ? ay : by) < y - R) continue;
        int solid = (l->back == NO_MAP_SECTOR) || (l->flags & 1);
        if (!solid) {
            const MapSector *f = &map_sectors[l->front], *b = &map_sectors[l->back];
            const int16_t hi = f->floor > b->floor ? f->floor : b->floor;
            const int16_t lo = f->ceil < b->ceil ? f->ceil : b->ceil;
            if (hi - here->floor > 24 || lo - hi < 56) solid = 1;
        }
        if (!solid) continue;
        /* distance^2 from (x,y) to segment ab */
        const int32_t dx = bx - ax, dy = by - ay, px = x - ax, py = y - ay;
        const int32_t len2 = dx * dx + dy * dy;
        if (!len2) continue;
        int32_t t = px * dx + py * dy;
        int32_t cx, cy;
        if (t <= 0) { cx = ax; cy = ay; }
        else if (t >= len2) { cx = bx; cy = by; }
        else { cx = ax + (int32_t)((int64_t)dx * t / len2); cy = ay + (int32_t)((int64_t)dy * t / len2); }
        const int32_t ex = x - cx, ey = y - cy;
        if (ex * ex + ey * ey < (int32_t)R * R) return 1;
    }
    return 0;
}

#ifdef DREAD_COMBAT
int ActorBlocked(int16_t x, int16_t y) { return blocked(x, y); }
#endif

static volatile uint16_t exit_req;              /* 1 = exit, 2 = secret exit */
static void use_line(void)
{
    /* a point 40 units ahead; activate the closest special line within 40 units of it */
    const uint16_t a = view.angle >> 6;
    const int32_t px = (view.x >> 16) + ((40 * (int32_t)sintab[(a + 256) & 1023]) >> 14);
    const int32_t py = (view.y >> 16) + ((40 * (int32_t)sintab[a]) >> 14);
    int best = -1; int32_t bd = 40 * 40;
    for (uint16_t i = 0; i < map_counts[5]; i++) {
        const MapLine *l = &map_lines[i];
        if (!l->special) continue;
        const int32_t ax = map_verts[l->v1][0], ay = map_verts[l->v1][1], bx = map_verts[l->v2][0], by = map_verts[l->v2][1];
        const int32_t dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
        if (!len2) continue;
        const int32_t t = (px - ax) * dx + (py - ay) * dy;
        int32_t cx, cy;
        if (t <= 0) { cx = ax; cy = ay; } else if (t >= len2) { cx = bx; cy = by; }
        else { cx = ax + (int32_t)((int64_t)dx * t / len2); cy = ay + (int32_t)((int64_t)dy * t / len2); }
        const int32_t d2 = (px - cx) * (px - cx) + (py - cy) * (py - cy);
        if (d2 < bd) { bd = d2; best = i; }
    }
    if (best < 0) return;
    const MapLine *l = &map_lines[best];
    const uint16_t sp = l->special;
    if (sp == 11) { exit_req = 1; return; }          /* exit switch */
    if (sp == 51) { exit_req = 2; return; }          /* secret exit switch */
    if ((sp == 1 || (sp >= 26 && sp <= 28) || (sp >= 31 && sp <= 34) || sp == 117 || sp == 118) && l->back != NO_MAP_SECTOR) {
        const int d = door_index(l->back);
        if (d >= 0) door_open(d, sp == 1 || (sp >= 26 && sp <= 28) || sp == 117);
    } else if (l->tag) {
        for (int d = 0; d < map_ndoors && d < 64; d++)
            if (map_sector_tag[map_doors[d].sector] == (int16_t)l->tag) door_open(d, 0);
    }
}

static void doors_tick(uint16_t dt)
{
    const int16_t psec = (int16_t)map_subs[R_PointInSub(view.x >> 16, view.y >> 16)].sector;
    for (int d = 0; d < map_ndoors && d < 64; d++) {
        MapSector *s = &map_sectors[map_doors[d].sector];
        const int16_t tgt = door_target[d];
        if (s->ceil < tgt) { s->ceil += 2 * dt; if (s->ceil > tgt) s->ceil = tgt; }
        else if (s->ceil > tgt) {
            if (psec == (int16_t)map_doors[d].sector) { door_target[d] = map_doors[d].open_ceil; continue; }   /* never close on the player */
            s->ceil -= 2 * dt; if (s->ceil < tgt) s->ceil = tgt;
        } else if (door_manual[d] && door_wait[d] != 0xFFFF) {
            if (door_wait[d] > dt) door_wait[d] -= dt;
            else { door_wait[d] = 0xFFFF; door_target[d] = s->floor; }
        }
    }
}

/* walk-over exit lines (52 exit, 124 secret exit) crossed by the move (x0,y0) -> (x1,y1) */
static void check_walk_exits(int16_t x0, int16_t y0, int16_t x1, int16_t y1)
{
    const int16_t gx = (int16_t)((x1 - map_bm[0]) >> 7), gy = (int16_t)((y1 - map_bm[1]) >> 7);
    if (gx < 0 || gy < 0 || gx >= map_bm[2] || gy >= map_bm[3]) return;
    const uint16_t cell = (uint16_t)(gy * map_bm[2] + gx);
    for (uint16_t k = map_bm_off[cell]; k < map_bm_off[cell + 1]; k++) {
        const MapLine *l = &map_lines[map_bm_list[k]];
        if (l->special != 52 && l->special != 124) continue;
        const int32_t ax = map_verts[l->v1][0], ay = map_verts[l->v1][1], bx = map_verts[l->v2][0], by = map_verts[l->v2][1];
        const int32_t s0 = (bx - ax) * (y0 - ay) - (by - ay) * (x0 - ax), s1 = (bx - ax) * (y1 - ay) - (by - ay) * (x1 - ax);
        if ((s0 < 0) == (s1 < 0)) continue;
        const int32_t t0 = (x1 - x0) * (ay - y0) - (y1 - y0) * (ax - x0), t1 = (x1 - x0) * (by - y0) - (y1 - y0) * (bx - x0);
        if ((t0 < 0) == (t1 < 0)) continue;
        exit_req = l->special == 124 ? 2 : 1;
    }
}

static void try_move(int32_t mx, int32_t my)
{
    const int32_t ox = view.x, oy = view.y;
    const int32_t nx = view.x + mx, ny = view.y + my;
    if (!blocked(nx >> 16, ny >> 16)) { view.x = nx; view.y = ny; }
    else if (!blocked(nx >> 16, view.y >> 16)) { view.x = nx; }
    else if (!blocked(view.x >> 16, ny >> 16)) { view.y = ny; }
    if (view.x != ox || view.y != oy) check_walk_exits((int16_t)(ox >> 16), (int16_t)(oy >> 16), (int16_t)(view.x >> 16), (int16_t)(view.y >> 16));
}

/* bench route: (vblanks, buttons) */
static const uint16_t bench_script[][2] = {
    {60, 0}, {120, BUTTON_UP}, {60, BUTTON_LEFT}, {150, BUTTON_UP}, {90, BUTTON_RIGHT}, {180, BUTTON_UP},
    {120, BUTTON_RIGHT | BUTTON_UP}, {120, BUTTON_UP}, {200, BUTTON_LEFT}, {150, BUTTON_UP}, {0, 0}
};

/* in-game menu (START): detail levels switch at once, the renderer adapts */
static void menu_draw(uint16_t sel)
{
    static const char *const res[2] = { "H40 (320)", "H32 (256)" }, *const det[2] = { "LINHAS DUPLICADAS ", "COLUNAS DUPLICADAS" };
    static const char *const crp[3] = { "LARGURA TOTAL ", "-2 TILES/LADO ", "-4 TILES/LADO " };
    char l[5][36];
    sprintf(l[0], "%c TELA:    %s", sel == 0 ? '>' : ' ', res[(mode >> 1) & 1]);
#ifdef DREAD_ROW_ONLY
    (void)det;
    sprintf(l[1], "%c DETALHE: LINHAS", sel == 1 ? '>' : ' ');
#else
    sprintf(l[1], "%c DETALHE: %s", sel == 1 ? '>' : ' ', det[mode & 1]);
#endif
    sprintf(l[2], "%c RECORTE: %s", sel == 2 ? '>' : ' ', crp[crop >> 1]);
    sprintf(l[3], "%c MUSICA:  %s", sel == 3 ? '>' : ' ', music_on ? "LIGADA   " : "DESLIGADA");
    sprintf(l[4], "%c VOLTAR", sel == 4 ? '>' : ' ');
    SYS_disableInts();
    VDP_clearPlane(WINDOW, TRUE);
    VDP_drawTextBG(WINDOW, "MODOS DE VIDEO", 1, 3);
    for (int i = 0; i < 5; i++) VDP_drawTextBG(WINDOW, l[i], 1, 5 + i);
    VDP_drawTextBG(WINDOW, "lados troca, START sai", 1, 11);
    SYS_enableInts();
}
static void menu(void)
{
    uint16_t sel = 0, pj = BUTTON_START;
    while (dma_src) {}
    SYS_disableInts();
    VDP_setTextPalette(PAL3);
    VDP_setWindowVPos(FALSE, 13);
    SYS_enableInts();
    menu_draw(sel);
    for (;;) {
        { const uint16_t v0 = vints; while (vints == v0) {} }
        JOY_update();
        const uint16_t j = JOY_readJoypad(JOY_1), e = j & ~pj;
        pj = j;
        if (e & BUTTON_START) break;
        if (e & BUTTON_UP) { sel = (sel + 4) % 5; menu_draw(sel); }
        if (e & BUTTON_DOWN) { sel = (sel + 1) % 5; menu_draw(sel); }
        if (e & (BUTTON_LEFT | BUTTON_RIGHT | BUTTON_A | BUTTON_C)) {
            if (sel == 4) break;
            if (sel == 3) {
#ifndef DREAD_NO_MUSIC
                music_on ^= 1;
                if (music_on) XGM2_play(MAP_MUSIC); else XGM2_stop();
#endif
                menu_draw(sel);
                continue;
            }
            if (sel == 2) { crop = (uint16_t)((crop + ((e & BUTTON_LEFT) ? 4 : 2)) % 6); set_mode(mode); }
            else set_mode(mode ^ (sel == 0 ? 2 : 1));
            SYS_disableInts(); VDP_setWindowVPos(FALSE, 13); SYS_enableInts();
            menu_draw(sel);
        }
    }
    SYS_disableInts();
    VDP_clearPlane(WINDOW, TRUE);
    VDP_setWindowVPos(FALSE, 0);
    SYS_enableInts();
    prev_joy = BUTTON_START;
}

#ifdef DREAD_EPISODE
#ifdef DREAD_NO_MUSIC
static uint16_t selected_map;
#endif

enum TitleScreen { TITLE_ART, TITLE_MENU, TITLE_LEVELS };
enum TitleChoice { TITLE_NEW_GAME, TITLE_SELECT_LEVEL, TITLE_BENCHMARK };

static const char *const title_items[] = { "NEW GAME", "SELECT LEVEL", "BENCHMARK" };
static const char *const title_levels[] = {
    "E1M1  HANGAR", "E1M2  NUCLEAR PLANT", "E1M3  TOXIN REFINERY",
    "E1M4  COMMAND CONTROL", "E1M5  PHOBOS LAB", "E1M6  CENTRAL PROCESSING",
    "E1M7  COMPUTER STATION", "E1M8  PHOBOS ANOMALY", "E1M9  MILITARY BASE"
};

static void draw_title_menu(enum TitleScreen screen, uint16_t cursor)
{
    SYS_disableInts();
    VDP_clearPlane(BG_A, TRUE);
    VDP_setHilightShadow(screen != TITLE_ART);
    VDP_setTextPalette(PAL3);
    VDP_setTextPriority(TRUE);
    if (screen == TITLE_ART) {
        VDP_drawTextBG(BG_A, "PRESS START", 14, 23);
    } else {
        const bool levels = screen == TITLE_LEVELS;
        const char *const *items = levels ? title_levels : title_items;
        const uint16_t count = levels ? sizeof(title_levels) / sizeof(*title_levels)
                                      : sizeof(title_items) / sizeof(*title_items);
        const uint16_t x = levels ? 8 : 14, y = levels ? 10 : 13;
        if (levels) VDP_drawTextBG(BG_A, "SELECT LEVEL", 14, 8);
        for (uint16_t i = 0; i < count; i++)
            VDP_drawTextBG(BG_A, items[i], x, y + i);
        VDP_drawTextBG(BG_A, ">", x - 2, y + cursor);
        VDP_drawTextBG(BG_A, "A / START: OK    B: BACK", 8, 22);
    }
    SYS_enableInts();
}

static void title(void)
{
    enum TitleScreen screen = TITLE_ART;
    uint16_t cursor = 0, previous = 0;
    HUD_ShowOpening();
    draw_title_menu(screen, cursor);
    while (!bench_req) {
        const uint16_t frame = vints;
        while (vints == frame && !bench_req) {}
        JOY_update();
        const uint16_t joy = JOY_readJoypad(JOY_1);
        const uint16_t pressed = joy & ~previous;
        previous = joy;
        if (screen == TITLE_ART) {
            if (!(pressed & (BUTTON_START | BUTTON_A | BUTTON_B | BUTTON_C))) continue;
            screen = TITLE_MENU;
        } else if (pressed & BUTTON_B) {
            cursor = screen == TITLE_LEVELS ? TITLE_SELECT_LEVEL : 0;
            screen = screen == TITLE_LEVELS ? TITLE_MENU : TITLE_ART;
        } else if (pressed & (BUTTON_START | BUTTON_A | BUTTON_C)) {
            if (screen == TITLE_LEVELS) {
                selected_map = cursor;
                break;
            }
            if (cursor != TITLE_SELECT_LEVEL) {
                selected_map = 0;
                bench_req = cursor == TITLE_BENCHMARK;
                break;
            }
            screen = TITLE_LEVELS;
            cursor = 0;
        } else if (pressed & (BUTTON_UP | BUTTON_DOWN)) {
            const uint16_t count = screen == TITLE_LEVELS
                ? sizeof(title_levels) / sizeof(*title_levels)
                : sizeof(title_items) / sizeof(*title_items);
            cursor = (cursor + ((pressed & BUTTON_UP) ? count - 1 : 1)) % count;
        } else continue;
        draw_title_menu(screen, cursor);
    }
    while (!bench_req) {
        JOY_update();
        if (!(JOY_readJoypad(JOY_1) & (BUTTON_START | BUTTON_A | BUTTON_C))) break;
    }
    HUD_ClearOpening();
}
#else
static void title(void)
{
    VDP_clearPlane(BG_B, TRUE);
    VDP_drawText(ROM_NAME, 4, 6);
    VDP_drawText("Renderer estilo Dread:", 4, 9);
    VDP_drawText("paredes por coluna, chao/teto", 4, 10);
    VDP_drawText("MAPA: " DREAD_MAP_LABEL, 4, 11);
#ifdef DREAD_COMBAT
    VDP_drawText("Teste de IA e tiros da pistola.", 4, 12);
#else
    VDP_drawText("Objetos e monstros estaticos.", 4, 12);
#endif
    VDP_drawText("Mede FPS. START no jogo: menu", 4, 13);
    VDP_drawText("de modos (H40/H32, linhas ou", 4, 14);
    VDP_drawText("colunas duplicadas).", 4, 15);
    VDP_drawText("Cima/baixo anda, lados gira,", 4, 16);
    VDP_drawText("C+lados anda de lado,", 4, 17);
    VDP_drawText("A atira, B abre portas.", 4, 18);
    VDP_drawText("aperte START ou aguarde", 4, 20);
    VDP_drawText("15 segundos", 4, 21);
    const uint16_t t0 = vints;
    while ((uint16_t)(vints - t0) < 15 * 60) {
        JOY_update();
        const uint16_t j = JOY_readJoypad(JOY_1);
        if (j & BUTTON_START) break;
        if (j & BUTTON_B) { bench_req = 1; break; }
        if (bench_req) break;
    }
    VDP_clearPlane(BG_B, TRUE);
}
#endif

static void place_player(void)
{
    view.x = (int32_t)map_start[0] << 16; view.y = (int32_t)map_start[1] << 16;
    view.angle = (uint16_t)((int32_t)map_start[2] * 65536 / 360);
    cur_floor = map_sectors[map_subs[R_PointInSub(map_start[0], map_start[1])].sector].floor;
    view.z = cur_floor + 41;
}

/* (re)load the selected map: geometry state, doors, monsters, items */
static void start_level(void)
{
#ifdef DREAD_EPISODE
    dread_map = &episode_maps[selected_map];
#endif
    R_Init();
#ifdef DREAD_COMBAT
    Actors_Init();
#endif
    for (int d = 0; d < map_ndoors && d < 64; d++) { door_target[d] = map_sectors[map_doors[d].sector].ceil; door_wait[d] = 0xFFFF; door_manual[d] = 0; }
    exit_req = 0;
}

#ifdef DREAD_COMBAT
/* item pickups in the player's subsector (flags bits 8-15 = item code from conv.py) */
static void pickups(HudState *hud, uint16_t psub)
{
    const int16_t px = (int16_t)(view.x >> 16), py = (int16_t)(view.y >> 16);
    for (uint16_t ti = map_sub_things[psub]; ti < map_sub_things[psub + 1]; ti++) {
        const MapThing *t = &map_things[ti];
        const uint16_t code = t->flags >> 8;
        if ((t->flags & THING_MONSTER) || !code || Thing_Taken(ti)) continue;
        if ((px - t->x) * (px - t->x) + (py - t->y) * (py - t->y) > 24 * 24) continue;
        uint16_t *hp = &hud->health, *ar = &hud->armor, *am = &hud->ammo[0];
        switch (code) {
        case 1: if (*am >= 200) continue; *am = *am + 10 > 200 ? 200 : *am + 10; break;          /* clip */
        case 2: if (*am >= 200) continue; *am = *am + 50 > 200 ? 200 : *am + 50; break;          /* box of bullets */
        case 3: if (*hp >= 100) continue; *hp = *hp + 10 > 100 ? 100 : *hp + 10; break;          /* stimpack */
        case 4: if (*hp >= 100) continue; *hp = *hp + 25 > 100 ? 100 : *hp + 25; break;          /* medikit */
        case 5: *hp = *hp + 1 > 200 ? 200 : *hp + 1; break;                                      /* health bonus */
        case 6: *ar = *ar + 1 > 200 ? 200 : *ar + 1; break;                                      /* armor bonus */
        case 7: if (*ar >= 100) continue; *ar = 100; break;                                      /* green armor */
        case 8: if (*ar >= 200) continue; *ar = 200; break;                                      /* blue armor */
        case 9: *hp = *hp + 100 > 200 ? 200 : *hp + 100; break;                                  /* soulsphere */
        case 10: *am = *am + 10 > 200 ? 200 : *am + 10; break;                                   /* backpack */
        default: continue;                                                                       /* keys, weapons: later */
        }
        hud->ammo_cur = hud->ammo[0];
        Thing_Take(ti);
        HUD_Draw(hud);
    }
}
#endif

int main(bool hard)
{
    (void)hard;
    SYS_disableInts();
    SYS_setVIntCallback(vint_cb);
    SYS_setHIntCallback(hint_a);
    SYS_enableInts();
#ifndef DREAD_NO_MUSIC
    XGM2_loadDriver(TRUE);
    if (music_on) XGM2_play(bgm_intro);
#endif
    title();
    start_level();
#if !defined(DREAD_EPISODE) && !defined(DREAD_TEXT_TITLE)
    HUD_Opening();
#endif
#ifndef DREAD_NO_MUSIC
    if (music_on) XGM2_play(MAP_MUSIC);
#endif
    HUD_Init(HUD_ROW0);
    VDP_setHInterrupt(TRUE);
    set_mode(START_MODE);
    HudState hud = { 100, 0, 50, {50, 0, 0, 0}, {200, 50, 50, 300}, 1, 0, 0 };
    HUD_Draw(&hud);
    uint16_t face_t = 0, weap_t = 0, weap_step = 0, bob = 0;
    static const uint8_t weap_seq[4][2] = { {1, 10}, {2, 7}, {3, 8}, {0, 0} };   /* frame, vblanks (Doom 6/4/5 tics) */

    place_player();

    uint16_t last = vints, fps_v0 = vints, fps_n = 0;
    uint16_t script_i = 0, script_t = 0;
    uint32_t bench_v0 = 0;
    char txt[40];
    if (bench_req) bench_v0 = vints;
    for (;;) {
        uint16_t now = vints;
        uint16_t dt = now - last; last = now;
        if (dt > 8) dt = 8;
        if (bench_req && !bench_done) dt = 4;    /* bench: same camera path at any speed (frames are comparable) */
        JOY_update();
        uint16_t j = JOY_readJoypad(JOY_1);
#ifdef FREEZE_AT
        if (bench_frames >= FREEZE_AT) { dt = 0; bench_done = 3; }   /* test builds: keep rendering one fixed view */
#endif
        if (bench_req && !bench_done) {
            script_t += dt;
            while (bench_script[script_i][0] && script_t >= bench_script[script_i][0]) { script_t -= bench_script[script_i][0]; script_i++; }
            j = bench_script[script_i][1];
            bench_joy = j;
            if (!bench_script[script_i][0]) {
                bench_done = 1; bench_vints = vints - bench_v0;
            }
        }
        if ((j & BUTTON_START) && !(prev_joy & BUTTON_START) && !bench_req) { prev_joy = j; menu(); last = vints; continue; }
        if ((j & BUTTON_B) && !(prev_joy & BUTTON_B)) use_line();
        prev_joy = j;
        doors_tick(dt);
        /* turn / move (per vblank speeds, Doom-like) */
        const int strafe = (j & BUTTON_C) != 0;
        const int32_t speed = 0x30000;     /* map units per vblank, 16.16 */
        /* pistol: A fires (Doom timing), the status bar counts the bullets */
        if (weap_step == 0 && (j & BUTTON_A) && hud.ammo[0]) {
            weap_step = 1; weap_t = weap_seq[0][1]; HUD_WeaponFrame(weap_seq[0][0]);
#ifdef DREAD_COMBAT
            Actors_Fire(&view, 1, 5);              /* pistol: 5 x (1..3) */
#endif
            hud.ammo[0]--; hud.ammo_cur = hud.ammo[0]; HUD_Draw(&hud);
        } else if (weap_step) {
            if (weap_t > dt) weap_t -= dt;
            else { HUD_WeaponFrame(weap_seq[weap_step][0]); weap_t = weap_seq[weap_step][1]; weap_step = weap_seq[weap_step][1] ? weap_step + 1 : 0; }
        }
        /* face looks around */
        face_t += dt;
        if (face_t > 90) { face_t = 0; hud.face = (int16_t)((hud.face + 1 + (vints & 1)) % 3); HUD_Draw(&hud); }
        if (!strafe) {
            if (j & BUTTON_LEFT) view.angle += 400 * dt;
            if (j & BUTTON_RIGHT) view.angle -= 400 * dt;
        }
        const uint16_t a = view.angle >> 6;
        const int32_t cs = sintab[(a + 256) & 1023], sn = sintab[a];
        int32_t fwd = 0, side = 0;
        if (j & BUTTON_UP) fwd = speed * dt;
        if (j & BUTTON_DOWN) fwd = -speed * dt;
        if (strafe && (j & BUTTON_LEFT)) side = -speed * dt;
        if (strafe && (j & BUTTON_RIGHT)) side = speed * dt;
        if (fwd || side) {
            bob += dt;
            const int16_t sx = sintab[(bob * 12) & 1023] >> 11, sy = sintab[(bob * 24) & 1023] >> 11;
            HUD_WeaponBob(sx, sy < 0 ? -sy : sy);
        }
        if (fwd || side) {
            const int32_t mx = ((fwd >> 8) * cs + (side >> 8) * sn) >> 6;
            const int32_t my = ((fwd >> 8) * sn - (side >> 8) * cs) >> 6;
            try_move(mx, my);
        }
        cur_floor = map_sectors[map_subs[R_PointInSub(view.x >> 16, view.y >> 16)].sector].floor;
        view.z = cur_floor + 41;

#ifdef DREAD_COMBAT
        {
            static ActorPlayer pl;
            const uint16_t health = hud.health, armor = hud.armor;
            pl.x = (int16_t)(view.x >> 16); pl.y = (int16_t)(view.y >> 16); pl.z = view.z;
            pl.sub = (uint16_t)R_PointInSub(pl.x, pl.y);
            pl.health = &hud.health; pl.armor = &hud.armor;
            if (!bench_req) Actors_Tick(&pl, dt);
            pickups(&hud, pl.sub);
            if (!hud.health) {                          /* dead: message, then the map starts again */
                HUD_Text(1, "VOCE MORREU");
                const uint16_t t0 = vints;
                while ((uint16_t)(vints - t0) < 120) {}
                HUD_Text(1, "");
                start_level(); place_player();
                hud.health = 100; hud.armor = 0; hud.ammo[0] = 50; hud.ammo_cur = 50;
                HUD_Draw(&hud);
                last = vints;
                continue;
            }
            if (health != hud.health || armor != hud.armor) HUD_Draw(&hud);
        }
#endif
        if (exit_req) {                                 /* level done: next map (E1M8 ends the episode) */
#ifdef DREAD_EPISODE
            const uint16_t secret = exit_req == 2;
            char msg[32];
            sprintf(msg, "E1M%u CONCLUIDA", selected_map + 1);
            HUD_Text(1, msg);
            const uint16_t t0 = vints;
            while ((uint16_t)(vints - t0) < 120) {}
            HUD_Text(1, "");
            if (selected_map == 7) SYS_hardReset();     /* end of the episode: back to the title */
            selected_map = secret ? 8 : (selected_map == 8 ? 3 : selected_map + 1);
            start_level(); place_player();
#ifndef DREAD_NO_MUSIC
            if (music_on) XGM2_play(MAP_MUSIC);
#endif
            last = vints;
            continue;
#else
            exit_req = 0;
#endif
        }
        /* render into the free RAM buffer, then hand it to the VBlank DMA */
        if (NBUF == 1) while (dma_src) {}   /* one buffer: the previous frame must be out first */
        uint8_t *const fb = fbuf + (cur_buf ? FB_BYTES : 0);
        R_RenderView(&view, fb);
        frame_segs = rstats.segs_drawn; frame_nodes = rstats.nodes_visited; frame_cols = rstats.col_visits; frame_anchors = rstats.anchors;
        while (dma_src) {}
        dma_pos = 0; dma_src = fb;
        cur_buf ^= (NBUF - 1);
        if (bench_req && !bench_done) bench_frames++;

        if (++fps_n == 16) {
            const uint16_t dv = vints - fps_v0; fps_v0 = vints; fps_n = 0;
            const uint16_t f10 = dv ? (uint16_t)(16UL * 600 / dv) : 0;
            sprintf(txt, "FPS %2u.%u  SEGS %3u ", f10 / 10, f10 % 10, frame_segs);
            HUD_Text(0, txt);
        }
        if (bench_done == 1) {
            const uint16_t f100 = (uint16_t)(bench_frames * 6000UL / (bench_vints ? bench_vints : 1));
            sprintf(txt, "BENCH %u quadros %u.%u%u FPS", (uint16_t)bench_frames, f100 / 100, (f100 / 10) % 10, f100 % 10);
            HUD_Text(1, txt);
            bench_done = 2;
        }
    }
    return 0;
}
