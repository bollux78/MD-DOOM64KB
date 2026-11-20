/* DREAD-MD D01: Dread-style renderer test on Mega Drive, Doom E1M1 (shareware WAD).
 *
 * Screen: H32, view 128x112 logical pixels (each 2x1 screen pixels), 4bpp tiles in RAM,
 * double-buffered: the CPU renders one RAM buffer while the VBlank interrupt DMAs the
 * previous one into the hidden VRAM copy, then flips plane A's name table. */
#include <genesis.h>
#include "render.h"
#include "game_hud.h"

#ifdef ROM_TAG_3PAL
#define ROM_NAME   "DREAD-MD D01 E1M1 3PAL"
#else
#define ROM_NAME   "DREAD-MD D01 E1M1"
#endif
#define VIEW_TROWS (VIEW_H / 8)
/* SGDK 2.x VRAM: plane A name table at 0xE000 (we flip it with 0xA000), plane B 0xC000 (text),
 * window 0xD000, font right after the 16 system tiles. Our tiles start at tile 128 (0x1000). */
#define TILE_FB0   128
#define TILE_FB1   (TILE_FB0 + 32 * VIEW_TROWS)
#define NT0        0xE000
#define NT1        0xA000
#define DMA_CHUNK  2048

static uint8_t fbuf[2][FB_BYTES];
static uint16_t ntbuf[VIEW_TROWS * 32];        /* view name table rows with per-tile palettes */
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

static void vint_cb(void)
{
    vints++;
    HUD_WeaponVBlank();
    if (dma_src) {
        const uint16_t n = (FB_BYTES - dma_pos) > DMA_CHUNK ? DMA_CHUNK : (FB_BYTES - dma_pos);
        const uint16_t dst = (shown ? TILE_FB0 : TILE_FB1) * 32 + dma_pos;
        DMA_doDma(DMA_VRAM, (void *)(dma_src + dma_pos), dst, n / 2, 2);
        dma_pos += n;
        if (dma_pos >= FB_BYTES) {
#if !defined(NPAL) || NPAL != 1
            const uint16_t nt = shown ? NT0 : NT1;
            for (int r = 0; r < VIEW_TROWS; r++)
                DMA_doDma(DMA_VRAM, (void *)(ntbuf + r * 32), nt + (VIEW_ROW0 + r) * 128, 32, 2);
#endif
            shown ^= 1;
            *(volatile uint16_t *)0xC00004 = 0x8200 | ((shown ? NT1 : NT0) >> 10);
            dma_src = 0;
        }
    }
}

static void setup_screen(void)
{
    SYS_disableInts();
    VDP_setScreenWidth256();
    *(volatile uint16_t *)0xC00004 = 0x8F02;      /* auto-increment 2 */
    /* palette */
    *(volatile uint32_t *)0xC00004 = 0xC0000000UL;
    for (int p = 0; p < num_palettes && p < 3; p++)
        for (int i = 0; i < 16; i++) *(volatile uint16_t *)0xC00000 = md_palette[p][i];
    /* both name tables: view rows point at the framebuffer tiles, column-major */
    for (int b = 0; b < 2; b++) {
        const uint16_t nt = b ? NT1 : NT0, base = b ? TILE_FB1 : TILE_FB0;
        for (int ty = 0; ty < 32; ty++) {
            vram_cmd(nt + ty * 128);
            for (int tx = 0; tx < 64; tx++) {
                uint16_t v = 0;
                if (tx < 32 && ty >= VIEW_ROW0 && ty < VIEW_ROW0 + VIEW_TROWS) v = base + tx * VIEW_TROWS + (ty - VIEW_ROW0);
                *(volatile uint16_t *)0xC00000 = v;
            }
        }
    }
    *(volatile uint16_t *)0xC00004 = 0x8200 | (NT0 >> 10);
    shown = 0;
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
    for (uint16_t i = 0; i < map_counts[5]; i++) {
        const MapLine *l = &map_lines[i];
        const int16_t ax = map_verts[l->v1][0], ay = map_verts[l->v1][1];
        const int16_t bx = map_verts[l->v2][0], by = map_verts[l->v2][1];
        if ((ax < bx ? ax : bx) > x + R || (ax > bx ? ax : bx) < x - R) continue;
        if ((ay < by ? ay : by) > y + R || (ay > by ? ay : by) < y - R) continue;
        int solid = (l->back == 0xFF) || (l->flags & 1);
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
    if ((sp == 1 || (sp >= 26 && sp <= 28) || (sp >= 31 && sp <= 34) || sp == 117 || sp == 118) && l->back != 0xFF) {
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

static void try_move(int32_t mx, int32_t my)
{
    const int32_t nx = view.x + mx, ny = view.y + my;
    if (!blocked(nx >> 16, ny >> 16)) { view.x = nx; view.y = ny; return; }
    if (!blocked(nx >> 16, view.y >> 16)) { view.x = nx; return; }
    if (!blocked(view.x >> 16, ny >> 16)) { view.y = ny; }
}

/* bench route: (vblanks, buttons) */
static const uint16_t bench_script[][2] = {
    {60, 0}, {120, BUTTON_UP}, {60, BUTTON_LEFT}, {150, BUTTON_UP}, {90, BUTTON_RIGHT}, {180, BUTTON_UP},
    {120, BUTTON_RIGHT | BUTTON_UP}, {120, BUTTON_UP}, {200, BUTTON_LEFT}, {150, BUTTON_UP}, {0, 0}
};

static void title(void)
{
    VDP_clearPlane(BG_B, TRUE);
    VDP_drawText(ROM_NAME, 4, 6);
    VDP_drawText("Renderer estilo Dread:", 4, 9);
    VDP_drawText("paredes por coluna, chao/teto", 4, 10);
    VDP_drawText("em cor solida, E1M1 do Doom.", 4, 11);
    VDP_drawText("Mede FPS (canto inferior).", 4, 13);
    VDP_drawText("Cima/baixo anda, lados gira,", 4, 15);
    VDP_drawText("C+lados anda de lado,", 4, 16);
    VDP_drawText("A atira, B abre portas.", 4, 17);
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

int main(bool hard)
{
    (void)hard;
    SYS_disableInts();
    SYS_setVIntCallback(vint_cb);
    SYS_enableInts();
    R_Init();
    for (int d = 0; d < map_ndoors && d < 64; d++) door_target[d] = map_sectors[map_doors[d].sector].ceil;
    title();
    HUD_Opening();
    setup_screen();
    HUD_Init(HUD_ROW0);
    HudState hud = { 100, 0, 50, {50, 0, 0, 0}, {200, 50, 50, 300}, 1, 0, 0 };
    HUD_Draw(&hud);
    uint16_t face_t = 0, weap_t = 0, weap_step = 0, bob = 0;
    static const uint8_t weap_seq[4][2] = { {1, 10}, {2, 7}, {3, 8}, {0, 0} };   /* frame, vblanks (Doom 6/4/5 tics) */

    view.x = (int32_t)map_start[0] << 16; view.y = (int32_t)map_start[1] << 16;
    view.angle = (uint16_t)((int32_t)map_start[2] * 65536 / 360);
    cur_floor = map_sectors[map_subs[R_PointInSub(map_start[0], map_start[1])].sector].floor;

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
        if (bench_req && !bench_done) {
            script_t += dt;
            while (bench_script[script_i][0] && script_t >= bench_script[script_i][0]) { script_t -= bench_script[script_i][0]; script_i++; }
            j = bench_script[script_i][1];
            bench_joy = j;
            if (!bench_script[script_i][0]) {
                bench_done = 1; bench_vints = vints - bench_v0;
            }
        }
        if ((j & BUTTON_B) && !(prev_joy & BUTTON_B)) use_line();
        prev_joy = j;
        doors_tick(dt);
        /* turn / move (per vblank speeds, Doom-like) */
        const int strafe = (j & BUTTON_C) != 0;
        const int32_t speed = 0x30000;     /* map units per vblank, 16.16 */
        /* pistol: A fires (Doom timing), the status bar counts the bullets */
        if (weap_step == 0 && (j & BUTTON_A) && hud.ammo[0]) {
            weap_step = 1; weap_t = weap_seq[0][1]; HUD_WeaponFrame(weap_seq[0][0]);
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

        /* render into the free RAM buffer, then hand it to the VBlank DMA */
        R_RenderView(&view, fbuf[cur_buf]);
        frame_segs = rstats.segs_drawn; frame_nodes = rstats.nodes_visited; frame_cols = rstats.col_visits; frame_anchors = rstats.anchors;
        while (dma_src) {}
#if !defined(NPAL) || NPAL != 1
        R_BuildNametable(ntbuf, shown ? TILE_FB0 : TILE_FB1);   /* goes to the hidden copy */
#endif
        dma_pos = 0; dma_src = fbuf[cur_buf];
        cur_buf ^= 1;
        if (bench_req && !bench_done) bench_frames++;

        if (++fps_n == 16) {
            const uint16_t dv = vints - fps_v0; fps_v0 = vints; fps_n = 0;
            const uint16_t f10 = dv ? (uint16_t)(16UL * 600 / dv) : 0;
            sprintf(txt, "FPS %2u.%u  SEGS %3u ", f10 / 10, f10 % 10, frame_segs);
            SYS_disableInts();
            VDP_drawTextEx(BG_B, txt, TILE_ATTR(PAL3, 1, 0, 0), 1, 25, CPU);
            SYS_enableInts();
        }
        if (bench_done == 1) {
            const uint16_t f100 = (uint16_t)(bench_frames * 6000UL / (bench_vints ? bench_vints : 1));
            sprintf(txt, "BENCH %u quadros %u.%u%u FPS", (uint16_t)bench_frames, f100 / 100, (f100 / 10) % 10, f100 % 10);
            SYS_disableInts();
            VDP_drawTextEx(BG_B, txt, TILE_ATTR(PAL3, 1, 0, 0), 1, 26, CPU);
            SYS_enableInts();
            bench_done = 2;
        }
    }
    return 0;
}
