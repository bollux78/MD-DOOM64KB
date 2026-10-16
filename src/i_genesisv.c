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
#if defined(DOOM_HUD_DOOMSTYLE_TEST)
#include "d_items.h" /* weaponinfo: current weapon's ammunition type */
#if defined(DOOM_HUD_WAD_ATLAS)
#include "doom_wad_hud_tiles.h"
#endif
#endif
#include "gen_pal.h"

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
#if defined(DOOM_HUD_DOOMSTYLE_TEST)
/* Sixteen original solid tiles already occupy USER_INDEX+0..15.
 * Reserve 4 decorative tiles + 16 face tiles once at boot. */
#define HUD_METAL_TILE   (SOLID_TILE_INDEX + 16)
#define HUD_TOP_TILE     (SOLID_TILE_INDEX + 17)
#define HUD_BOTTOM_TILE  (SOLID_TILE_INDEX + 18)
#define HUD_SEAM_TILE    (SOLID_TILE_INDEX + 19)
#define HUD_FACE_TILE    (SOLID_TILE_INDEX + 20)
#endif

#if defined(DOOM_CELL_LUT)
/* 32 x 256 tilemap words in ROM; built from WAD COLORMAP and genpal_cell. */
#include "colormap_cells.h"
extern const uint8_t *fullcolormap;
#endif

// チャンキー FB。各要素は完成済み VDP タイルマップ語。
/* In classic-HUD mode, 3D renders 24 rows but DMA presents 28 rows.
 * The bottom four rows never enter the 3D renderer. */
#if defined(DOOM_CLASSIC_TEXT_HUD)
#if VIEWWINDOWHEIGHT != 24 || VIEWWINDOWWIDTH != 38
#error DOOM_CLASSIC_TEXT_HUD requires 38x24 3D viewport
#endif
#define VDP_DISPLAY_ROWS 28
#else
#define VDP_DISPLAY_ROWS VIEWWINDOWHEIGHT
#endif
static uint16_t _s_screen[VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS];

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
#if defined(DOOM_HUD_DOOMSTYLE_TEST)
/* 32x32 static monochrome portrait. Bit 31 is the leftmost pixel.
 * Pal3/15 is the existing gray HUD text color. No PAL writes or
 * per-frame VRAM tile generation. Static test artwork, not WAD STFACE. */
#if !defined(DOOM_HUD_WAD_ATLAS)
static const uint32_t doom_hud_face_rows[32] = {
    0x7ffffffeu, /* row 0 */
    0x80000001u, /* row 1 */
    0x80000001u, /* row 2 */
    0x803ffc01u, /* row 3 */
    0x81ffff81u, /* row 4 */
    0x87ffffe1u, /* row 5 */
    0x8ffffff1u, /* row 6 */
    0x8ffffff1u, /* row 7 */
    0x8ffffff1u, /* row 8 */
    0x8bffffd1u, /* row 9 */
    0x8bffffd1u, /* row 10 */
    0x89ffff91u, /* row 11 */
    0x89000091u, /* row 12 */
    0x89f00f91u, /* row 13 */
    0x89000091u, /* row 14 */
    0x897e7e91u, /* row 15 */
    0x81381c81u, /* row 16 */
    0x81010081u, /* row 17 */
    0x81010081u, /* row 18 */
    0x81010081u, /* row 19 */
    0x81410281u, /* row 20 */
    0x8103c081u, /* row 21 */
    0x81000081u, /* row 22 */
    0x80000001u, /* row 23 */
    0x800ff001u, /* row 24 */
    0x8007e001u, /* row 25 */
    0x80000001u, /* row 26 */
    0x80000001u, /* row 27 */
    0x801ff801u, /* row 28 */
    0x800ff001u, /* row 29 */
    0x80000001u, /* row 30 */
    0x7ffffffeu, /* row 31 */
};

#endif /* !DOOM_HUD_WAD_ATLAS */

static uint16_t I_HudCurrentAmmo(void)
{
    const int16_t weapon = (int16_t)_g_player.readyweapon;
    if (weapon < 0 || weapon >= NUMWEAPONS) return 0;
    const ammotype_t type = weaponinfo[weapon].ammo;
    if ((int16_t)type < 0 || type >= NUMAMMO) return 0;
    return hud_saturate3(_g_player.ammo[type]);
}

static uint8_t I_HudKeys(void)
{
    return (uint8_t)((_g_player.cards[0] ? 1u : 0u)
        | (_g_player.cards[1] ? 2u : 0u)
        | (_g_player.cards[2] ? 4u : 0u));
}

/* This boot-only work uses one 8-word stack tile and an 128-byte ROM mask.
 * Do NOT allocate a 32x32 image in 64 KiB WRAM. */
static void I_BuildDoomStyleTiles(void)
{
#if defined(DOOM_HUD_WAD_ATLAS)
    /* One boot-time upload of the HUD tiles (188 or 211, no VBlank DMA).
     * No new framebuffer or per-frame VRAM uploads. */
    for (uint16_t tile = 0; tile < DOOM_WAD_HUD_TOTAL_TILES; tile++)
        VDP_loadTileData(doom_wad_hud_words[tile],
                         HUD_METAL_TILE + tile, 1, CPU);
#else
    uint32_t tile[8];
    for (uint16_t kind = 0; kind < 4u; kind++)
    {
        for (uint16_t y = 0; y < 8u; y++)
        {
            uint32_t row = 0;
            for (uint16_t x = 0; x < 8u; x++)
            {
                uint16_t on = 0;
                if (kind == 0u) /* riveted plate, alternating gray specks */
                    on = (y == 0u || y == 7u || ((x + (y & 1u)) % 4u == 0u));
                else if (kind == 1u) /* top bevel */
                    on = y <= 1u || (y == 3u && x == 3u);
                else if (kind == 2u) /* bottom bevel */
                    on = y >= 6u || (y == 4u && x == 4u);
                else /* vertical metal rib */
                    on = x == 0u || x == 1u || x == 7u;
                row = (row << 4) | (on ? 15u : 0u);
            }
            tile[y] = row;
        }
        VDP_loadTileData(tile, HUD_METAL_TILE + kind, 1, CPU);
    }

    /* Face tiles laid out 4x4, 4 bpp, 0=black 15=gray. */
    for (uint16_t tileY = 0; tileY < 4u; tileY++)
    for (uint16_t tileX = 0; tileX < 4u; tileX++)
    {
        for (uint16_t y = 0; y < 8u; y++)
        {
            const uint32_t bits = doom_hud_face_rows[tileY * 8u + y];
            uint32_t row = 0;
            for (uint16_t x = 0; x < 8u; x++)
            {
                const uint16_t bitX = tileX * 8u + x;
                row = (row << 4) | ((bits & (1UL << (31u - bitX))) ? 15u : 0u);
            }
            tile[y] = row;
        }
        VDP_loadTileData(tile, HUD_FACE_TILE + tileY * 4u + tileX, 1, CPU);
    }
#endif /* DOOM_HUD_WAD_ATLAS */
}

static void I_DoomStyleText(uint16_t x, uint16_t y, uint8_t color,
                             const char *value)
{
    while (*value && x < VIEWWINDOWWIDTH)
        _s_screen[y * VIEWWINDOWWIDTH + x++] = font_cell(color, *value++);
}

#if defined(DOOM_HUD_WAD_ATLAS)
static inline uint16_t I_WadHudCell(uint16_t source)
{
    return TILE_ATTR_FULL(doom_wad_hud_pal[source], 0, 0, 0,
                          HUD_METAL_TILE + source);
}

/* One 8x16 red-number glyph = two tiles. Changes are still picked up by
 * the existing health/armor/ammo conditional 28-row DMA. */
static void I_WadHudNum3(uint16_t x, uint16_t value)
{
    uint16_t hundreds = value / 100;
    uint16_t tens = (value / 10) % 10;
    uint16_t units = value % 10;
    const uint16_t digits[3] = {hundreds, tens, units};
    for (uint16_t i = 0; i < 3; i++)
    {
#if defined(DOOM_HUD_CELSO_ART)
        /* Celso's original 16x16 numeral canvas. Keep every source pixel,
         * two horizontal tiles by two vertical tiles, with no runtime
         * VRAM uploads. This v2 test intentionally uses fixed 16px spacing;
         * exact proportional pixel anchors need a separate DMA experiment. */
        const uint16_t start = DOOM_WAD_HUD_DIGIT_OFFSET + digits[i] * 4u;
        const uint16_t cx = x + i * 2u;
        _s_screen[25 * VIEWWINDOWWIDTH + cx]     = I_WadHudCell(start);
        _s_screen[25 * VIEWWINDOWWIDTH + cx + 1] = I_WadHudCell(start + 1u);
        _s_screen[26 * VIEWWINDOWWIDTH + cx]     = I_WadHudCell(start + 2u);
        _s_screen[26 * VIEWWINDOWWIDTH + cx + 1] = I_WadHudCell(start + 3u);
#else
        const uint16_t start = DOOM_WAD_HUD_DIGIT_OFFSET + digits[i] * 2u;
        _s_screen[25 * VIEWWINDOWWIDTH + x + i] = I_WadHudCell(start);
        _s_screen[26 * VIEWWINDOWWIDTH + x + i] = I_WadHudCell(start + 1u);
#endif
    }
}
#endif

static void I_DoomStyleHud(void)
{
    /* Four rows are always built in the CPU framebuffer, but DMA uploads
     * them only on the first frame or when a displayed value changes. */
    if (_g_gamestate != GS_LEVEL)
    {
        for (uint16_t y = 24; y < 28; y++)
            for (uint16_t x = 0; x < VIEWWINDOWWIDTH; x++)
                _s_screen[y * VIEWWINDOWWIDTH + x] = BLACK_CELL;
        return;
    }

#if defined(DOOM_HUD_WAD_ATLAS)
    /* Real Doom status artwork: WAD patches if available, or the user's
     * Doom sprite reference sheet embedded as fallback. Source selection
     * is reported by the asset generator during the build. */
    for (uint16_t i = 0; i < DOOM_WAD_HUD_BG_TILES; i++)
        _s_screen[24 * VIEWWINDOWWIDTH + i] = I_WadHudCell(i);

    /* Center: fixed neutral Doomguy face from the original artwork. */
    for (uint16_t y = 0; y < 4; y++)
        for (uint16_t x = 0; x < 4; x++)
        {
            const uint16_t tile = DOOM_WAD_HUD_FACE_OFFSET + 4u*y + x;
            _s_screen[(24+y) * VIEWWINDOWWIDTH + 17+x] = I_WadHudCell(tile);
        }

    /* Doom original red numeral glyphs, values from live player state. */
#if defined(DOOM_HUD_CELSO_ART)
    /* Six tile columns (48 px) per large native glyph field.
     * No overlap with centered 4x4 face tiles (columns 17..20). */
    I_WadHudNum3(1, I_HudCurrentAmmo());
    I_WadHudNum3(9, hud_saturate3(
        _g_player.mo ? _g_player.mo->health : _g_player.health));
    I_WadHudNum3(22, hud_saturate3(_g_player.armorpoints));
#else
    I_WadHudNum3(2, I_HudCurrentAmmo());
    I_WadHudNum3(10, hud_saturate3(
        _g_player.mo ? _g_player.mo->health : _g_player.health));
    I_WadHudNum3(23, hud_saturate3(_g_player.armorpoints));
#endif

    /* Three actual card states; these remain stock-font indicators in V1.
     * Keep the existing dirty-state bitmask for keys and weapon changes. */
    I_DoomStyleText(30, 24, 14, "KEYS");
    {
        const uint8_t keys = I_HudKeys();
#if defined(DOOM_HUD_CELSO_ART)
        /* Genuine 7x5 key-card art from Celso's source. Redraw only
         * on dirty key changes through the existing 28-row tile DMA. */
        _s_screen[25 * VIEWWINDOWWIDTH + 31] =
            (keys & 1u) ? I_WadHudCell(DOOM_WAD_HUD_KEY_OFFSET)
                        : font_cell(7, '-');
        _s_screen[25 * VIEWWINDOWWIDTH + 33] =
            (keys & 2u) ? I_WadHudCell(DOOM_WAD_HUD_KEY_OFFSET + 1u)
                        : font_cell(7, '-');
        _s_screen[25 * VIEWWINDOWWIDTH + 35] =
            (keys & 4u) ? I_WadHudCell(DOOM_WAD_HUD_KEY_OFFSET + 2u)
                        : font_cell(7, '-');
#else
        _s_screen[25 * VIEWWINDOWWIDTH + 31] =
            font_cell(7, (keys & 1u) ? 'B' : '-');
        _s_screen[25 * VIEWWINDOWWIDTH + 33] =
            font_cell(14, (keys & 2u) ? 'Y' : '-');
        _s_screen[25 * VIEWWINDOWWIDTH + 35] =
            font_cell(4, (keys & 4u) ? 'R' : '-');
#endif
        int16_t weapon = (int16_t)_g_player.readyweapon;
        if (weapon < 0 || weapon >= NUMWEAPONS) weapon = 0;
        _s_screen[26 * VIEWWINDOWWIDTH + 6] = font_cell(7, 'W');
        _s_screen[26 * VIEWWINDOWWIDTH + 7] =
            font_cell(7, (char)('0' + weapon));
    }
#else
    for (uint16_t y = 24; y < 28; y++)
    for (uint16_t x = 0; x < VIEWWINDOWWIDTH; x++)
    {
        uint16_t tile = y == 24 ? HUD_TOP_TILE :
                        (y == 27 ? HUD_BOTTOM_TILE : HUD_METAL_TILE);
        if (x == 0 || x == 37 || x == 8 || x == 16 ||
            x == 21 || x == 29)
            tile = HUD_SEAM_TILE;
        _s_screen[y * VIEWWINDOWWIDTH + x] =
            TILE_ATTR_FULL(3, 0, 0, 0, tile);
    }

    /* Center portrait: fixed artwork. Labels and values use stock SGDK
     * font tiles. The selected-weapon ammo number is genuinely dynamic. */
    for (uint16_t y = 0; y < 4; y++)
        for (uint16_t x = 0; x < 4; x++)
            _s_screen[(24 + y) * VIEWWINDOWWIDTH + 17 + x] =
                TILE_ATTR_FULL(3, 0, 0, 0,
                               HUD_FACE_TILE + y * 4u + x);

    I_DoomStyleText(1, 24, 14, "AMMO");
    I_DoomStyleText(9, 24, 14, "HEALTH");
    I_DoomStyleText(22, 24, 14, "ARMOR");
    I_DoomStyleText(30, 24, 14, "KEYS");

    hud_num(2, 25, I_HudCurrentAmmo(), 3);
    hud_num(10, 25, hud_saturate3(
        _g_player.mo ? _g_player.mo->health : _g_player.health), 3);
    hud_num(23, 25, hud_saturate3(_g_player.armorpoints), 3);

    I_DoomStyleText(1, 26, 7, "WEAP");
    {
        int16_t weapon = (int16_t)_g_player.readyweapon;
        if (weapon < 0 || weapon >= NUMWEAPONS) weapon = 0;
        hud_num(6, 26, (uint16_t)weapon, 1);
    }
    I_DoomStyleText(9, 26, 7, "HP%");
    I_DoomStyleText(22, 26, 7, "AR%");
    I_DoomStyleText(30, 26, 7, "CARDS");

    /* Keycards are dynamically read and tinted with existing text colors.
     * Blue uses gray because a reserved blue font color is unavailable. */
    const uint8_t keys = I_HudKeys();
    _s_screen[25 * VIEWWINDOWWIDTH + 31] =
        font_cell(7, (keys & 1u) ? 'B' : '-');
    _s_screen[25 * VIEWWINDOWWIDTH + 33] =
        font_cell(14, (keys & 2u) ? 'Y' : '-');
    _s_screen[25 * VIEWWINDOWWIDTH + 35] =
        font_cell(4, (keys & 4u) ? 'R' : '-');
#endif /* DOOM_HUD_WAD_ATLAS */
}
#endif

static void I_DrawClassicTextHUD(void)
{
    for (int16_t y = VIEWWINDOWHEIGHT; y < VDP_DISPLAY_ROWS; y++)
        for (int16_t x = 0; x < VIEWWINDOWWIDTH; x++)
            _s_screen[y * VIEWWINDOWWIDTH + x] = BLACK_CELL;

    if (_g_gamestate != GS_LEVEL) return;

    /* Only updates numbers/labels in tilemap RAM; no extra pixel rendering.
     * Labels deliberately describe bullet ammo, not weapon-dependent ammo. */
    hud_label(1, 25, "HEALTH");
    hud_num(8, 25, hud_saturate3(_g_player.mo ? _g_player.mo->health : _g_player.health), 3);
    hud_label(13, 25, "ARMOR");
    hud_num(19, 25, hud_saturate3(_g_player.armorpoints), 3);
    hud_label(24, 25, "BULLETS");
    hud_num(32, 25, hud_saturate3(_g_player.ammo[am_clip]), 3);
    hud_label(1, 27, "DOOM - MEGA DRIVE");
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
#if defined(DOOM_CACHE_STATS)
    R_CacheStatsReset();
#endif
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
#if defined(DOOM_HUD_DOOMSTYLE_TEST)
    I_BuildDoomStyleTiles();
#endif

	// 256 色 -> セル語 LUT を構築
	for (uint16_t i = 0; i < 256; i++)
		colorcell[i] = cell_for_color((uint8_t)i);

	I_ReloadPalette();
	I_UploadNewPalette(0);
	newpal = NO_PALETTE_CHANGE;

	// 画面を黒で埋める
	for (int i = 0; i < VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS; i++)
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
#if defined(DOOM_HUD_DOOMSTYLE_TEST)
    I_DoomStyleHud();
#elif defined(DOOM_CLASSIC_TEXT_HUD)
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
#if defined(DOOM_HUD_DOOMSTYLE_TEST)
        /* WAD-style mockup draws current-weapon ammo, selected weapon
         * and all three keycards, so they must invalidate the 4 HUD rows. */
        static uint8_t previousKeys;
        static int16_t previousWeapon;
        uint16_t bullets = level ? I_HudCurrentAmmo() : 0;
        uint8_t keys = level ? I_HudKeys() : 0;
        int16_t weapon = level ? (int16_t)_g_player.readyweapon : 0;
        uint8_t changed = !initialized || previousLevel != level
            || previousHealth != health || previousArmor != armor
            || previousBullets != bullets || previousKeys != keys
            || previousWeapon != weapon;
        previousKeys = keys;
        previousWeapon = weapon;
#else
        uint16_t bullets = level ? hud_saturate3(_g_player.ammo[am_clip]) : 0;
        uint8_t changed = !initialized || previousLevel != level
            || previousHealth != health || previousArmor != armor
            || previousBullets != bullets;
#endif

        previousHealth = health;
        previousArmor = armor;
        previousBullets = bullets;
        previousLevel = level;
        initialized = 1;

        VDP_setTileMapDataRect(BG_A, _s_screen, 0, 0,
                               VIEWWINDOWWIDTH,
                               changed ? VDP_DISPLAY_ROWS : VIEWWINDOWHEIGHT,
                               VIEWWINDOWWIDTH, DMA);
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
