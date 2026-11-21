/* DREAD-MD: opening image, Doom status bar (Claudio's HUD from the WAD, as in R128/Manifold) and the
 * pistol view sprite. Mega Drive only. */
#include <genesis.h>
#include "render.h"
#include "game_hud.h"
#include "hud_assets.h"
#ifdef DREAD_EPISODE
#include "image_tiles.h"
#endif

extern const uint16_t weap_pal[16], weap_x, weap_y, weap_tiles, weap_nframes, weap_npieces;
extern const uint8_t weap_piece[][4];
extern const uint32_t weap_data[];
extern const uint16_t title_ntiles, title_pal[64], title_mapa[1120], title_mapb[1120];
extern const uint32_t title_tiles[];

#define TILE_HUD    1024                       /* 0x8000: bar tiles, then the 16-tile face slot */
#define TILE_FACE   (TILE_HUD + HUDW_NTILES)
#define TILE_WEAP   848                        /* right after the framebuffer tiles (128 + 720); up to 176 tiles before the HUD at 1024 */
#define TILE_TITLE  112                        /* the opening tiles end below the SGDK font at the top of tile VRAM */
#define BGB         0xC000                     /* SGDK 2.x plane B */
#define BGA         0xE000
#define SLIST       0xF400

static inline void vram_addr(uint16_t a) { *(volatile uint32_t *)0xC00004 = 0x40000000UL | ((uint32_t)(a & 0x3FFF) << 16) | (a >> 14); }
static inline void vram_w(uint16_t v) { *(volatile uint16_t *)0xC00000 = v; }
static inline void cram_set(uint16_t idx, const uint16_t *src, uint16_t n)
{
    *(volatile uint32_t *)0xC00004 = 0xC0000000UL | ((uint32_t)(idx * 2) << 16);
    while (n--) *(volatile uint16_t *)0xC00000 = *src++;
}
static void vram_copy32(uint16_t dst_tile, const uint32_t *src, uint16_t ntiles)
{
    vram_addr(dst_tile * 32);
    for (uint32_t i = 0; i < (uint32_t)ntiles * 8; i++) {
        const uint32_t w = src[i];
        vram_w((uint16_t)(w >> 16)); vram_w((uint16_t)w);
    }
}

void HUD_ShowOpening(void)
{
    SYS_disableInts();
    VDP_setEnable(FALSE);
    VDP_setScreenWidth320();
    VDP_setHorizontalScroll(BG_A, 0);
    VDP_setHorizontalScroll(BG_B, 0);
    VDP_setAutoInc(2);
    cram_set(0, title_pal, 64);
    vram_copy32(TILE_TITLE, title_tiles, title_ntiles);
    for (int plane = 0; plane < 2; plane++) {
        const uint16_t *m = plane ? title_mapa : title_mapb;
        for (uint16_t y = 0; y < 32; y++) {
            vram_addr((plane ? BGA : BGB) + y * 128);
            for (uint16_t x = 0; x < 64; x++) {
                uint16_t v = 0;
                if (x < 40 && y < 28 && (plane == 0 || m[y * 40 + x])) { const uint16_t w = m[y * 40 + x]; v = (uint16_t)((w & 0xE000) | (TILE_TITLE + (w & 0x7FF))); }
                vram_w(v);
            }
        }
    }
    VDP_setEnable(TRUE);
    SYS_enableInts();
}

void HUD_ClearOpening(void)
{
    SYS_disableInts();
    VDP_setEnable(FALSE);
    VDP_setHilightShadow(FALSE);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
#ifdef DREAD_EPISODE
    /* The opening and gameplay reuse the same pattern memory. */
    VDP_fillTileData(0, TILE_TITLE, TILE_WEAP - TILE_TITLE, TRUE);
    VDP_setTextPalette(PAL0);
#endif
    VDP_setEnable(TRUE);
    SYS_enableInts();
}

/* Standalone demo opening. START (or 8 s) continues. */
void HUD_Opening(void)
{
    HUD_ShowOpening();
    extern volatile uint16_t vints, bench_req;
    const uint16_t t0 = vints;
    while ((uint16_t)(vints - t0) < 8 * 60 && !bench_req) {
        JOY_update();
        if (JOY_readJoypad(JOY_1) & BUTTON_START) break;
    }
    while (!bench_req) { JOY_update(); if (!(JOY_readJoypad(JOY_1) & BUTTON_START)) break; }   /* wait release */
    HUD_ClearOpening();
}

/* ---- status bar on plane B rows [row0, row0+4) */
#ifdef DREAD_EPISODE
static uint32_t face_frame[16*8];

static void unpack_tiles(uint32_t *dst, const uint16_t *refs, uint16_t count)
{
    while (count--) {
        memcpy(dst, image_tiles + (uint32_t)*refs++ * 8, 32);
        dst += 8;
    }
}
#endif

static uint16_t hud_row0, hud_col0 = HUD_COL0;
static int16_t weap_dx;
static int16_t cur_face = -1;
static uint16_t hud_nt[4][32];
static volatile uint8_t hud_dirty, face_dirty, sat_dirty;
static int16_t bob_x, bob_y;
static uint16_t txt_nt[2][40];
static volatile uint8_t txt_dirty;

void HUD_Init(uint16_t row0)
{
    hud_row0 = row0;
    SYS_disableInts();
    /* The text title clears plane B with DMA fill, which leaves increment 1. */
    VDP_setAutoInc(2);
    cram_set(16, weap_pal, 16);               /* PAL1: weapon */
    cram_set(32, hudw_fpal, 16);              /* PAL2: faces */
    cram_set(48, hudw_pal, 16);               /* PAL3: bar, digits, text */
#ifdef DREAD_EPISODE
    for (uint16_t i = 0; i < HUDW_NTILES; i++)
        vram_copy32(TILE_HUD + i, image_tiles + (uint32_t)hudw_tiles_refs[i] * 8, 1);
    vram_copy32(TILE_WEAP, weap_data, weap_tiles);
#else
    vram_copy32(TILE_HUD, &hudw_tiles[0][0], HUDW_NTILES);
    vram_copy32(TILE_WEAP, weap_data, weap_tiles);
#endif
    /* weapon sprites: one entry per piece, linked */
    vram_addr(SLIST);
    for (uint16_t i = 0; i < weap_npieces; i++) {
        const uint8_t *p = weap_piece[i];
        uint16_t tile = TILE_WEAP;
        for (uint16_t k = 0; k < i; k++) tile += weap_piece[k][2] * weap_piece[k][3];
        vram_w((uint16_t)(128 + weap_y + p[1] + VIEW_TOP_PX));
        vram_w((uint16_t)(((p[2] - 1) << 10) | ((p[3] - 1) << 8) | (i + 1 < weap_npieces ? i + 1 : 0)));
        vram_w((uint16_t)((1 << 13) | tile));     /* low priority: the high-priority status bar covers the weapon when it bobs down */
        vram_w((uint16_t)(128 + weap_x + p[0]));
    }
    SYS_enableInts();
}

void HUD_Draw(const HudState *st)
{
    uint16_t rows[4][32];
    for (int r = 0; r < 4; r++) for (int c = 0; c < 32; c++) rows[r][c] = hudw_bgmap[r][c];
    const uint16_t vals[3] = { st->ammo_cur, st->health, st->armor };
    const uint8_t cols[3] = { HUDW_AMMO_C, HUDW_HEALTH_C, HUDW_ARMOR_C };
    for (int w = 0; w < 3; w++) {
        const uint16_t v = vals[w] > 999 ? 999 : vals[w];
        const uint16_t d[3] = { v / 100, v / 10 % 10, v % 10 };
        const uint8_t lead[3] = { v >= 100, v >= 10, 1 };
        for (int r = 0; r < 3; r++) {
            for (int i = 0; i < 3; i++) if (lead[i]) rows[r][cols[w] + i] = hudw_big[w][i][r][d[i]];
            if (w) rows[r][cols[w] + 3] = hudw_pct[w - 1][r];
        }
    }
    const uint16_t mask = st->arms | (st->keys << 6);
    for (int k = 0; k < HUDW_NWID; k++) {
        const uint16_t v = ((mask >> hudw_wid_b0[k]) & 1) | (hudw_wid_b1[k] != 255 ? ((mask >> hudw_wid_b1[k]) & 1) << 1 : 0);
        rows[hudw_wid_row[k]][hudw_wid_col[k]] = hudw_wid_id[k][v];
    }
    for (int t = 0; t < 4; t++)
        for (int part = 0; part < 2; part++) {
            const uint16_t v = part ? st->maxammo[t] : st->ammo[t];
            const uint16_t d[3] = { v / 100, v / 10 % 10, v % 10 };
            const uint8_t lead[3] = { v >= 100, v >= 10, 1 };
            for (int i = 0; i < 3; i++) if (lead[i]) rows[HUDW_TABLE_R + t][HUDW_TABLE_C + part * 3 + i] = hudw_ysm[t][d[i]];
        }
    /* VRAM writes happen in the VBlank (HUD_VBlank): no interrupt masking during the frame,
       so the per-line scroll interrupt (row-doubled view) never misses a line */
    if (st->face != cur_face) {
#ifdef DREAD_EPISODE
        face_dirty = 0;
        __asm__ volatile ("" ::: "memory");
        unpack_tiles(face_frame, hudw_faces_refs + (uint16_t)st->face * 16, 16);
        __asm__ volatile ("" ::: "memory");
#endif
        cur_face = st->face;
        face_dirty = 1;
    }
    for (int r = 0; r < 4; r++)
        for (int c = 0; c < 32; c++) {
            const int face = r >= HUDW_FACE_R && r < HUDW_FACE_R + 4 && c >= HUDW_FACE_C && c < HUDW_FACE_C + HUDW_FACE_W;
            hud_nt[r][c] = face ? (uint16_t)(0x8000 | (2 << 13) | (TILE_FACE + (r - HUDW_FACE_R) * HUDW_FACE_W + (c - HUDW_FACE_C)))
                                : (uint16_t)(0x8000 | (3 << 13) | (TILE_HUD + rows[r][c]));
        }
    hud_dirty = 1;
}

/* ---- weapon: frame upload is requested here and done by the caller's VBlank (WEAP_VBlank) */
static volatile int16_t weap_req = -1;
void HUD_WeaponFrame(uint16_t f)
{
#ifdef DREAD_EPISODE
#endif
    weap_req = (int16_t)f;
}
void HUD_WeaponBob(int16_t dx, int16_t dy) { bob_x = dx; bob_y = dy; sat_dirty = 1; }

void HUD_Text(uint16_t line, const char *s)      /* line 0/1 = screen rows 25/26 */
{
    for (int i = 0; i < 40; i++) {
        const char ch = *s ? *s++ : ' ';
        txt_nt[line][i] = (uint16_t)((3 << 13) | 0x8000 | (TILE_FONT_INDEX + (ch - 32)));
    }
    txt_dirty |= (uint8_t)(1 << line);
}

/* called from the VBlank interrupt: every VRAM update of the HUD, face, weapon and text */
void HUD_VBlank(void)
{
    if (weap_req >= 0) {
        const uint16_t f = (uint16_t)weap_req; weap_req = -1;
        DMA_doDma(DMA_VRAM, (void *)(weap_data + (uint32_t)f * weap_tiles * 8), TILE_WEAP * 32, weap_tiles * 16, 2);
    }
    if (face_dirty) {
        face_dirty = 0;
#ifdef DREAD_EPISODE
        DMA_doDma(DMA_VRAM, face_frame, TILE_FACE * 32, 16 * 16, 2);
#else
        DMA_doDma(DMA_VRAM, (void *)&hudw_faces[cur_face][0][0], TILE_FACE * 32, 16 * 16, 2);
#endif
    }
    if (hud_dirty) {
        hud_dirty = 0;
        for (int r = 0; r < 4; r++) DMA_doDma(DMA_VRAM, hud_nt[r], BGB + (hud_row0 + r) * 128 + hud_col0 * 2, 32, 2);
    }
    for (int l = 0; l < 2; l++)
        if (txt_dirty & (1 << l)) { txt_dirty &= (uint8_t)~(1 << l); DMA_doDma(DMA_VRAM, txt_nt[l], BGB + (25 + l) * 128, 40, 2); }
    if (sat_dirty) {
        sat_dirty = 0;
        for (uint16_t i = 0; i < weap_npieces; i++) {
            const uint8_t *p = weap_piece[i];
            vram_addr(SLIST + i * 8);
            vram_w((uint16_t)(128 + weap_y + p[1] + VIEW_TOP_PX + bob_y));
            vram_addr(SLIST + i * 8 + 6);
            vram_w((uint16_t)(128 + weap_x + p[0] + bob_x + weap_dx));
        }
    }
}

/* screen mode change (ints disabled by the caller): bar column, weapon x offset */
void HUD_SetLayout(uint16_t col0, int16_t dx)
{
    hud_col0 = col0; weap_dx = dx;
    for (int r = 0; r < 4; r++) { vram_addr(BGB + (hud_row0 + r) * 128); for (int i = 0; i < 64; i++) vram_w(0); }
    hud_dirty = 1; sat_dirty = 1;
}
