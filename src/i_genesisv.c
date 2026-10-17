#if defined(DOOM_R22_PIXEL4)
#include "r22_video.inc"
#else
/*-----------------------------------------------------------------------------
 *
 *  Sega Genesis / Mega Drive video code
 *  (Doom64KB の i_neogev.c をベースに ngdevkit -> SGDK へ置換)
 *
 *  方式: VDP プレーン A を 38x28 の「チャンキー・フレームバッファ」として使う。
 *  各セル = 8x8 ベタ塗りタイル 1 個。タイル 0..15 は単色(パレット内 index 0..15)。
 *  Doom の 256 色は 64 色(4 パレット x 16)へ量子化(scripts/genpal.py)。
 *  _s_screen は完成済み VDP タイルマップ語を直接保持し、I_FinishUpdate で一括 DMA。
 *
 *  Copyright (C) 2026 Frenkel Smeijers
 *  GPL v2 or later.
 *-----------------------------------------------------------------------------*/

#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include <stdint.h>

#include "compiler.h"
#include "i_system.h"
#include "i_video.h"
#include "m_random.h"
#include "r_defs.h"
#include "v_video.h"
#include "w_wad.h"

#include "globdata.h"
#include "gen_pal.h"
#include "r21_textscreen.h"
#include "r21_prof.h"
#include "r20_stackguard.h"
#include "r20_counters.h"
#include "r20_dma.h"

#if defined(DOOM_BUILD_VARIANT)
#include "doom_build_identity.h"
#endif


extern const int16_t CENTERY;

#if defined(DOOM_CACHE_STATS)
extern uint32_t doom_cache_hits;
extern uint32_t doom_cache_misses;
extern uint32_t doom_cache_evictions;
extern void R_CacheStatsReset(void);
#endif

// 16 個のベタ塗りタイルを置く VRAM 先頭 index
#define SOLID_TILE_INDEX  TILE_USER_INDEX

#if defined(DOOM_CELL_LUT)
/* 32 x 256 tilemap words in ROM; built from WAD COLORMAP and genpal_cell. */
#include "colormap_cells.h"
extern const uint8_t *fullcolormap;
#endif

// チャンキー FB。各要素は完成済み VDP タイルマップ語。
/* Classic HUD uses a fixed 28-row VDP buffer. R16 lifts the four-row
 * status strip from rows 24..27 to 22..25 and reserves rows 26..27 as
 * black CRT overscan safety margin. The 3D viewport is truly 38x22,
 * so its projection, weapon scale and clipping are recomputed. */
#if defined(DOOM_CLASSIC_TEXT_HUD)
#if VIEWWINDOWWIDTH != 38
#error DOOM_CLASSIC_TEXT_HUD requires 38 columns
#endif
#if defined(DOOM_R16_HUD_UP2)
#if VIEWWINDOWHEIGHT != 22
#error DOOM_R16_HUD_UP2 requires 38x22 viewport
#endif
#else
#if VIEWWINDOWHEIGHT != 24
#error DOOM_CLASSIC_TEXT_HUD requires 38x24 viewport unless R16 enabled
#endif
#endif
#define VDP_DISPLAY_ROWS 28
#else
#define VDP_DISPLAY_ROWS VIEWWINDOWHEIGHT
#endif
#if defined(DOOM_R20_REG_COLUMNS) || defined(DOOM_R20_FLAT_INLINE)
uint16_t _s_screen[VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS];
#else
static uint16_t _s_screen[VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS];
#endif

#if defined(DOOM_R20_ROWTAB) || defined(DOOM_R20_FLAT_UNROLL)
/* R20 R1: row index -> first cell of that row. Replaces yl*38 (MULS.W #38,
 * ~46 cycles) by one indexed word read. Exact for yl in 0..27. */
#if VDP_DISPLAY_ROWS > 28
#error R20 row table covers 28 rows
#endif
static const uint16_t r20_rowofs[28] = {
     0*VIEWWINDOWWIDTH,  1*VIEWWINDOWWIDTH,  2*VIEWWINDOWWIDTH,  3*VIEWWINDOWWIDTH,
     4*VIEWWINDOWWIDTH,  5*VIEWWINDOWWIDTH,  6*VIEWWINDOWWIDTH,  7*VIEWWINDOWWIDTH,
     8*VIEWWINDOWWIDTH,  9*VIEWWINDOWWIDTH, 10*VIEWWINDOWWIDTH, 11*VIEWWINDOWWIDTH,
    12*VIEWWINDOWWIDTH, 13*VIEWWINDOWWIDTH, 14*VIEWWINDOWWIDTH, 15*VIEWWINDOWWIDTH,
    16*VIEWWINDOWWIDTH, 17*VIEWWINDOWWIDTH, 18*VIEWWINDOWWIDTH, 19*VIEWWINDOWWIDTH,
    20*VIEWWINDOWWIDTH, 21*VIEWWINDOWWIDTH, 22*VIEWWINDOWWIDTH, 23*VIEWWINDOWWIDTH,
    24*VIEWWINDOWWIDTH, 25*VIEWWINDOWWIDTH, 26*VIEWWINDOWWIDTH, 27*VIEWWINDOWWIDTH };
#endif
#if defined(DOOM_R20_ROWTAB)
#define R20_DEST(x, yl) (&_s_screen[r20_rowofs[(uint16_t)(yl)] + (uint16_t)(x)])
#else
#define R20_DEST(x, yl) (&_s_screen[(yl) * VIEWWINDOWWIDTH + (x)])
#endif

// Doom 8bit 色 index -> VDP タイルマップ語
#if defined(DOOM_R20_COLOR_ROM)
#include "r20_colorcell.h"
#elif defined(DOOM_R20_FLAT_INLINE)
uint16_t colorcell[256];
#else
static uint16_t colorcell[256];
#endif

#if defined(DOOM_R20_COUNTERS)
#if defined(DOOM_MEM_DIAG) || defined(DOOM_ROUTINE_PROFILE) || defined(DOOM_CACHE_STATS)
#error DOOM_R20_COUNTERS uses the result-screen rows of the other diagnostics
#endif
uint32_t r20_cnt[R20C_N];
#endif

static int16_t palettelumpnum;


// ビュー slot(0..55) -> セル語。各パレットの index 1..14 がビュー色（0=黒, 15=テキスト色は予約）。
static inline uint16_t cell_for_color(uint8_t doomcolor)
{
	uint8_t slot = genpal_cell[doomcolor];               // 0..GENPAL_NVIEW-1
	uint8_t pal  = slot / GENPAL_VIEW_PER_PAL;           // 0..3
	uint8_t idx  = 1 + (slot % GENPAL_VIEW_PER_PAL);     // 1..14
	return TILE_ATTR_FULL(pal, 0, 0, 0, SOLID_TILE_INDEX + idx);
}

// 真の黒セル（全パレット index 0 = 黒。テキスト背景・画面クリア用）
#define BLACK_CELL  TILE_ATTR_FULL(0, 0, 0, 0, SOLID_TILE_INDEX + 0)

#if defined(DOOM_R20_REG_COLUMNS)
const uint16_t *R20_SelectCellMap(const uint8_t *map) {
    if (map && fullcolormap) {
        uintptr_t off=(uintptr_t)map-(uintptr_t)fullcolormap;
        if(off<8192u && !(off&255u))return doom_colormap_cells[off>>8];
    }
    return NULL;
}
#endif

// Doom テキスト色(0..15) -> テキストパレット(0..3): PAL0=白 / PAL1=赤 / PAL2=黄 / PAL3=灰
// （i_neogev.c の colors[] の意図に合わせる: 4,12=赤 / 14=黄 / 7,8,9=灰 / 既定=白）
static const uint8_t textpal_for_color[16] = {
	0, 0, 0, 0, 1, 0, 0, 3, 3, 3, 0, 0, 1, 0, 2, 0
};

// テキスト1文字のセル語。SGDK 内蔵フォント(TILE_FONT_INDEX, ASCII 32..127, 前景=index15)を使う。
static inline uint16_t font_cell(uint8_t color, char c)
{
	uint8_t uc = (uint8_t)c;
	// メニューカーソルは CP437 のスカル(コード 1,2)。SGDK フォントに無いので '>' で代用。
	if (uc == 1 || uc == 2)
		uc = '>';
	else if (uc < 32 || uc > 127)
		uc = 32;
	uint8_t pal = textpal_for_color[color & 15];
	return TILE_ATTR_FULL(pal, 0, 0, 0, TILE_FONT_INDEX + (uc - 32));
}


//**************************************************************************************
//
// デバッグ表示（画面右上）: 実測 FPS "x.xfps"
//

extern volatile uint32_t _g_vblankCount;   // i_genesis.c（60Hz）

#if defined(DOOM_R20_HUD_LAZY)
static uint8_t r20_hud_dirty = 1;
#endif
#if defined(DOOM_R20_FPS_LAZY)
static uint8_t r20_fps_dirty = 1;
static uint16_t r20_last_fps_x100;
#endif
#if defined(DOOM_R20_HUD_LAZY) || defined(DOOM_R20_FPS_LAZY)
static void R20_InvalidateVideo(void)
{
#if defined(DOOM_R20_HUD_LAZY)
    r20_hud_dirty = 1;
#endif
#if defined(DOOM_R20_FPS_LAZY)
    r20_fps_dirty = 1;
#endif
}
#else
#define R20_InvalidateVideo() ((void)0)
#endif
#if defined(DOOM_R20_HUD_LAZY) && !defined(DOOM_HUD_DMA_STATUS_ONLY)
#error R20 lazy HUD requires the existing status-only DMA state
#endif

#define HUD_COL 15   // 白(PAL0 index15)

static void hud_putc(int16_t cx, int16_t cy, char c)
{
	if ((uint16_t)cx < VIEWWINDOWWIDTH && (uint16_t)cy < VDP_DISPLAY_ROWS)
		_s_screen[cy * VIEWWINDOWWIDTH + cx] = font_cell(HUD_COL, c);
}

// v を cx から digits 桁、ゼロ埋め右詰めで描画
static void hud_num(int16_t cx, int16_t cy, uint16_t v, int8_t digits)
{
	for (int8_t i = digits - 1; i >= 0; i--)
	{
		hud_putc(cx + i, cy, (char)('0' + (v % 10)));
		v /= 10;
	}
}

#if defined(DOOM_CLASSIC_TEXT_HUD)
/* Minimal tile HUD; no SRAM; no 3D drawing into the four bottom rows. */
static void hud_label(int16_t x, int16_t y, const char* text)
{
    while (*text && x < VIEWWINDOWWIDTH)
        _s_screen[y * VIEWWINDOWWIDTH + x++] = font_cell(HUD_COL, *text++);
}
static uint16_t hud_saturate3(int32_t value)
{
    if (value < 0) return 0;
    if (value > 999) return 999;
    return (uint16_t)value;
}
static void I_DrawClassicTextHUD(void)
{
    for (int16_t y = VIEWWINDOWHEIGHT; y < VDP_DISPLAY_ROWS; y++)
        for (int16_t x = 0; x < VIEWWINDOWWIDTH; x++)
            _s_screen[y * VIEWWINDOWWIDTH + x] = BLACK_CELL;

    if (_g_gamestate != GS_LEVEL) return;

    /* Only updates numbers/labels in tilemap RAM; no extra pixel rendering.
     * Labels deliberately describe bullet ammo, not weapon-dependent ammo. */
    /* Use viewport-relative coordinates: original 24 -> 25/27,
     * R16 22 -> 23/25. Rows 26/27 remain black on a CRT. */
    const int16_t hud_values_row = VIEWWINDOWHEIGHT + 1;
    const int16_t hud_title_row = VIEWWINDOWHEIGHT + 3;
    hud_label(1, hud_values_row, "HEALTH");
    hud_num(8, hud_values_row, hud_saturate3(_g_player.mo ? _g_player.mo->health : _g_player.health), 3);
    hud_label(13, hud_values_row, "ARMOR");
    hud_num(19, hud_values_row, hud_saturate3(_g_player.armorpoints), 3);
    hud_label(24, hud_values_row, "BULLETS");
    hud_num(32, hud_values_row, hud_saturate3(_g_player.ammo[am_clip]), 3);
    hud_label(1, hud_title_row, "DOOM - MEGA DRIVE");
}
#endif

static void I_DrawDebugCounters(void)
{
	static uint16_t frameCount = 0;
	static uint16_t fps_x100   = 0;
	static uint32_t lastVb     = 0;
	static uint16_t lastFrame  = 0;

	uint32_t vb = _g_vblankCount;
	frameCount++;

	// FPS を約1秒(60 VBlank)ごとに更新。fps = 描画フレーム数 / (経過VBlank/60)。
	// x100 表記: fps_x100 = frames * 6000 / 経過VBlank。経過が60ちょうどでないため小数も出る。
	uint32_t dvb = vb - lastVb;
	if (dvb >= 60)
	{
		uint16_t df = frameCount - lastFrame;
		fps_x100  = (uint16_t)(((uint32_t)df * 6000u) / dvb);
		lastVb    = vb;
		lastFrame = frameCount;
	}

    // Show FPS only in-level. On entering a level, clear the entire
    // dedicated top bar once; HUD messages may reuse its left-hand side.
#if defined(DOOM_R11_TOPBAR_CLIP)
    static uint8_t topbar_in_level;
    if (_g_gamestate != GS_LEVEL)
    {
        topbar_in_level = 0;
#if defined(DOOM_R20_FPS_LAZY)
        r20_fps_dirty = 1;
#endif
        return;
    }
    if (!topbar_in_level)
    {
#if defined(DOOM_R20_FPS_LAZY)
        r20_fps_dirty = 1;
#endif
        for (uint16_t i = 0; i < VIEWWINDOWWIDTH; i++)
            _s_screen[i] = BLACK_CELL;
#if defined(DOOM_R11_LEFTCOL_CLIP)
        /* Clear the border once on entering a level, including pixels
           left over from a menu or fullscreen image. Wall, sprite and
           automap paths do not draw column zero afterwards. */
        for (uint16_t y = 1; y < VIEWWINDOWHEIGHT; y++)
            _s_screen[y * VIEWWINDOWWIDTH] = BLACK_CELL;
#endif
        topbar_in_level = 1;
    }
#else
    if (_g_gamestate != GS_LEVEL)
        return;
#endif

#if defined(DOOM_R20_FPS_LAZY)
    /* Measurement still advances every frame. Only formatting/stores skip. */
    if (!r20_fps_dirty && r20_last_fps_x100 == fps_x100) return;
    r20_last_fps_x100 = fps_x100;
    r20_fps_dirty = 0;
#endif

	// 右上に "D.Dfps" / "DD.Dfps" を右詰め(col 37 右端)で表示。cols 31..37 を使用。
	{
		uint16_t fps_x10 = (fps_x100 + 5) / 10;
		uint16_t ip = fps_x10 / 10; if (ip > 99) ip = 99;
		uint16_t fp = fps_x10 % 10;
		uint16_t x = (ip >= 10) ? 31 : 32;

		for (uint16_t i = 31; i <= 37; i++)
			hud_putc(i, 0, ' ');

		if (ip >= 10)
			hud_num(x, 0, ip, 2);
		else
			hud_num(x, 0, ip, 1);
		hud_putc(x + ((ip >= 10) ? 2 : 1), 0, '.');
		hud_putc(x + ((ip >= 10) ? 3 : 2), 0, (char)('0' + fp));
		hud_putc(x + ((ip >= 10) ? 4 : 3), 0, 'f');
		hud_putc(x + ((ip >= 10) ? 5 : 4), 0, 'p');
		hud_putc(x + ((ip >= 10) ? 6 : 5), 0, 's');
	}
}


/* Error screens are also required by playable builds without TIMEDEMO. */
#if defined(DOOM_R21_NO_VDP_INIT) || defined(DOOM_R21_HEAP_PROBE)
volatile uint16_t r21_heap_at_end_free, r21_heap_at_end_largest;
void I_R21_ProbeHeap(void)
{
    r21_heap_at_end_free = MEM_getFree();
    r21_heap_at_end_largest = MEM_getLargestFreeBlock();
}
#endif
#if defined(DOOM_R21_NO_VDP_INIT)
void I_R21_TextScreen(void)
{
    /* Keep the boot VDP setup (H40, 64x32 planes, font tiles, Doom CRAM).
       Only stop pending DMA and blank both planes; DMA fill needs no heap. */
    VDP_waitDMACompletion();
    VDP_setHInterrupt(FALSE);
    VDP_clearPlane(BG_A, TRUE);
    VDP_clearPlane(BG_B, TRUE);
    VDP_setTextPlane(BG_A);
    VDP_setTextPriority(TRUE);
}
#endif

#if defined(TIMEDEMO)
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
#if defined(DOOM_R21_PROF)
#if defined(DOOM_R20_STACKGUARD) || defined(DOOM_R20_COUNTERS) || defined(DOOM_ROUTINE_PROFILE) || defined(DOOM_CACHE_STATS) || defined(DOOM_PROFILE)
#error DOOM_R21_PROF owns result rows 19..22; build it without other diagnostics
#endif
    R21_ProfStart();
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

#if defined(DOOM_ROUTINE_PROFILE)
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
    for (;;) SYS_doVBlankProcess();
}
#endif

//**************************************************************************************
//
// Palette
//

void I_ReloadPalette(void)
{
	char lumpName[8] = "PLAYPAL";
	if (_g_gamma != 0)
		lumpName[7] = '0' + _g_gamma;
	palettelumpnum = W_GetNumForName(lumpName);
}


static void I_UploadNewPalette(int8_t pal)
{
	if (pal < 0)
		pal = 0;
	if (pal >= GENPAL_NSUB)
		pal = GENPAL_NSUB - 1;
	PAL_setColors(0, genpal_cram[pal], 64, DMA);   // PAL0..3（ビュー色 + 予約テキスト色）
}


static int8_t newpal;
#define NO_PALETTE_CHANGE 100


void I_SetPalette(int8_t p)
{
	newpal = p;
}


void V_SetSTPalette(void)
{
	// Do nothing
}


//**************************************************************************************
//
// Init / shutdown
//

static void I_BuildSolidTiles(void)
{
	// 各タイル i は全 64 ピクセルが index i のベタ塗り
	uint32_t tile[8];
	for (uint16_t i = 0; i < 16; i++)
	{
		uint32_t row = i * 0x11111111UL;   // 8 ピクセル分の nibble
		for (uint16_t j = 0; j < 8; j++)
			tile[j] = row;
		VDP_loadTileData(tile, SOLID_TILE_INDEX + i, 1, CPU);
	}
}


void I_InitGraphicsHardwareSpecificCode(void)
{
#if defined(DOOM_R21_V2_HEAPBUF)
    {
        extern void I_R21_AllocVideoCopy(void);
        I_R21_AllocVideoCopy();
    }
#endif
    R20_StopVideo();
    R20_InvalidateVideo();
	VDP_setScreenWidth320();
	VDP_setPlaneSize(64, 32, TRUE);

	I_BuildSolidTiles();

	// 256 色 -> セル語 LUT を構築
#if !defined(DOOM_R20_COLOR_ROM)
	for (uint16_t i = 0; i < 256; i++)
		colorcell[i] = cell_for_color((uint8_t)i);
#endif

	I_ReloadPalette();
	I_UploadNewPalette(0);
	newpal = NO_PALETTE_CHANGE;

	// 画面を黒で埋める
	for (int i = 0; i < VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS; i++)
		_s_screen[i] = BLACK_CELL;
#if defined(DOOM_R21_PROF)
    R21_ProfInit();
#endif
}


void I_ShutdownGraphics(void)
{
    R20_StopVideo();
	// Do nothing
}


#if (defined(DOOM_R20_DMA_BATCH) || defined(DOOM_R20_VBLANK_VIDEO)) && (!defined(DOOM_HUD_DMA_STATUS_ONLY) || defined(DOOM_R11_TOPBAR_DMA))
#error R20g DMA requires status-only, full-width rows
#endif
/* R20g DMA experiments. V3 batches only RAM tilemap rows, on the fixed
 * 64-wide BG_A set above. V2 snapshots 28 rows (2128 B, including HUD) so
 * neither framebuffer nor HUD can be torn by an interrupt. Palette and
 * tilemap ownership move together; main-loop VDP setup/results drain first.
 * V2 deliberately uses SGDK DMA unless V3 is also enabled, for clean A/B. */
#if defined(DOOM_R20_DMA_BATCH)
static void R20_UploadRows(const uint16_t *src,uint16_t rows) {
    uint16_t sr;
    __asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr" : "=d"(sr) : : "cc","memory");
    bool taken=Z80_getAndRequestBus(TRUE);
    VDP_setAutoInc(2);
    volatile uint16_t *ctrl=(volatile uint16_t *)VDP_CTRL_PORT;
    uint16_t dest=VDP_getPlaneAddress(BG_A,0,0);
    for(uint16_t y=0;y<rows;y++,src+=VIEWWINDOWWIDTH,dest+=128) {
        uint32_t wordaddr=(uint32_t)src>>1;
        *ctrl=0x9300|VIEWWINDOWWIDTH; *ctrl=0x9400;
        *ctrl=0x9500|(wordaddr&255); *ctrl=0x9600|((wordaddr>>8)&255);
        *ctrl=0x9700|((wordaddr>>16)&127);
        volatile uint32_t command=VDP_DMA_VRAM_ADDR((uint32_t)dest);
        volatile uint16_t *words=(volatile uint16_t *)&command;
        *ctrl=words[0];
        /* The triggering second word MUST be a memory operand, as in SGDK. */
        __asm__ volatile("move.w %0,(%1)" : : "m"(words[1]),"a"(ctrl) : "cc","memory");
    }
    if(!taken) Z80_releaseBus();
    __asm__ volatile("move.w %0,%%sr" : : "d"(sr) : "cc","memory");
}
#else
static void R20_UploadRows(const uint16_t *src,uint16_t rows) {
    VDP_setTileMapDataRect(BG_A,src,0,0,VIEWWINDOWWIDTH,rows,VIEWWINDOWWIDTH,DMA);
}
#endif
#if defined(DOOM_R20_VBLANK_VIDEO)
#if defined(DOOM_R21_V2_HEAPBUF)
#if !defined(DOOM_R21_NO_VDP_INIT)
#error DOOM_R21_V2_HEAPBUF needs DOOM_R21_NO_VDP_INIT (no 3 KB font unpack after boot)
#endif
/* R21 V2c: a static 2128-byte snapshot shrinks the SGDK heap before boot;
 * SGDK's internal_reset() then fails VDP_init()'s 3082-byte font unpack
 * (MEM_init -> DMA_init -> VDP_init), i.e. the ROM stops before main().
 * Allocate the snapshot from the SGDK heap after boot instead. */
static uint16_t *r20_video_copy;
void I_R21_AllocVideoCopy(void)
{
    if (!r20_video_copy)
        r20_video_copy = MEM_alloc(VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS * sizeof(uint16_t));
    if (!r20_video_copy)
        I_Error("R21 V2c: no SGDK heap for %u B", (unsigned)(VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS * 2));
}
#else
static uint16_t r20_video_copy[VIEWWINDOWWIDTH*VDP_DISPLAY_ROWS];
#endif
static volatile uint16_t r20_video_ready;
static uint16_t r20_video_rows;
static int8_t r20_video_palette=100, r20_next_palette=100;
static uint32_t r20_video_queued_vb;
void R20_VBlankVideo(void) {
    if(!r20_video_ready) return;
    /* NTSC raw V counter: start early enough to fit the transfer in blank.
       Late callbacks leave the immutable pending snapshot for next VBlank. */
    uint16_t line=(*(volatile uint16_t *)0xC00008)>>8;
    if(line<224 || line>232) return;
    R20_PROBE();
    if(r20_video_palette!=100) I_UploadNewPalette(r20_video_palette);
    R20_UploadRows(r20_video_copy,r20_video_rows);
    __asm__ volatile("" : : : "memory");
    r20_video_ready=0;
}
static void R20_WaitVideo(void) {
    while(r20_video_ready) {
        if(_g_vblankCount-r20_video_queued_vb>180)
            I_Error("R20g DMA: VBlank timeout");
    }
}
void R20_AbortVideo(void) {
    uint16_t sr;
    __asm__ volatile("move.w %%sr,%0\n\tori.w #0x700,%%sr" : "=d"(sr) : : "cc","memory");
    r20_video_ready=0; r20_next_palette=100;
    __asm__ volatile("move.w %0,%%sr" : : "d"(sr) : "cc","memory");
}
void R20_StopVideo(void) {
    R20_WaitVideo();
    r20_next_palette=100;
}
static void R20_Present(uint16_t rows) {
    R20_WaitVideo();
    _fmemcpy(r20_video_copy,_s_screen,rows*VIEWWINDOWWIDTH*sizeof(uint16_t));
    r20_video_rows=rows;
    r20_video_palette=r20_next_palette; r20_next_palette=100;
    r20_video_queued_vb=_g_vblankCount;
    __asm__ volatile("" : : : "memory");
    r20_video_ready=1;
}
#elif defined(DOOM_R20_DMA_BATCH)
static void R20_Present(uint16_t rows) { R20_UploadRows(_s_screen,rows); }
#endif

void I_FinishUpdate(void)
{
#if defined(DOOM_ROUTINE_PROFILE)
    doom_profile_stage = 5;
#endif
#if defined(DOOM_PROFILE)
    uint32_t start_vb = _g_vblankCount;
#endif
	/* Diagnostic only: permit the renderer to run without explicit frame pacing. */
#if !defined(DOOM_NO_VSYNC)
	VDP_waitVSync();
#endif

	if (newpal != NO_PALETTE_CHANGE)
	{
#if defined(DOOM_R20_VBLANK_VIDEO)
        r20_next_palette=newpal;
#else
		I_UploadNewPalette(newpal);
#endif
		newpal = NO_PALETTE_CHANGE;
	}

	I_DrawDebugCounters();   // 右上に VBLANK/フレーム/FPS を重畳
#if defined(DOOM_R20_STACKGUARD)
    {
        static uint8_t sample;
        R20_PROBE();
        if ((sample++ & 15u) == 0u) R20_DiagSample();
        if (_g_gamestate == GS_LEVEL) {
            for (uint16_t x = 0; x < VIEWWINDOWWIDTH; x++) hud_putc(x, 0, ' ');
            hud_putc(0, 0, 'T'); hud_num(1, 0, (uint16_t)_g_gametic, 5);
            hud_putc(7, 0, 'S'); hud_num(8, 0, r20_peak, 4);
            hud_putc(13, 0, 'E'); hud_num(14, 0, r20_errors, 2);
            hud_putc(17, 0, 'H'); hud_num(18, 0, r20_sgdk_free, 5);
            hud_putc(24, 0, 'Z'); hud_num(25, 0, r20_zone_free, 5);
        }
    }
#endif
#if defined(DOOM_CLASSIC_TEXT_HUD) && !defined(DOOM_R20_HUD_LAZY)
    I_DrawClassicTextHUD();
#endif

#if defined(DOOM_HUD_DMA_STATUS_ONLY)
    /* Single-DMA, minimal-state diagnostic based on the successful
     * 24-row-only ROM. No 304-byte lastHud array, no extra VDP writes.
     * Status fields are precisely those printed in the black HUD strip. */
    {
        static uint16_t previousHealth;
        static uint16_t previousArmor;
        static uint16_t previousBullets;
        static uint8_t previousLevel;
        static uint8_t initialized;

        uint8_t level = _g_gamestate == GS_LEVEL;
        uint16_t health = level
            ? hud_saturate3(_g_player.mo ? _g_player.mo->health : _g_player.health)
            : 0;
        uint16_t armor = level ? hud_saturate3(_g_player.armorpoints) : 0;
        uint16_t bullets = level ? hud_saturate3(_g_player.ammo[am_clip]) : 0;
        uint8_t changed = !initialized || previousLevel != level
            || previousHealth != health || previousArmor != armor
            || previousBullets != bullets
#if defined(DOOM_R20_HUD_LAZY)
            || r20_hud_dirty
#endif
            ;
#if defined(DOOM_R20_HUD_LAZY)
        if (changed) I_DrawClassicTextHUD();
        r20_hud_dirty = 0;
#endif

        previousHealth = health;
        previousArmor = armor;
        previousBullets = bullets;
        previousLevel = level;
        initialized = 1;

#if defined(DOOM_R11_TOPBAR_DMA)
        /* The row is black except for FPS and optional text messages.
           Compare the actual tile words (not just FPS) so that gameplay
           messages, automap transitions and future telemetry still update.
           If unchanged, transfer only rows 1..23, or 1..27 when HUD changes. */
        static uint16_t lastTopRow[VIEWWINDOWWIDTH];
        static uint8_t topRowInitialized;
        uint8_t topRowChanged = !topRowInitialized;
        if (level)
        {
            for (uint16_t x = 0; x < VIEWWINDOWWIDTH; x++)
            {
                if (_s_screen[x] != lastTopRow[x])
                    topRowChanged = 1;
                lastTopRow[x] = _s_screen[x];
            }
            topRowInitialized = 1;
        }
        else
            topRowInitialized = 0;

        if (level && !topRowChanged)
            VDP_setTileMapDataRect(BG_A, &_s_screen[VIEWWINDOWWIDTH],
                                   0, 1, VIEWWINDOWWIDTH,
                                   changed ? VDP_DISPLAY_ROWS - 1 : VIEWWINDOWHEIGHT - 1,
                                   VIEWWINDOWWIDTH, DMA);
        else
#endif
#if defined(DOOM_R20_VBLANK_VIDEO) || defined(DOOM_R20_DMA_BATCH)
            R20_Present(changed ? VDP_DISPLAY_ROWS : VIEWWINDOWHEIGHT);
#else
            VDP_setTileMapDataRect(BG_A, _s_screen, 0, 0,
                                   VIEWWINDOWWIDTH,
                                   changed ? VDP_DISPLAY_ROWS : VIEWWINDOWHEIGHT,
                                   VIEWWINDOWWIDTH, DMA);
#endif
    }
#elif defined(DOOM_HUD_DMA24)
    /* The 3D framebuffer has 24 rows (DMA). The status strip is
     * CPU-updated only for changed tilemap rows, avoiding multi-DMA. */
    VDP_setTileMapDataRect(BG_A, _s_screen, 0, 0,
                           VIEWWINDOWWIDTH, VIEWWINDOWHEIGHT,
                           VIEWWINDOWWIDTH, DMA);
#if !defined(DOOM_HUD_DMA24_NOHUDWRITE)
    {
        static uint16_t lastHud[4 * VIEWWINDOWWIDTH];
        static uint8_t hudInitialized = 0;
        for (uint16_t row = 0; row < 4; row++)
        {
            const uint16_t *src = &_s_screen[(VIEWWINDOWHEIGHT + row) * VIEWWINDOWWIDTH];
            uint16_t *old = &lastHud[row * VIEWWINDOWWIDTH];
            uint8_t changed = !hudInitialized;
            for (uint16_t x = 0; x < VIEWWINDOWWIDTH; x++)
            {
                if (src[x] != old[x]) changed = 1;
                old[x] = src[x];
            }
            if (changed)
                /* CPU-write the few dirty HUD cells. This avoids issuing
                 * several more DMA requests during a NO_VSYNC frame. */
                VDP_setTileMapDataRect(BG_A, src, 0,
                                       VIEWWINDOWHEIGHT + row,
                                       VIEWWINDOWWIDTH, 1,
                                       VIEWWINDOWWIDTH, CPU);
        }
        hudInitialized = 1;
    }
#endif
#else
	VDP_setTileMapDataRect(BG_A, _s_screen, 0, 0,
	                       VIEWWINDOWWIDTH, VDP_DISPLAY_ROWS,
	                       VIEWWINDOWWIDTH, DMA);
#endif
#if defined(DOOM_PROFILE)
    prof_vdp_vb += _g_vblankCount - start_vb;
#endif
#if defined(DOOM_ROUTINE_PROFILE)
    doom_profile_stage = 0;
#endif
#if defined(TIMEDEMO)
	I_BenchmarkFrame();
#endif
}


//**************************************************************************************
//
// Column / span rendering （ハード非依存。i_neogev.c とほぼ同一だが uint16 stride=W）
//

#define COLEXTRABITS (8 - 1)
#define COLBITS (8 + 1)

/* R20 S4: keep the column writers out of line in every A/B variant, so that
 * a change inside them cannot change LTO inlining in R_Subsector (measured
 * with GCC 13: the R19 asm variant was inlined, the C variant was not). */
#if defined(DOOM_R20_NOINLINE_COLUMNS)
#define R20_COLFN __attribute__((noinline))
#else
#define R20_COLFN
#endif


R20_COLFN void R_DrawColumnSprite(const draw_column_vars_t *dcvars)
{
	int16_t count = (dcvars->yh - dcvars->yl) + 1;
	if (count <= 0)
		return;
    R20_COUNT(R20C_TEX_CALLS, 1);
    R20_COUNT(R20C_TEX_CELLS, count);

	const uint8_t *source   = dcvars->source;
	const uint8_t *colormap = dcvars->colormap;

	uint16_t *dest = R20_DEST(dcvars->x, dcvars->yl);

	const uint16_t fracstep = dcvars->fracstep;
#if defined(DOOM_R17_FRAC_MULU)
    /*
     * R17: only the low 16 bits of the initial texture fraction survive.
     * For signed delta (yl-CENTERY), unsigned MULU.W on its low word is
     * bit-exact modulo 65536, including negative deltas and step=65535.
     * Avoid generic signed 32x32 multiplication on the MC68000.
     */
    uint32_t row_product = (uint16_t)(dcvars->yl - CENTERY);
    __asm__ ("mulu.w %1,%0"
             : "+&d" (row_product)
             : "d" (fracstep)
             : "cc");
    uint16_t frac = (uint16_t)((dcvars->texturemid >> COLEXTRABITS) + (uint16_t)row_product);
#else
	uint16_t frac = (dcvars->texturemid >> COLEXTRABITS) + (dcvars->yl - CENTERY) * fracstep;
#endif
	const uint8_t colbits = COLBITS;

#if defined(DOOM_CELL_LUT)
    /*
     * One bounds-checked selection per wall/sprite column; the inner pixel
     * loop performs a single 16-bit lookup instead of two chained lookups.
     * Use original path for any colormap not in the standard COLORMAP lump.
     * The tile palette is constant across PLAYPAL flash changes; those
     * change CRAM only, so this mapping remains correct.
     */
#if defined(DOOM_R20_CELLMAP_MEMO)
    /*
     * R20 R2: the colormap only changes per seg / per sprite, but the
     * validation below ran for every column. Remember the last answer.
     * NULL means "not a standard COLORMAP row": original C fallback.
     * Valid because fullcolormap is set once in R_InitColormaps.
     */
    static const uint8_t  *r20_last_colormap;
    static const uint16_t *r20_last_cellmap;
    const uint16_t *cellmap;
    if (colormap == r20_last_colormap)
        cellmap = r20_last_cellmap;
    else
    {
        cellmap = NULL;
        if (colormap && fullcolormap)
        {
            const uintptr_t offset = (uintptr_t)colormap - (uintptr_t)fullcolormap;
            if (offset < (32u * 256u) && (offset & 255u) == 0u)
                cellmap = doom_colormap_cells[offset >> 8];
        }
        r20_last_colormap = colormap;
        r20_last_cellmap = cellmap;
    }
    if (cellmap)
    {
        {
#else
    if (colormap && fullcolormap)
    {
        const uintptr_t offset = (uintptr_t)colormap - (uintptr_t)fullcolormap;
        if (offset < (32u * 256u) && (offset & 255u) == 0u)
        {
            const uint16_t *cellmap = doom_colormap_cells[offset >> 8];
#endif
#if defined(DOOM_R20_PIXEL_ADDX)
            /*
             * R20 P2: same contract as R17 (frac mod 65536, texel = frac>>9),
             * with integer and fraction in two registers:
             *   ip = frac>>9 (0..127), fl = frac<<7 (low 9 bits on top).
             * ADD.W fl sets X exactly when the low 9 bits overflow; ADDX.W
             * adds step>>9 plus that carry; AND keeps 7 bits (mod 128).
             * Musashi: 70 cycles/cell vs 106 (R17); about +108 per call.
             * Equivalence: 605 random/edge columns, 0 differences.
             */
            uint16_t n20 = (uint16_t)count - 1;
            uint16_t ip = frac, fl = frac;
            uint16_t si = fracstep, sl = fracstep;
            uint16_t t20;
#if defined(DOOM_R20_PIXEL_UNROLL)
            if (count <= 22) {
                void *end20;
                n20 = (uint16_t)(-22 * count);
            __asm__ volatile(
                "lsl.w  #7,%[fl]\n\t"
                "rol.w  #7,%[ip]\n\t"
                "and.w  %[k],%[ip]\n\t"
                "lsl.w  #7,%[sl]\n\t"
                "rol.w  #7,%[si]\n\t"
                "and.w  %[k],%[si]\n\t"
                "lea 2f(%%pc),%[end]\n\t"
                "jmp (%[end],%[n].w)\n\t"
                ".rept 22\n\t"
                "moveq  #0,%[t]\n\t"
                "move.b (%[s],%[ip].w),%[t]\n\t"
                "add.w  %[t],%[t]\n\t"
                "move.w (%[m],%[t].w),(%[d])\n\t"
                "lea    76(%[d]),%[d]\n\t"
                "add.w  %[sl],%[fl]\n\t"
                "addx.w %[si],%[ip]\n\t"
                "and.w  %[k],%[ip]\n\t"
                ".endr\n2:"
                : [end] "=&a" (end20), [d] "+&a" (dest),
                  [fl] "+&d" (fl), [ip] "+&d" (ip),
                  [sl] "+&d" (sl), [si] "+&d" (si),
                  [n] "+&d" (n20), [t] "=&d" (t20)
                : [s] "a" (source), [m] "a" (cellmap),
                  [k] "d" ((uint16_t)127)
                : "cc", "memory");
            return;
            }
#endif
            __asm__ volatile(
                "lsl.w  #7,%[fl]\n\t"
                "rol.w  #7,%[ip]\n\t"
                "and.w  %[k],%[ip]\n\t"
                "lsl.w  #7,%[sl]\n\t"
                "rol.w  #7,%[si]\n\t"
                "and.w  %[k],%[si]\n\t"
                "1:\n\t"
                "moveq  #0,%[t]\n\t"
                "move.b (%[s],%[ip].w),%[t]\n\t"
                "add.w  %[t],%[t]\n\t"
                "move.w (%[m],%[t].w),(%[d])\n\t"
                "lea    76(%[d]),%[d]\n\t"
                "add.w  %[sl],%[fl]\n\t"
                "addx.w %[si],%[ip]\n\t"
                "and.w  %[k],%[ip]\n\t"
                "dbra   %[n],1b"
                : [d] "+&a" (dest),
                  [fl] "+&d" (fl), [ip] "+&d" (ip),
                  [sl] "+&d" (sl), [si] "+&d" (si),
                  [n] "+&d" (n20), [t] "=&d" (t20)
                : [s] "a" (source), [m] "a" (cellmap),
                  [k] "d" ((uint16_t)127)
                : "cc", "memory");
            return;
#elif defined(DOOM_R17_PIXEL_DBRA)
            /*
             * R17: exact MC68000 DBRA loop for the standard COLORMAP.
             * frac is 16-bit modulo 65536, texel index is frac>>9.
             * Lookup is byte-indexed source -> 16-bit VDP tilemap word.
             * Index is zero-extended after MOVE.B; cellmap index is
             * doubled because its entries are words. 38*2=76-byte stride.
             * Non-standard/fixed colormaps retain the original C fallback.
             */
            uint16_t loopcount = (uint16_t)count;
            uint16_t idx;
            __asm__ volatile(
                "subq.w #1,%[n]\n\t"
                "1:\n\t"
                "move.w %[f],%[i]\n\t"
                "lsr.w #8,%[i]\n\t"
                "lsr.w #1,%[i]\n\t"
                "move.b (%[s],%[i].w),%[i]\n\t"
                "andi.w #255,%[i]\n\t"
                "add.w %[i],%[i]\n\t"
                "move.w (%[m],%[i].w),(%[d])\n\t"
#if defined(DOOM_R20_LEA_STRIDE)
                /* R20 P1: LEA d16(An),An (8 cycles) replaces ADDA.W #imm,An. */
                "lea 76(%[d]),%[d]\n\t"
#else
                "adda.w #76,%[d]\n\t"
#endif
                "add.w %[step],%[f]\n\t"
                "dbra %[n],1b"
                : [d] "+&a" (dest),
                  [f] "+&d" (frac),
                  [n] "+&d" (loopcount),
                  [i] "=&d" (idx)
                : [s] "a" (source),
                  [m] "a" (cellmap),
                  [step] "d" (fracstep)
                : "cc", "memory");
            return;
#elif defined(DOOM_R8_LUT_UNROLL) && (DOOM_R8_LUT_UNROLL == 2 || DOOM_R8_LUT_UNROLL == 4)
            /* Exact 16-bit frac stepping; no change to colour, texels or clipping.
               Tests only the fast Color LUT path (the normal fall-back is untouched). */
            while (count >= DOOM_R8_LUT_UNROLL)
            {
#if DOOM_R8_LUT_UNROLL >= 1
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
#endif
#if DOOM_R8_LUT_UNROLL >= 2
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
#endif
#if DOOM_R8_LUT_UNROLL >= 3
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
#endif
#if DOOM_R8_LUT_UNROLL >= 4
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
#endif
                count -= DOOM_R8_LUT_UNROLL;
            }
            while (count-- > 0)
            {
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
            }
#else
            do
            {
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
            } while (--count);
#endif
            return;
        }
    }
#endif

#if defined(DOOM_UNROLL_COLUMNS)
    /* Two pixels per loop, identical 16-bit fractional wraparound. */
    while (count >= 2)
    {
        *dest = colorcell[colormap[source[frac >> colbits]]];
        dest += VIEWWINDOWWIDTH;
        frac += fracstep;
        *dest = colorcell[colormap[source[frac >> colbits]]];
        dest += VIEWWINDOWWIDTH;
        frac += fracstep;
        count -= 2;
    }
    if (count)
        *dest = colorcell[colormap[source[frac >> colbits]]];
#else
	do
	{
		*dest = colorcell[colormap[source[frac >> colbits]]];
		dest += VIEWWINDOWWIDTH;
		frac += fracstep;
	} while (--count);
#endif
}


void R_DrawColumnWall(const draw_column_vars_t *dcvars)
{
	R_DrawColumnSprite(dcvars);
}


R20_COLFN void R_DrawColumnFlat(uint8_t color, const draw_column_vars_t *dcvars)
{
	int16_t count = (dcvars->yh - dcvars->yl) + 1;
	if (count <= 0)
		return;
    R20_COUNT(R20C_FLAT_CALLS, 1);
    R20_COUNT(R20C_FLAT_CELLS, count);

	uint16_t cell = colorcell[color];
#if defined(DOOM_R20_FLAT_UNROLL)
    uint16_t *dest = &_s_screen[r20_rowofs[(uint16_t)dcvars->yl] + (uint16_t)dcvars->x];
#else
	uint16_t *dest = R20_DEST(dcvars->x, dcvars->yl);
#endif

#if defined(DOOM_R20_FLAT_UNROLL)
#if VIEWWINDOWWIDTH != 38
#error R20 flat unroll uses the 76-byte row stride
#endif
    /*
     * R20 R3: 22 MOVE.W Dn,d16(An) stores with a computed entry point,
     * 12 cycles per cell instead of 32 and no loop counter. The pointer is
     * biased by -76 so that no displacement is zero (the assembler would
     * shrink a 0(An) store to (An) and break the 4-byte spacing).
     * Rows are written bottom-up; a solid colour does not care.
     * Equivalence: 400 random columns vs the C loop, 0 differences.
     */
    if (count <= 22)
    {
        int16_t off = (int16_t)(-4 * count);
        __asm__ volatile(
            "lea    -76(%[d]),%[d]\n\t"
            "jmp    (2f,%%pc,%[o].w)\n\t"
            "move.w %[c],1672(%[d])\n\t"  "move.w %[c],1596(%[d])\n\t"
            "move.w %[c],1520(%[d])\n\t"  "move.w %[c],1444(%[d])\n\t"
            "move.w %[c],1368(%[d])\n\t"  "move.w %[c],1292(%[d])\n\t"
            "move.w %[c],1216(%[d])\n\t"  "move.w %[c],1140(%[d])\n\t"
            "move.w %[c],1064(%[d])\n\t"  "move.w %[c],988(%[d])\n\t"
            "move.w %[c],912(%[d])\n\t"   "move.w %[c],836(%[d])\n\t"
            "move.w %[c],760(%[d])\n\t"   "move.w %[c],684(%[d])\n\t"
            "move.w %[c],608(%[d])\n\t"   "move.w %[c],532(%[d])\n\t"
            "move.w %[c],456(%[d])\n\t"   "move.w %[c],380(%[d])\n\t"
            "move.w %[c],304(%[d])\n\t"   "move.w %[c],228(%[d])\n\t"
            "move.w %[c],152(%[d])\n\t"   "move.w %[c],76(%[d])\n"
            "2:"
            : [d] "+&a" (dest)
            : [c] "d" (cell), [o] "d" (off)
            : "cc", "memory");
        return;
    }
#endif

#if defined(DOOM_R19_FLAT_DBRA)
    uint16_t n19 = (uint16_t)count - 1;
    __asm__ volatile (
        "1:\n\tmove.w %[c],(%[d])\n\tadda.w #76,%[d]\n\tdbra %[n],1b"
        : [d] "+&a" (dest), [n] "+&d" (n19)
        : [c] "d" (cell) : "cc", "memory");
#elif defined(DOOM_UNROLL_COLUMNS)
    /* Fixed-color spans: four writes with one loop branch. */
    while (count >= 4)
    {
        dest[0] = cell;
        dest[VIEWWINDOWWIDTH] = cell;
        dest[2 * VIEWWINDOWWIDTH] = cell;
        dest[3 * VIEWWINDOWWIDTH] = cell;
        dest += 4 * VIEWWINDOWWIDTH;
        count -= 4;
    }
    while (count-- > 0)
    {
        *dest = cell;
        dest += VIEWWINDOWWIDTH;
    }
#else
	do
	{
		*dest = cell;
		dest += VIEWWINDOWWIDTH;
	} while (--count);
#endif
}


void R_DrawFuzzColumn(const draw_column_vars_t *dcvars)
{
	// TODO: ファジー(不可視)描画。とりあえずスプライトと同じ。
	R_DrawColumnSprite(dcvars);
}


//**************************************************************************************
//
// Full-screen / background images
//

void V_DrawRawFullScreen(int16_t num)
{
    R20_InvalidateVideo();
	const uint8_t *lump = W_GetLumpByNum(num);

	static const fixed_t DXI = ((fixed_t)SCREENWIDTH  << FRACBITS) / VIEWWINDOWWIDTH;
	static const fixed_t DYI = ((fixed_t)SCREENHEIGHT << FRACBITS) / VIEWWINDOWHEIGHT;

	uint16_t *dst = &_s_screen[0];
	fixed_t y = 0;
	for (int h = 0; h < VIEWWINDOWHEIGHT; h++)
	{
		fixed_t x = 0;
		for (int w = 0; w < VIEWWINDOWWIDTH; w++)
		{
			*dst++ = colorcell[lump[(y >> FRACBITS) * SCREENWIDTH + (x >> FRACBITS)]];
			x += DXI;
		}
		y += DYI;
	}
}


void V_DrawBackground(int16_t backgroundnum)
{
    R20_InvalidateVideo();
	// メニュー/ヘルプ背景。チャンキー FB では黒で塗ってテキストを読みやすくする。
	(void)backgroundnum;
	for (int i = 0; i < VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT; i++)
		_s_screen[i] = BLACK_CELL;
}


void V_ClearViewWindow(void)
{
    R20_InvalidateVideo();
	for (int i = 0; i < VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT; i++)
		_s_screen[i] = BLACK_CELL;
}


//**************************************************************************************
//
// Text / HUD （各セルに SGDK 内蔵フォントのグリフタイルを書き込む）
//

void V_DrawCharacter(int16_t x, int16_t y, uint8_t color, char c)
{
#if defined(DOOM_R20_FPS_LAZY)
    if (y == 0) r20_fps_dirty = 1;
#endif
	if ((uint16_t)x < VIEWWINDOWWIDTH && (uint16_t)y < VIEWWINDOWHEIGHT)
		_s_screen[y * VIEWWINDOWWIDTH + x] = font_cell(color, c);
}

void V_DrawSTCharacter(int16_t x, int16_t y, uint8_t color, char c)
{
	V_DrawCharacter(x, y, color, c);
}

void V_DrawCharacterForeground(int16_t x, int16_t y, uint8_t color, char c)
{
	V_DrawCharacter(x, y, color, c);
}

void V_DrawString(int16_t x, int16_t y, uint8_t color, const char* s)
{
#if defined(DOOM_R20_FPS_LAZY)
    if (y == 0) r20_fps_dirty = 1;
#endif
	if ((uint16_t)y >= VIEWWINDOWHEIGHT)
		return;
	while (*s)
	{
		if ((uint16_t)x < VIEWWINDOWWIDTH)
			_s_screen[y * VIEWWINDOWWIDTH + x] = font_cell(color, *s);
		s++;
		x++;
	}
}

void V_DrawSTString(int16_t x, int16_t y, uint8_t color, const char* s)
{
	V_DrawString(x, y, color, s);
}

void V_ClearString(int16_t y, size_t len)
{
#if defined(DOOM_R20_FPS_LAZY)
    if (y == 0) r20_fps_dirty = 1;
#endif
	if ((uint16_t)y >= VIEWWINDOWHEIGHT)
		return;
	uint16_t *d = &_s_screen[y * VIEWWINDOWWIDTH];
	for (size_t i = 0; i < len && i < VIEWWINDOWWIDTH; i++)
		d[i] = BLACK_CELL;
}


//**************************************************************************************
//
// Lines (automap) / screen pages / wipe
//

void V_InitDrawLine(void)      { }
void V_ShutdownDrawLine(void)  { }

void V_DrawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, uint8_t color)
{
	uint16_t cell = colorcell[color];
	int dx =  abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
	int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
	int err = dx + dy;
	for (;;)
	{
        if ((uint16_t)x0 < VIEWWINDOWWIDTH && (uint16_t)y0 < VIEWWINDOWHEIGHT
#if defined(DOOM_R11_TOPBAR_CLIP)
            && (_g_gamestate != GS_LEVEL || y0 != 0)
#endif
#if defined(DOOM_R11_LEFTCOL_CLIP)
            && (_g_gamestate != GS_LEVEL || x0 != 0)
#endif
           )
            _s_screen[y0 * VIEWWINDOWWIDTH + x0] = cell;
		if (x0 == x1 && y0 == y1)
			break;
		int e2 = 2 * err;
		if (e2 >= dy) { err += dy; x0 += sx; }
		if (e2 <= dx) { err += dx; y0 += sy; }
	}
}


void I_InitScreenPage(void)
{
	V_ClearViewWindow();
}


void I_InitScreenPages(void)
{
	V_ClearViewWindow();
}


void wipe_StartScreen(void)
{
	I_InitScreenPages();
}


void D_Wipe(void)
{
	// TODO: 画面ワイプ。今は即時更新。
	I_FinishUpdate();
}

#endif /* DOOM_R22_PIXEL4 */
