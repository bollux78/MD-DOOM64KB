#!/usr/bin/env python3
"""R117 meas (after apply_r116.py): benchmark accuracy for the official Run All. No renderer change.

Finding (R116): the 0.3 FPS minimum is a level-load window, not gameplay.
  - G_DoPlayDemo resets the 1 s window BEFORE G_ReadDemoHeader -> G_InitNew -> G_DoLoadLevel, so the
    synchronous load (~3.3 s at 7.67 MHz, ~1.7 s at 13 MHz: 0.3 vs 0.6 FPS, it scales with the CPU)
    falls inside the first window of every demo after the first.
  - The demos desync and the player dies; "use" respawns, which reloads the level (G_DoReborn ->
    ga_loadlevel) mid-demo with no window reset at all (R116 probe: leveltime < gametic on E1M2,
    E1M3, E1M4, E1M5, E1M6, E1M9 and the special).
Changes:
  - G_DoLoadLevel times itself (VBlanks) and calls R117_LoadDone: the 1 s window restarts AFTER every
    load (first map, next demo, death reload). Average FPS / frames / time are unchanged (wall clock).
  - New lines: 1% LOW FPS (frames / time of the slowest 1% of frames), WORST/P99 FRAME in VBlanks,
    MIN AT (map and leveltime of the slowest window), LOADS count / longest, LOAD TIME total.
  - Frame-cost histogram: 64 x uint16 (cost in VBlanks between presented frames, >= 63 capped);
    the first frame after a load or a reset is not counted.
All new state is forced into .data (BSS unchanged); ~150 B. Per frame: a few instructions.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


B = 'src/r22_benchmark.inc'
rep(B, '''static boolean bench_active;
''', '''static boolean bench_active;
/* R117 measurement (forced into .data: BSS unchanged). */
#define R117_D __attribute__((section(".data")))
static uint16_t r117_hist[64] R117_D = {0};
static uint32_t r117_last_vb R117_D = 0;
static uint32_t r117_load_total R117_D = 0;
static uint16_t r117_loads R117_D = 0, r117_load_max R117_D = 0;
static uint8_t  r117_min_map R117_D = 0;
static int32_t  r117_min_lt R117_D = 0;
static void R117_Clear(void){
    for(uint16_t i=0;i<64;i++)r117_hist[i]=0;
    r117_last_vb=0;r117_load_total=0;r117_loads=0;r117_load_max=0;r117_min_map=0;r117_min_lt=0;
}
''', 1)
rep(B, '''    bench_windows = 0;
    bench_active = true;
''', '''    bench_windows = 0;
    bench_active = true;
    R117_Clear();
''')
rep(B, '''void I_BenchmarkWindowReset(void)
{
    if (!bench_active) return;
    bench_window_vb = _g_vblankCount;
    bench_window_frames = 0;
}
''', '''void I_BenchmarkWindowReset(void)
{
    if (!bench_active) return;
    bench_window_vb = _g_vblankCount;
    bench_window_frames = 0;
    r117_last_vb = 0;
}
/* Called at the end of G_DoLoadLevel with the VBlank count taken at its start. */
void R117_LoadDone(uint32_t t0)
{
    if (!bench_active) return;
    const uint32_t dt = _g_vblankCount - t0;
    r117_loads++; r117_load_total += dt;
    if (dt > r117_load_max) r117_load_max = (uint16_t)(dt > 0xffffu ? 0xffffu : dt);
    bench_window_vb = _g_vblankCount;
    bench_window_frames = 0;
    r117_last_vb = 0;
}
''')
rep(B, '''    bench_frames++;
    bench_window_frames++;
    uint32_t elapsed = _g_vblankCount - bench_window_vb;
    if (elapsed >= 60)
    {
        uint16_t fps_x10 = (uint16_t)((bench_window_frames * 600u + elapsed / 2) / elapsed);
        if (fps_x10 < bench_min_x10) bench_min_x10 = fps_x10;
''', '''    bench_frames++;
    bench_window_frames++;
    {
        const uint32_t now = _g_vblankCount;
        if (r117_last_vb) {
            uint32_t c = now - r117_last_vb;
            if (c > 63u) c = 63u;
            r117_hist[c]++;
        }
        r117_last_vb = now ? now : 1u;
    }
    uint32_t elapsed = _g_vblankCount - bench_window_vb;
    if (elapsed >= 60)
    {
        uint16_t fps_x10 = (uint16_t)((bench_window_frames * 600u + elapsed / 2) / elapsed);
        if (fps_x10 < bench_min_x10) {
            extern uint8_t r116_active; extern int32_t _g_leveltime; extern int16_t _g_gamemap;
            r117_min_map = (uint8_t)_g_gamemap; r117_min_lt = _g_leveltime; (void)r116_active;
        }
        if (fps_x10 < bench_min_x10) bench_min_x10 = fps_x10;
''')
rep(B, '''    VDP_drawText("TOTAL FRAMES", 5, 15);''', '''    {
        /* R117: 1% low, worst/P99 frame, location of the slowest window, loads. */
        uint32_t n = 0;
        for (uint16_t i = 0; i < 64; i++) n += r117_hist[i];
        uint32_t want = n / 100u; if (!want && n) want = 1;
        uint32_t got = 0, cost = 0; uint16_t p99 = 0, worst = 0;
        for (int16_t i = 63; i >= 0; i--) {
            const uint32_t h = r117_hist[i];
            if (h && !worst) worst = (uint16_t)i;
            if (got < want && h) {
                uint32_t t = want - got; if (t > h) t = h;
                got += t; cost += t * (uint32_t)i; p99 = (uint16_t)i;
            }
        }
        VDP_drawText("1% LOW FPS", 5, 9);
        if (cost) { bench_fixed(buffer, (got * 6000u + cost / 2u) / cost, 2); } else { buffer[0] = '-'; buffer[1] = 0; }
        VDP_drawText(buffer, 24, 9);
        VDP_drawText("MIN AT E1M", 5, 11);
        bench_u32(buffer, r117_min_map); VDP_drawText(buffer, 15, 11);
        VDP_drawText("TIC", 17, 11);
        bench_u32(buffer, (uint32_t)(r117_min_lt < 0 ? 0 : r117_min_lt)); VDP_drawText(buffer, 24, 11);
        VDP_drawText("WORST/P99 FRAME VB", 5, 13);
        bench_u32(buffer, worst); VDP_drawText(buffer, 24, 13);
        VDP_drawText("/", 27, 13);
        bench_u32(buffer, p99); VDP_drawText(buffer, 28, 13);
        VDP_drawText("LOADS / LONGEST S", 5, 16);
        bench_u32(buffer, r117_loads); VDP_drawText(buffer, 24, 16);
        VDP_drawText("/", 27, 16);
        bench_fixed(buffer, ((uint32_t)r117_load_max * 100u + 30u) / 60u, 2); VDP_drawText(buffer, 28, 16);
        VDP_drawText("LOAD TIME (SECONDS)", 5, 18);
        bench_fixed(buffer, (uint32_t)(((uint64_t)r117_load_total * 100u + 30u) / 60u), 2); VDP_drawText(buffer, 24, 18);
    }
    VDP_drawText("TOTAL FRAMES", 5, 15);''')

G = 'src/g_game.c'
rep(G, '''static void G_DoLoadLevel (void)
{
''', '''static void G_DoLoadLevel (void)
{
    extern volatile uint32_t _g_vblankCount;
    const uint32_t r117_t0 = _g_vblankCount;
''')
rep(G, '''    ST_Start(); // wake up the status bar
    HU_Start(); // wake up the heads up text
}''', '''    ST_Start(); // wake up the status bar
    HU_Start(); // wake up the heads up text
    { extern void R117_LoadDone(uint32_t t0); R117_LoadDone(r117_t0); }
}''')

p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r116-'" in s and "('demotest', 1)" in s
p.write_text(s.replace("'r116-'", "'r117-'").replace("('demotest', 1)", "('meas', 1)"))
print('R117 meas')
