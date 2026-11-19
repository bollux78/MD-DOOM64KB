"""MANIFOLD_BENCH=1: benchmark mode inside the ROM (test ROMs only).

After the level loads the ROM walks a fixed list of viewpoints on its own: the 4 spawn directions (the player is
not moved) plus the extra worst-case spots listed per map in BENCH_POINTS.  Per point it renders SETTLE frames
(not counted) and NF frames whose last_frame_ticks (SGDK getTick, 300/s) are averaged.  When the list is done the
screen is cleared and a table with ticks/frame and FPS per point is drawn; START leaves it (level reload, the bench
does not run again).  The state is the struct `m14b` overlaid on manifold_dbg[0..4] (18 bytes, no extra BSS) so MAME/Lua can read it too:
m14b.st 0 = warming up / running, 2 = table shown, 3 = finished.  res[i] = avg ticks / 2 (u8).
Needs MONSTERS_INACTIVE=1 in the build for repeatable numbers (the script that builds bench ROMs sets it).
Points are (label, x, y, angle) with map units and 1024 = full circle, 0 = east."""
import os

NF = 8          # measured frames per point
SETTLE = 3      # frames rendered after the jump before counting

# extra spots per map (spawn x4 is always there).  x, y in map units, ang 0..1023
BENCH_POINTS = {
    "E1M1": [("ESC A", 420, -3232, 512), ("ESC B", 420, -3232, 640), ("ESC C", 420, -3232, 384),
             ("ESC D", 200, -3232, 0), ("ESC E", 200, -3232, 512)],
}


def _one(text, anchor, new, what):
    assert text.count(anchor) == 1, (what, text.count(anchor))
    return text.replace(anchor, new, 1)


def m14_bench(out):
    if os.environ.get("MANIFOLD_BENCH", "0") != "1":
        return
    map_name = os.environ.get("MANIFOLD_MAP", "E1M1")
    ex = BENCH_POINTS.get(map_name, [])
    assert len(ex) <= 8
    tbl = ('const struct { u16 n; s16 p[%d][3]; } __attribute__((section(".rodata.m14b_tbl"))) m14b_tbl = { %d, { %s } };\n'
           % (max(len(ex), 1), len(ex), ",".join("{%d,%d,%d}" % (x, y, a) for _, x, y, a in ex) or "{0,0,0}"))
    code = r'''
/* ---- MANIFOLD_BENCH: in-ROM benchmark ---- */
int within_sector(fix32 x, fix32 y, u16 sector);
#define M14B_NP 12
#define M14B_NF %(nf)d
#define M14B_SETTLE %(settle)d
#define M14B_HOLD 3
typedef struct { u8 st, i; s8 n; u8 fl; u16 acc; u8 res[M14B_NP]; } m14b_t;   /* fl: 1 = START was held, 2 = warm-up started */
extern volatile u32 manifold_dbg[8];            /* slots 0..5 are unused: reuse them, no extra BSS (RAM is full) */
#define m14b (*(m14b_t *)(void *)manifold_dbg)
extern const struct { u16 n; s16 p[8][3]; } m14b_tbl;   /* per map, fixed address (linker script), extra points only */
extern u16 m14_map_id_var;
#define M14B_COUNT (4 + m14b_tbl.n)

static void m14b_put(const char *t, u16 x, u16 y) {
    while (*t) { M14_VB_BEGIN(); VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL3, 1, 0, 0, TILE_FONT_INDEX + (*t) - 32), x++, y + 2); M14_VB_END(); t++; }
}
static char *m14b_dec(char *p, u32 v, u8 w) {          /* right-aligned decimal in w columns */
    char *e = p + w; char *q = e;
    do { *--q = (char)('0' + v %% 10); v /= 10; } while (v && q > p);
    while (q > p) *--q = ' ';
    return e;
}
static void m14b_show(void) {
    char ln[41]; u8 k; u32 sum = 0;
    SYS_setHIntCallback(NULL); VDP_setHInterrupt(0); VDP_setEnable(1);   /* the 3D view blanks the borders from an HInt */
    VDP_clearPlane(BG_A, TRUE); VDP_clearPlane(BG_B, TRUE);
    VDP_setVerticalScroll(BG_A, 0); VDP_setVerticalScroll(BG_B, 0); VDP_setHorizontalScroll(BG_A, 0); VDP_setHorizontalScroll(BG_B, 0);
    VDP_resetSprites(); VDP_updateSprites(1, CPU);
    SYS_doVBlankProcess(); SYS_doVBlankProcess();
    PAL_setColor(48, 0x000); PAL_setColor(49, 0xEEE);
    { char d[4]; d[0] = 'E'; d[1] = '1'; d[2] = 'M'; d[3] = 0; m14b_put("BENCH", 0, 1); m14b_put(d, 6, 1);
      d[0] = (char)('1' + m14_map_id_var); d[1] = 0; m14b_put(d, 9, 1); m14b_put("ticks/quadro (300 = 1 s)", 12, 1); }
    for (k = 0; k < M14B_COUNT; k++) {
        u32 t = (u32)m14b.res[k] * 2; char *p = ln; char lb[10]; const char *s = lb; { u8 q; static const char *const sp[4] = { "SPAWN 0", "SPAWN 90", "SPAWN 180", "SPAWN 270" }; if (k < 4) s = sp[k]; else { for (q = 0; q < 6; q++) lb[q] = "PONTO "[q]; lb[6] = (char)('0' + k - 3); lb[7] = 0; } } u32 f;
        sum += t;
        while (*s && p < ln + 12) *p++ = *s++;
        while (p < ln + 12) *p++ = ' ';
        p = m14b_dec(p, t, 5); *p++ = ' '; *p++ = ' ';
        f = t ? 3000UL / t : 0; p = m14b_dec(p, f / 10, 3); *p++ = '.'; *p++ = (char)('0' + f %% 10);
        *p++ = ' '; *p++ = 'F'; *p++ = 'P'; *p++ = 'S'; *p = 0;
        m14b_put(ln, 2, 3 + k);
    }
    { char *p = ln; const char *s = "TOTAL"; while (*s) *p++ = *s++; while (p < ln + 12) *p++ = ' ';
      p = m14b_dec(p, sum, 5); *p = 0; m14b_put(ln, 2, 4 + M14B_COUNT); }
    m14b_put("START = SAIR", 2, 7 + M14B_COUNT);
}

/* start of run_game: 1 = reload level, 2 = skip the frame (table on screen) */
int m14_bench_pre(void) {
    u16 j;
    if (m14b.st < 2) return 0;
    if (m14b.st == 3) return 0;
    j = JOY_readJoypad(JOY_1);
    if (j & BUTTON_START) { if (!(m14b.fl & 1)) { m14b.st = 3; return 1; } } else m14b.fl &= ~1;
    return 2;
}
/* before the camera math: jump to the point when it starts */
void m14_bench_set(void) {
    s16 x, y; u16 c, n;
    if (m14b.st >= 2 || m14b.n != 0) return;
    if (m14b.i < 4) { cur_player_pos.ang = (u16)m14b.i << 8; return; }            /* spawn: keep position, turn */
    cur_player_pos.ang = (u16)m14b_tbl.p[m14b.i - 4][2];
    x = m14b_tbl.p[m14b.i - 4][0]; y = m14b_tbl.p[m14b.i - 4][1];
    cur_player_pos.x = (fix32)x << FIX32_FRAC_BITS; cur_player_pos.y = (fix32)y << FIX32_FRAC_BITS;
    n = cur_portal_map->num_sectors;
    for (c = 0; c < n; c++) if (within_sector(cur_player_pos.x, cur_player_pos.y, c)) break;
    if (c == n) return;                                       /* not inside any cell: measure where we are */
    cur_player_pos.cur_sector = c;
    cur_player_pos.z = (fix32)(get_sector_group_floor_height(sector_group(c, cur_portal_map)) >> 4) << FIX32_FRAC_BITS;
}
/* after last_frame_ticks is known */
void m14_bench_post(void) {
    if (m14b.st >= 2) return;
    if (m14b.n == 0 && m14b.i == 0 && m14b.acc == 0 && !(m14b.fl & 2)) { m14b.fl |= 2; m14b.n = -60; return; }  /* warm-up after level start */
    m14b.n++;
    if (m14b.n <= 0) return;
    if (m14b.n > M14B_SETTLE && m14b.n <= M14B_SETTLE + M14B_NF) m14b.acc += last_frame_ticks;
    if (m14b.n == M14B_SETTLE + M14B_NF) { u16 a = m14b.acc / (M14B_NF * 2); m14b.res[m14b.i] = a > 255 ? 255 : (u8)a; m14b.acc = 0; }
    if (m14b.n >= M14B_SETTLE + M14B_NF + M14B_HOLD) {     /* HOLD: same view kept a few frames so the shown picture is settled (snapshots) */
        m14b.n = 0; m14b.i++;
        if (m14b.i >= M14B_COUNT) { m14b.st = 2; if (JOY_readJoypad(JOY_1) & BUTTON_START) m14b.fl |= 1; m14b_show(); }
    }
}
''' % dict(nf=NF, settle=SETTLE)
    mp = out / "src/e1m1_map.c"
    assert mp.exists(), "e1m1_map.c missing"
    mp.write_text(mp.read_text() + "\n" + tbl)
    g = out / "src/game.c"
    t = g.read_text()
    t += code
    # hooks
    a = "    calc_movement_speeds();\n\n    int input_res = handle_input();"
    t = _one(t, a, "    calc_movement_speeds();\n    { extern int m14_bench_pre(void); int br_ = m14_bench_pre(); if (br_ == 1) return RESET_MODE; if (br_ == 2) return SAME_MODE; }\n\n    int input_res = handle_input();", "bench pre hook")
    a = "    angleCos32 = cosFix32(cur_player_pos.ang);"
    t = _one(t, a, "    { extern void m14_bench_set(void); m14_bench_set(); }\n" + a, "bench set hook")
    a = "    last_frame_ticks = end_ticks - start_ticks;"
    t = _one(t, a, a + "\n    { extern void m14_bench_post(void); m14_bench_post(); }", "bench post hook")
    g.write_text(t)
    print("bench: %d points on %s" % (4 + len(ex), map_name))
