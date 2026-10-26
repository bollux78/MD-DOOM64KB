/* Recreated Doom status bar (DOOM_HUD_WAD). Included by r22_video.inc, GPL-2.0-or-later.
 * Palette line 3 + VRAM tiles HUDW_VRAM_BASE.. + BG_A rows 22..25. Updates touch the VDP only when the displayed numbers, keys,
 * weapons or face change; everything else is ROM data (hud_wad_assets.h, generated from the user's IWAD). */
#include "hud_wad_assets.h"
#include "hud_wad_logic.h"
#include "d_items.h"
#include "r_main.h"
#if !defined(DOOM_R57_NARROW256) || !defined(DOOM_R57_VIEW_MENU) || !defined(DOOM_R57_H32)
#error DOOM_HUD_WAD needs the R57 H32/H40 view-menu layout (r57_hud_dirty, r57_h32_active)
#endif
#if (HUDW_VRAM_BASE < R22_PAIR_TILE_BASE + 512) || (HUDW_VRAM_BASE + HUDW_NTILES + 12 > 1440)
#error HUD tiles overlap the pair patterns or the SGDK font
#endif
#define HUDW_ROW0 22u

static HudFace hudw_face;
static uint16_t hudw_hash;
static uint8_t hudw_shown_face = 255;

static void HUDW_Snapshot(HudState *s)
{
    const player_t *p = &_g_player;
    s->health = p->mo ? p->mo->health : p->health;
    s->armor = p->armorpoints;
    s->ammo_r = weaponinfo[p->readyweapon].ammo != am_noammo ? p->ammo[weaponinfo[p->readyweapon].ammo] : -1;
    for (uint8_t i = 0; i < 4; i++) { s->ammo[i] = p->ammo[i]; s->maxammo[i] = p->maxammo[i]; }
    uint8_t arms = 0;
    for (uint8_t i = 0; i < 6; i++) if (p->weaponowned[i + 1]) arms |= (uint8_t)(1u << i);
    if (p->weaponowned[wp_supershotgun]) arms |= 2;
    s->arms = arms;
    s->keys = (uint8_t)((p->cards[0] ? 1 : 0) | (p->cards[1] ? 2 : 0) | (p->cards[2] ? 4 : 0));
    s->face = hudw_face.index;
}

static void HUDW_UploadFace(void)
{
    uint16_t sr = R22_Lock();
    volatile uint32_t *ctrl = (volatile uint32_t *)0xC00004, *data = (volatile uint32_t *)0xC00000;
    VDP_setAutoInc(2);
    *ctrl = VDP_WRITE_VRAM_ADDR((uint32_t)(HUDW_VRAM_BASE + HUDW_FACE_SLOT) * 32u);
    const uint32_t *w = &hudw_faces[hudw_face.index < HUDW_NFACES ? hudw_face.index : 0][0][0];
    for (uint16_t i = 0; i < 12u * 8u; i++) *data = w[i];
    R22_Unlock(sr);
    hudw_shown_face = hudw_face.index;
}

static void HUDW_LoadTiles(void)
{
    uint16_t sr = R22_Lock();
    volatile uint32_t *ctrl = (volatile uint32_t *)0xC00004, *data = (volatile uint32_t *)0xC00000;
    VDP_setAutoInc(2);
    *ctrl = VDP_WRITE_VRAM_ADDR((uint32_t)HUDW_VRAM_BASE * 32u);
    for (uint16_t t = 0; t < HUDW_NTILES; t++)
        for (uint8_t r = 0; r < 8; r++) *data = hudw_tiles[t][r];
    R22_Unlock(sr);
    PAL_setColors(48, hudw_pal, 16, CPU);          /* CRAM line 3 belongs to the bar */
}

static void HUDW_WriteRows(const HudState *s)
{
    uint16_t words[HUDW_COLS];
    const uint16_t x0 = r57_h32_active ? 3u : 4u;       /* H32: planes scroll 24 px; H40: bar centred in the 40 columns */
    for (uint8_t row = 0; row < HUDW_ROWS; row++) {
        HUDW_ComposeRow(s, row, words);
        uint16_t sr = R22_Lock();
        volatile uint32_t *ctrl = (volatile uint32_t *)0xC00004;
        volatile uint16_t *data = (volatile uint16_t *)0xC00000;
        VDP_setAutoInc(2);
        *ctrl = VDP_WRITE_VRAM_ADDR(VDP_BG_A + (HUDW_ROW0 + row) * 128u + x0 * 2u);
        for (uint8_t c = 0; c < HUDW_COLS; c++) *data = words[c];
        R22_Unlock(sr);
    }
}

/* Called once per rendered frame while in a level. force: planes/tiles were wiped (mode change, native picture left, level start). */
static void HUDW_Frame(uint8_t force)
{
    HudState s;
    HUDW_Snapshot(&s);
    uint16_t h = HUDW_Hash(&s);
    uint8_t face_changed = (hudw_shown_face != hudw_face.index);
    if (!force && !face_changed && h == hudw_hash) return;
    R20_StopVideo();
    if (force) { HUDW_LoadTiles(); face_changed = 1; }
    if (face_changed) HUDW_UploadFace();
    if (force || h != hudw_hash) { HUDW_WriteRows(&s); hudw_hash = h; }
}

/* Per game tic (from ST_Ticker): the face widget. */
void HUDW_Ticker(void)
{
    const player_t *p = &_g_player;
    HudFaceIn in;
    in.health = p->mo ? p->mo->health : p->health;
    in.damagecount = p->damagecount;
    in.bonuscount = p->bonuscount;
    in.attackdown = p->attackdown != 0;
    in.god = (p->cheats & CF_GODMODE) || p->powers[pw_invulnerability];
    in.has_attacker = p->attacker && p->attacker != p->mo;
    uint16_t w = 0;
    for (uint8_t i = 0; i < NUMWEAPONS; i++) if (p->weaponowned[i]) w |= (uint16_t)(1u << i);
    in.weapons = w;
    in.mo_angle = p->mo ? p->mo->angle : 0;
    in.angle_to_attacker = in.has_attacker ? R_PointToAngle2(p->mo->x, p->mo->y, p->attacker->x, p->attacker->y) : 0;
    in.random = (uint16_t)(((uint32_t)_g_gametic * 2654435761u) >> 16);
    HUDW_FaceTick(&hudw_face, &in);
}

/* Level start: face memory reset, tiles/palette/rows reloaded on the next frame. */
void HUDW_Start(void)
{
    uint16_t w = 0;
    for (uint8_t i = 0; i < NUMWEAPONS; i++) if (_g_player.weaponowned[i]) w |= (uint16_t)(1u << i);
    HUDW_FaceInit(&hudw_face, _g_player.mo ? _g_player.mo->health : _g_player.health, w);
    r57_hud_dirty = 1;
}
