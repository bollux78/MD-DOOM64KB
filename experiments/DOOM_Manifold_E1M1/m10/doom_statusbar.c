/* M10: classic Doom status bar for Manifold, built on Claudio's R128 HUD-WAD
 * (scripts/lab/gen_hud_wad.py + src/hud_wad_logic.h). Copied into the staged
 * Manifold tree by stage_rom.py (MANIFOLD_HUD=doom); assets are generated on
 * the runner from the shareware IWAD and never committed.
 *
 * VRAM: HUDW_NTILES static tiles + 16-tile face slot, allocated from Manifold's
 * normal tile area in place of the old inventory HUD (asserted at init).
 * CRAM: everything on PAL2 (the old HUD line); PAL0 weapon, PAL1 3D view,
 * PAL3 object sprites/text are untouched.
 * BG_B: bar on rows 22..25, columns 4..35; stone margins on columns 0..3 and
 * 36..39; rows 26..27 cleared. Rows 28+ (sky tiles) are never written.
 * Cost: tilemap rewritten only when HUDW_Hash changes; the face (16 tiles,
 * 512 B) is DMA-uploaded only when the frame changes. */
#include "manifold_mute_klog.h"
#include <genesis.h>
#include "inventory.h"

static u16 manifold_hud_base;
#define HUDW_VRAM_BASE manifold_hud_base
#include "hud_wad_assets.h"
#include "hud_wad_logic.h"

#ifdef MANIFOLD_H32
#define DHUD_X 0            /* H32: the 256 px bar is the full screen width */
#else
#define DHUD_X 4
#endif
#define DHUD_Y 22
#define DHUD_PAL2(w) ((u16)(((w) & ~0x6000) | 0x4000))   /* logic emits PAL3/PAL2 words -> force line 2 */

static HudState dhud_state;
static HudFace dhud_face;
static u16 dhud_last_hash;
static u8 dhud_have_hash;
static u16 dhud_row[32];
u16 doom_hud_vram_first, doom_hud_vram_count;   /* exported for the VRAM report/asserts */

static void dhud_draw_bar(void) {
    for (u8 r = 0; r < HUDW_ROWS; r++) {
        HUDW_ComposeRow(&dhud_state, r, dhud_row);
        for (u8 c = 0; c < HUDW_COLS; c++) dhud_row[c] = DHUD_PAL2(dhud_row[c]);
        VDP_setTileMapDataRect(BG_B, dhud_row, DHUD_X, DHUD_Y + r, HUDW_COLS, 1, HUDW_COLS, CPU);
    }
}

static void dhud_draw_margins(void) {
#ifndef MANIFOLD_H32
    for (u8 r = 0; r < HUDW_ROWS; r++) {
        u16 left = DHUD_PAL2(HUDW_WORD(hudw_bgmap[r][0]));
        u16 right = DHUD_PAL2(HUDW_WORD(hudw_bgmap[r][HUDW_COLS - 1]));
        for (u8 c = 0; c < 4; c++) {
            VDP_setTileMapXY(BG_B, left, c, DHUD_Y + r);
            VDP_setTileMapXY(BG_B, right, 36 + c, DHUD_Y + r);
        }
    }
#endif
    VDP_clearTileMapRect(BG_B, 0, DHUD_Y + HUDW_ROWS, 40, 2);   /* rows 26-27 */
}

u32 doom_hud_init(u32 free_tile_loc) {
    manifold_hud_base = (u16)free_tile_loc;
    doom_hud_vram_first = manifold_hud_base;
    doom_hud_vram_count = HUDW_NTILES + HUDW_FACE_W * 4;
    VDP_loadTileData((const u32 *)hudw_tiles, manifold_hud_base, HUDW_NTILES, CPU);
    PAL_setPalette(PAL2, hudw_pal, CPU);
    /* Manifold has no Doom player stats yet: TEMPORARY fixed values (Doom
     * start: 100% health, 0% armor, pistol 50 bullets, no other arms). Keys
     * come from Manifold's real inventory. */
    dhud_state.health = 100;
    dhud_state.armor = 0;
    dhud_state.ammo_r = 50;
    dhud_state.ammo[0] = 50;  dhud_state.maxammo[0] = 200;
    dhud_state.ammo[1] = 0;   dhud_state.maxammo[1] = 50;
    dhud_state.ammo[2] = 0;   dhud_state.maxammo[2] = 300;
    dhud_state.ammo[3] = 0;   dhud_state.maxammo[3] = 50;
    dhud_state.arms = 0;
    dhud_state.keys = 0;
    HUDW_FaceInit(&dhud_face, dhud_state.health, 0);
    dhud_have_hash = 0;
    dhud_draw_margins();
    return free_tile_loc + doom_hud_vram_count;
}

void doom_hud_update(void) {
    u8 keys = 0;
    if (inventory_has_item(BLUE_KEY)) keys |= 1;
    if (inventory_has_item(GREEN_KEY)) keys |= 2;    /* Manifold green key shown as Doom's yellow card */
    if (inventory_has_item(RED_KEY)) keys |= 4;
    dhud_state.keys = keys;

    HudFaceIn in;
    memset(&in, 0, sizeof(in));
    in.health = dhud_state.health;
    in.attackdown = (JOY_readJoypad(JOY_1) & BUTTON_A) ? 1 : 0;
    in.random = random();
    HUDW_FaceTick(&dhud_face, &in);
    if (dhud_face.shown != dhud_face.index) {
        dhud_face.shown = dhud_face.index;
        VDP_loadTileData((const u32 *)hudw_faces[dhud_face.index], manifold_hud_base + HUDW_FACE_SLOT, 16, DMA);
    }

    u16 h = HUDW_Hash(&dhud_state);
    if (!dhud_have_hash || h != dhud_last_hash) {
        dhud_last_hash = h;
        dhud_have_hash = 1;
        dhud_draw_bar();
    }
}
