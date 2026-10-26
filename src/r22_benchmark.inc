/* Shared R21 benchmark implementation. */
#if defined(TIMEDEMO) || defined(DOOM_R50_PLAY_BENCH)
/* Benchmark v2: displayed frames, wall-clock VBlanks and one-second FPS windows.
   VDP/Z80 clocks are unchanged even when the 68000 is overclocked. */
static uint32_t bench_start_vb;
static uint32_t bench_window_vb;
static uint32_t bench_frames;
static uint32_t bench_window_frames;
static uint16_t bench_min_x10;
static uint16_t bench_max_x10;
static uint16_t bench_windows;
static boolean bench_active;
#if defined(DOOM_PROFILE)
/* Coarse, low-overhead sampling: VBlank increments at 60 Hz.
   Totals are approximate, NOT cycle-accurate. */
static uint32_t prof_logic_vb, prof_render_vb, prof_vdp_vb;
void I_ProfileLogic(uint32_t elapsed) { prof_logic_vb += elapsed; }
void I_ProfileRender(uint32_t elapsed) { prof_render_vb += elapsed; }
#endif

#if defined(DOOM_R21_FRAME_HASH)
#if defined(DOOM_R20_STACKGUARD) || defined(DOOM_R20_COUNTERS) || defined(DOOM_ROUTINE_PROFILE) || defined(DOOM_CACHE_STATS) || defined(DOOM_PROFILE) || defined(DOOM_R21_PROF)
#error DOOM_R21_FRAME_HASH owns result rows 19..22; build it without other diagnostics
#endif
/*
 * R21 N2: exact-equivalence oracle. Every DEMO3 frame, hash the tilemap that
 * is about to be shown (rows 1..27: viewport + HUD; row 0 holds the FPS text,
 * which legitimately differs between builds), then fold it into a running
 * hash. An optimisation that claims to be exact must reproduce the control's
 * checkpoints bit for bit. Cost ~31 k cycles/frame: FPS of this ROM is not a
 * performance number.
 */
typedef uint32_t __attribute__((may_alias)) r21_u32a;
static uint32_t r21_hash;
static uint32_t r21_hash_at[8];
static const uint16_t r21_hash_mark[7] = { 1, 10, 100, 500, 1000, 1500, 2000 };
static void R21_HashFrame(uint32_t frame)
{
    const r21_u32a *p = (const r21_u32a *)&_s_screen[VIEWWINDOWWIDTH];
    uint16_t n = (uint16_t)((VIEWWINDOWWIDTH * (VDP_DISPLAY_ROWS - 1)) / 2);
    uint32_t h = 0x811C9DC5u;
    do
    {
        h = ((h << 7) | (h >> 25)) + *p++;
    } while (--n);
    r21_hash = ((r21_hash << 3) | (r21_hash >> 29)) ^ h;
    for (uint16_t i = 0; i < 7; i++)
        if (frame == r21_hash_mark[i])
            r21_hash_at[i] = r21_hash;
    r21_hash_at[7] = r21_hash;
}
#if ((VIEWWINDOWWIDTH * (VDP_DISPLAY_ROWS - 1)) & 1)
#error R21 frame hash reads pairs of tile words
#endif
#endif

void I_BenchmarkReset(void)
{
    bench_start_vb = _g_vblankCount;
    bench_window_vb = bench_start_vb;
    bench_frames = 0;
    bench_window_frames = 0;
    bench_min_x10 = 0xffff;
    bench_max_x10 = 0;
    bench_windows = 0;
    bench_active = true;
#if defined(DOOM_CACHE_STATS)
    R_CacheStatsReset();
#endif
#if defined(DOOM_ROUTINE_PROFILE)
    I_ProfileSampleReset();
#endif
#if defined(DOOM_R20_COUNTERS)
    for (uint16_t i = 0; i < R20C_N; i++) r20_cnt[i] = 0;
#endif
#if defined(DOOM_R48_P0_PROFILE)
    for (uint16_t i = 0; i < R48_STATS_N; i++) r48_prof[i] = 0;
#endif
#if defined(DOOM_R21_PROF)
#if defined(DOOM_R20_STACKGUARD) || defined(DOOM_R20_COUNTERS) || defined(DOOM_ROUTINE_PROFILE) || defined(DOOM_CACHE_STATS) || defined(DOOM_PROFILE)
#error DOOM_R21_PROF owns result rows 19..22; build it without other diagnostics
#endif
    R21_ProfStart();
#endif
#if defined(DOOM_R68_PROF)
#if defined(DOOM_R21_PROF)
#error R68 and R21 profilers both use the HInt vector
#endif
    R68_Start();
#endif
#if defined(DOOM_R21_STACK_PLAY)
#if !defined(DOOM_R20_STACKGUARD)
#error DOOM_R21_STACK_PLAY extends DOOM_R20_STACKGUARD
#endif
    R21_StackRepaintForPlay();
#endif
#if defined(DOOM_R21_FRAME_HASH)
    r21_hash = 0;
    for (uint16_t i = 0; i < 8; i++) r21_hash_at[i] = 0;
#endif
#if defined(DOOM_PROFILE)
    prof_logic_vb = prof_render_vb = prof_vdp_vb = 0;
#endif
}

static void I_BenchmarkFrame(void)
{
    if (!bench_active) return;
#if defined(DOOM_R21_FRAME_HASH)
    R21_HashFrame(bench_frames + 1);
#endif
    bench_frames++;
    bench_window_frames++;
    uint32_t elapsed = _g_vblankCount - bench_window_vb;
    if (elapsed >= 60)
    {
        uint16_t fps_x10 = (uint16_t)((bench_window_frames * 600u + elapsed / 2) / elapsed);
        if (fps_x10 < bench_min_x10) bench_min_x10 = fps_x10;
        if (fps_x10 > bench_max_x10) bench_max_x10 = fps_x10;
        bench_windows++;
        bench_window_frames = 0;
        bench_window_vb = _g_vblankCount;
    }
}

/* Plain text results avoid dependence on libc printf/formatting stubs. */
static void bench_u32(char *out, uint32_t n)
{
    char tmp[11];
    uint16_t len = 0;
    do { tmp[len++] = (char)('0' + n % 10); n /= 10; } while (n);
    for (uint16_t i = 0; i < len; i++) out[i] = tmp[len - i - 1];
    out[len] = 0;
}

static void bench_fixed(char *out, uint32_t n, uint8_t decimals)
{
    uint32_t scale = 1;
    for (uint8_t i = 0; i < decimals; i++) scale *= 10;
    bench_u32(out, n / scale);
    while (*out) out++;
    if (decimals)
    {
        *out++ = '.';
        uint32_t remainder = n % scale;
        uint32_t divisor = scale / 10;
        while (divisor)
        {
            *out++ = (char)('0' + (remainder / divisor) % 10);
            divisor /= 10;
        }
        *out = 0;
    }
}

void I_BenchmarkShowResults(void)
{
    R20_StopVideo();
#if defined(DOOM_R20_STACKGUARD)
    R20_PROBE();
    R20_DiagFreeze();
#endif
    bench_active = false;
    uint32_t elapsed = _g_vblankCount - bench_start_vb;
    if (!elapsed) elapsed = 1;
    uint32_t avg_x100 = (bench_frames * 6000u + elapsed / 2) / elapsed;
    uint32_t seconds_x100 = (elapsed * 100u + 30u) / 60u;
    char buffer[16];

#if defined(DOOM_R21_PROF)
    R21_ProfStop(bench_frames);
#endif
    R21_PROBE_HEAP();
    R21_TEXT_SCREEN();
#if defined(DOOM_R57_H32)
    VDP_setScreenWidth320();
    VDP_setHorizontalScroll(BG_A,0);VDP_setHorizontalScroll(BG_B,4);
    r57_h32_active=0;r57_hud_dirty=1;
#endif
    VDP_setTextPalette(PAL0);
    PAL_setColor(15, 0x0EEE);
#if defined(DOOM_BUILD_VARIANT)
    /* Same exact variant name used for the ROM title and artifact filename. */
    VDP_drawText(DOOM_BUILD_TITLE, 4, 2);
#elif defined(DOOM_ROUTINE_PROFILE)
    VDP_drawText("DOOM MD - ROUTINE PROFILE", 2, 2);
#else
    VDP_drawText("DOOM MD - TIMEDEMO 3.0", 5, 2);
#endif
    VDP_drawText("DEMO3 / NTSC 60HZ", 5, 5);

    VDP_drawText("AVERAGE FPS", 5, 8);
    bench_fixed(buffer, avg_x100, 2);
    VDP_drawText(buffer, 24, 8);

    VDP_drawText("MIN FPS (1S)", 5, 10);
    if (bench_windows) bench_fixed(buffer, bench_min_x10, 1);
    else { buffer[0] = '-'; buffer[1] = 0; }
    VDP_drawText(buffer, 24, 10);

    VDP_drawText("MAX FPS (1S)", 5, 12);
    if (bench_windows) bench_fixed(buffer, bench_max_x10, 1);
    else { buffer[0] = '-'; buffer[1] = 0; }
    VDP_drawText(buffer, 24, 12);

    VDP_drawText("TOTAL FRAMES", 5, 15);
    bench_u32(buffer, bench_frames);
    VDP_drawText(buffer, 24, 15);

    VDP_drawText("TIME (SECONDS)", 5, 17);
    bench_fixed(buffer, seconds_x100, 2);
    VDP_drawText(buffer, 24, 17);

#if defined(DOOM_R48_P0_PROFILE)
    {
        /* These are totals across DEMO3, not CPU cycle measurements.
         * The profiler adds branches/stores to hot loops and distorts FPS. */
        static const char *const labels[R48_STATS_N] = {
            "WALL PIXELS", "FLAT PIXELS", "SPR PIXELS",
            "WALL CALLS", "FLAT CALLS", "SPR CALLS",
            "WAIT CALLS", "WAIT SPINS"
        };
        for (uint16_t i = 0; i < R48_STATS_N; i++) {
            const uint16_t y = (uint16_t)(19 + i);
            VDP_drawText(labels[i], 3, y);
            bench_u32(buffer, r48_prof[i]);
            VDP_drawText(buffer, 23, y);
        }
    }
#elif defined(DOOM_ROUTINE_PROFILE)
    {
#if defined(DOOM_R7_PROFILE)
        const char *names[11] = { "OTHER/LOGIC", "SETUP", "BSP OTHER", "SEG LOOP REST", "MASKED/SPR", "VDP/DMA", "DRAW WALL", "COMPOSE COL", "STORE RANGE", "ADD LINE", "CHECK BBOX" };
        uint32_t total = 0;
        for (uint16_t n = 0; n < 11; n++) total += doom_profile_samples[n];
        if (!total) total = 1;
        for (uint16_t n = 0; n < 11; n++) {
            uint32_t pct_x10 = (doom_profile_samples[n] * 1000u + total / 2) / total;
            uint16_t x = n < 6 ? 1 : 21;
            uint16_t y = 20 + (n < 6 ? n : n - 6);
            VDP_drawText(names[n], x, y);
            bench_fixed(buffer, pct_x10, 1);
            VDP_drawText(buffer, x + 14, y);
        }
#else
        const char *names[6] = { "OTHER/LOGIC", "SETUP", "BSP TRAVERSE", "WALL COLUMNS", "MASKED/SPR", "VDP WAIT/DMA" };
        uint32_t total = 0;
        for (uint16_t n = 0; n < 6; n++) total += doom_profile_samples[n];
        if (!total) total = 1;
        for (uint16_t n = 0; n < 6; n++)
        {
            uint32_t pct_x10 = (doom_profile_samples[n] * 1000u + total / 2) / total;
            VDP_drawText(names[n], 3, 19 + n);
            bench_fixed(buffer, pct_x10, 1);
            VDP_drawText(buffer, 24, 19 + n);
        }
#endif
    }
#elif defined(DOOM_PROFILE)
    VDP_drawText("CPU LOGIC", 5, 19);
    bench_fixed(buffer, (prof_logic_vb * 100u + 30u) / 60u, 2);
    VDP_drawText(buffer, 24, 19);
    VDP_drawText("RENDER OTHER", 5, 20);
    bench_fixed(buffer, ((prof_render_vb > prof_vdp_vb ? prof_render_vb - prof_vdp_vb : 0) * 100u + 30u) / 60u, 2);
    VDP_drawText(buffer, 24, 20);
    VDP_drawText("VDP SYNC + DMA", 5, 21);
    bench_fixed(buffer, (prof_vdp_vb * 100u + 30u) / 60u, 2);
    VDP_drawText(buffer, 24, 21);
    VDP_drawText("TIMES APPROX / VB=16.7MS", 2, 24);
#elif defined(DOOM_CACHE_STATS)
    /* Statistics count only requests to R_ComposeColumn, not all textures.
     * Counter increments add overhead; compare FPS using non-stats ROMs. */
    VDP_drawText("CACHE SLOTS", 5, 19);
    bench_u32(buffer, DOOM_CACHE_SLOTS);
    VDP_drawText(buffer, 24, 19);
    VDP_drawText("CACHE HITS", 5, 20);
    bench_u32(buffer, doom_cache_hits);
    VDP_drawText(buffer, 24, 20);
    VDP_drawText("CACHE MISSES", 5, 21);
    bench_u32(buffer, doom_cache_misses);
    VDP_drawText(buffer, 24, 21);
    VDP_drawText("CACHE EVICTIONS", 5, 22);
    bench_u32(buffer, doom_cache_evictions);
    VDP_drawText(buffer, 24, 22);
    VDP_drawText("HIT RATE %", 5, 24);
    {
        uint32_t requests = doom_cache_hits + doom_cache_misses;
        uint32_t ratio = requests ? (doom_cache_hits * 1000u + requests / 2) / requests : 0;
        bench_fixed(buffer, ratio, 1);
        VDP_drawText(buffer, 24, 24);
    }
    VDP_drawText("STATS ROM: FPS HAS OVERHEAD", 2, 26);
#elif defined(DOOM_R20_COUNTERS)
    {
        /* Per presented frame, x10. Counting costs CPU: FPS is not a baseline. */
        static const char *const names[R20C_N] = {
            "TEX CALLS", "TEX CELLS", "FLAT CALLS", "FLAT CELLS",
            "WALL 1PATCH", "WALL MULTI", "WALL COMPOSED", "TAN 16BIT",
            "TAN 32BIT", "SEGS", "SIGHT CHECKS", "SIGHT DEPTH",
            "SEG COLUMNS", "TEX SKIPPABLE" };
        uint32_t frames = bench_frames ? bench_frames : 1;
        for (uint16_t n = 0; n < R20C_N; n++)
        {
            /* R21: 7 + 7 rows (19..25); values right-aligned 6 chars. */
            uint16_t x = n < 7 ? 1 : 20;
            uint16_t y = 19 + (n < 7 ? n : n - 7);
            VDP_drawText(names[n], x, y);
            if (n == R20C_SIGHT_DEPTH)
                bench_u32(buffer, r20_cnt[n]);              /* a maximum, not a rate */
            else
                bench_fixed(buffer, (r20_cnt[n] * 10u + frames / 2) / frames, 1);
            VDP_drawText(buffer, x + 14, y);
        }
    }
#else
    VDP_drawText("MIN/MAX: FULL 1S WINDOWS", 3, 23);
#endif
#if defined(DOOM_R21_NO_VDP_INIT) || defined(DOOM_R21_HEAP_PROBE)
#define R21_SHOW_HEAP_AT_END() do { \
        VDP_drawText("SGDK FREE / BLOCK AT END", 3, 18); \
        bench_u32(buffer, r21_heap_at_end_free); VDP_drawText(buffer, 28, 18); \
        bench_u32(buffer, r21_heap_at_end_largest); VDP_drawText(buffer, 34, 18); \
    } while (0)
#else
#define R21_SHOW_HEAP_AT_END() ((void)0)
#endif
    R21_SHOW_HEAP_AT_END();
#if defined(DOOM_R21_PROF)
    VDP_drawText("PROFILE SAMPLES", 3, 19);
    bench_u32(buffer, r21_prof_samples); VDP_drawText(buffer, 24, 19);
    VDP_drawText("BAD FRAME / OUT RANGE", 3, 20);
    bench_u32(buffer, r21_prof_bad); VDP_drawText(buffer, 25, 20);
    bench_u32(buffer, r21_prof_out); VDP_drawText(buffer, 32, 20);
    VDP_drawText(r21_prof_state == 3 ? "HISTOGRAM IN SRAM: QUIT EMU"
               : r21_prof_state == 2 ? "PROFILER OFF: ROM ABOVE 2MB"
                                     : "PROFILER NOT RUN", 3, 21);
    VDP_drawText("PROFILE FPS HAS OVERHEAD", 3, 22);
#endif
#if defined(DOOM_R21_FRAME_HASH)
    {
        static const char *const r21_hash_label[8] = {
            "H1", "H10", "H100", "H500", "H1000", "H1500", "H2000", "HEND" };
        for (uint16_t i = 0; i < 8; i++)
        {
            uint16_t x = (i & 1) ? 21 : 2;
            uint16_t y = 19 + (i >> 1);
            VDP_drawText(r21_hash_label[i], x, y);
            intToHex(r21_hash_at[i], buffer, 8);
            VDP_drawText(buffer, x + 7, y);
        }
    }
#endif
#if defined(DOOM_R20_STACKGUARD)
    /* All data were frozen BEFORE VDP_init. Keep inside CRT-safe rows. */
    for (uint16_t y = 5; y <= 24; y++)
        VDP_drawText("                                      ", 1, y);
    VDP_drawText("FRAMES", 3, 5); bench_u32(buffer, bench_frames); VDP_drawText(buffer, 25, 5);
    VDP_drawText("TIME SEC", 3, 7); bench_fixed(buffer, seconds_x100, 2); VDP_drawText(buffer, 25, 7);
    VDP_drawText("STACK PEAK / RESERVE", 3, 9);
    bench_u32(buffer, r20_peak); VDP_drawText(buffer, 25, 9);
    bench_u32(buffer, R20_StackReserveBytes()); VDP_drawText(buffer, 32, 9);
    VDP_drawText("ERROR MASK / FIRST TIC", 3, 11);
    bench_u32(buffer, r20_errors); VDP_drawText(buffer, 25, 11);
    bench_u32(buffer, r20_first_error_tic); VDP_drawText(buffer, 30, 11);
    VDP_drawText("SGDK MIN FREE / BLOCK", 3, 13);
    bench_u32(buffer, r20_sgdk_free); VDP_drawText(buffer, 25, 13);
    bench_u32(buffer, r20_sgdk_largest); VDP_drawText(buffer, 32, 13);
    VDP_drawText("ZONE MIN FREE / BLOCK", 3, 15);
    bench_u32(buffer, r20_zone_free); VDP_drawText(buffer, 25, 15);
    bench_u32(buffer, r20_zone_largest); VDP_drawText(buffer, 32, 15);
    VDP_drawText("MIN SP (HEX)", 3, 17);
    intToHex(r20_min_sp, buffer, 8); VDP_drawText(buffer, 25, 17);
    VDP_drawText("1=STACK 2=END 4=SGDK", 3, 19);
    VDP_drawText("8=SP 16=ZONE; MASK ADDS", 3, 20);
#if defined(DOOM_R21_STACK_PLAY)
    VDP_drawText("BOOT PEAK / PLAY PEAK", 3, 21);
    bench_u32(buffer, r21_boot_peak); VDP_drawText(buffer, 25, 21);
    bench_u32(buffer, r20_peak); VDP_drawText(buffer, 32, 21);
    VDP_drawText("ROW 9 PEAK = DEMO3 ONLY", 3, 22);
#else
    VDP_drawText("PEAK SINCE MAIN; SATURATES", 3, 22);
#endif
    VDP_drawText("DIAGNOSTIC FPS HAS OVERHEAD", 3, 23);
    R21_SHOW_HEAP_AT_END();
#endif
#if defined(DOOM_R50_PLAY_BENCH)
    /* PLAY-only benchmark results, no mandatory ROM reset.
     * Consume a new START press, then release it before returning so the
     * same input cannot immediately dismiss/reopen the menu. Keep sound
     * and joypad service active in each VBlank. */
    VDP_drawText("START: RETURN TO MENU", 6, 26);
    uint16_t keys;
    do {
        SYS_doVBlankProcess();
        JOY_update();
        keys=JOY_readJoypad(JOY_1);
    } while (keys & BUTTON_START);
    do {
        SYS_doVBlankProcess();
        JOY_update();
        keys=JOY_readJoypad(JOY_1);
    } while (!(keys & BUTTON_START));
    do {
        SYS_doVBlankProcess();
        JOY_update();
        keys=JOY_readJoypad(JOY_1);
    } while (keys & BUTTON_START);
    return;
#else
    for (;;) SYS_doVBlankProcess();
#endif
}
#endif

