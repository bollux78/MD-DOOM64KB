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


extern const int16_t CENTERY;

// 16 個のベタ塗りタイルを置く VRAM 先頭 index
#define SOLID_TILE_INDEX  TILE_USER_INDEX

#if defined(DOOM_CELL_LUT)
/* 32 x 256 tilemap words in ROM; built from WAD COLORMAP and genpal_cell. */
#include "colormap_cells.h"
extern const uint8_t *fullcolormap;
#endif

// チャンキー FB。各要素は完成済み VDP タイルマップ語。
static uint16_t _s_screen[VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT];

// Doom 8bit 色 index -> VDP タイルマップ語
static uint16_t colorcell[256];

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

#define HUD_COL 15   // 白(PAL0 index15)

static void hud_putc(int16_t cx, int16_t cy, char c)
{
	if ((uint16_t)cx < VIEWWINDOWWIDTH && (uint16_t)cy < VIEWWINDOWHEIGHT)
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

	// FPS はゲーム画面(GS_LEVEL)のときだけ表示する（タイトル/メニュー/集計画面では出さない）。
	if (_g_gamestate != GS_LEVEL)
		return;

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
#if defined(DOOM_ROUTINE_PROFILE)
    I_ProfileSampleReset();
#endif
#if defined(DOOM_PROFILE)
    prof_logic_vb = prof_render_vb = prof_vdp_vb = 0;
#endif
}

static void I_BenchmarkFrame(void)
{
    if (!bench_active) return;
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
    bench_active = false;
    uint32_t elapsed = _g_vblankCount - bench_start_vb;
    if (!elapsed) elapsed = 1;
    uint32_t avg_x100 = (bench_frames * 6000u + elapsed / 2) / elapsed;
    uint32_t seconds_x100 = (elapsed * 100u + 30u) / 60u;
    char buffer[16];

    VDP_init();
    VDP_setTextPalette(PAL0);
    PAL_setColor(15, 0x0EEE);
    #if defined(DOOM_ROUTINE_PROFILE)
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
#else
    VDP_drawText("MIN/MAX: FULL 1S WINDOWS", 3, 23);
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
	VDP_setScreenWidth320();
	VDP_setPlaneSize(64, 32, TRUE);

	I_BuildSolidTiles();

	// 256 色 -> セル語 LUT を構築
	for (uint16_t i = 0; i < 256; i++)
		colorcell[i] = cell_for_color((uint8_t)i);

	I_ReloadPalette();
	I_UploadNewPalette(0);
	newpal = NO_PALETTE_CHANGE;

	// 画面を黒で埋める
	for (int i = 0; i < VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT; i++)
		_s_screen[i] = BLACK_CELL;
}


void I_ShutdownGraphics(void)
{
	// Do nothing
}


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
		I_UploadNewPalette(newpal);
		newpal = NO_PALETTE_CHANGE;
	}

	I_DrawDebugCounters();   // 右上に VBLANK/フレーム/FPS を重畳

	VDP_setTileMapDataRect(BG_A, _s_screen, 0, 0,
	                       VIEWWINDOWWIDTH, VIEWWINDOWHEIGHT,
	                       VIEWWINDOWWIDTH, DMA);
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


void R_DrawColumnSprite(const draw_column_vars_t *dcvars)
{
	int16_t count = (dcvars->yh - dcvars->yl) + 1;
	if (count <= 0)
		return;

	const uint8_t *source   = dcvars->source;
	const uint8_t *colormap = dcvars->colormap;

	uint16_t *dest = &_s_screen[dcvars->yl * VIEWWINDOWWIDTH + dcvars->x];

	const uint16_t fracstep = dcvars->fracstep;
	uint16_t frac = (dcvars->texturemid >> COLEXTRABITS) + (dcvars->yl - CENTERY) * fracstep;
	const uint8_t colbits = COLBITS;

#if defined(DOOM_CELL_LUT)
    /*
     * One bounds-checked selection per wall/sprite column; the inner pixel
     * loop performs a single 16-bit lookup instead of two chained lookups.
     * Use original path for any colormap not in the standard COLORMAP lump.
     * The tile palette is constant across PLAYPAL flash changes; those
     * change CRAM only, so this mapping remains correct.
     */
    if (colormap && fullcolormap)
    {
        const uintptr_t offset = (uintptr_t)colormap - (uintptr_t)fullcolormap;
        if (offset < (32u * 256u) && (offset & 255u) == 0u)
        {
            const uint16_t *cellmap = doom_colormap_cells[offset >> 8];
            do
            {
                *dest = cellmap[source[frac >> colbits]];
                dest += VIEWWINDOWWIDTH;
                frac += fracstep;
            } while (--count);
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


void R_DrawColumnFlat(uint8_t color, const draw_column_vars_t *dcvars)
{
	int16_t count = (dcvars->yh - dcvars->yl) + 1;
	if (count <= 0)
		return;

	uint16_t cell = colorcell[color];
	uint16_t *dest = &_s_screen[dcvars->yl * VIEWWINDOWWIDTH + dcvars->x];

#if defined(DOOM_UNROLL_COLUMNS)
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
	// メニュー/ヘルプ背景。チャンキー FB では黒で塗ってテキストを読みやすくする。
	(void)backgroundnum;
	for (int i = 0; i < VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT; i++)
		_s_screen[i] = BLACK_CELL;
}


void V_ClearViewWindow(void)
{
	for (int i = 0; i < VIEWWINDOWWIDTH * VIEWWINDOWHEIGHT; i++)
		_s_screen[i] = BLACK_CELL;
}


//**************************************************************************************
//
// Text / HUD （各セルに SGDK 内蔵フォントのグリフタイルを書き込む）
//

void V_DrawCharacter(int16_t x, int16_t y, uint8_t color, char c)
{
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
		if ((uint16_t)x0 < VIEWWINDOWWIDTH && (uint16_t)y0 < VIEWWINDOWHEIGHT)
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
