"""Patch staged Manifold M14 to add resumable pause and SRAM checkpoints.

Used only when MANIFOLD_START_MENU=1 (M14 multi-map builds).
Does NOT modify renderer or the SGDK's V-Int.
"""
from pathlib import Path
import os
import shutil

MAPIDS = {f"E1M{i}": i - 1 for i in range(1,10)}

def _one(text, old, new, label):
    if text.count(old) != 1:
        raise AssertionError(f"M14 native-save anchor changed: {label} ({text.count(old)})")
    return text.replace(old, new, 1)

def install(out, spawn_x, spawn_y, spawn_ang, spawn_cell):
    out = Path(out)
    root = Path(__file__).resolve().parents[1]
    src = out / "src"
    shutil.copyfile(root / "tools/m14/multimap/m14_sram.h", src / "m14_sram.h")
    mapid = MAPIDS[os.environ.get("MANIFOLD_MAP", "E1M1")]

    # Staged level.c knows the current map identity, used to validate saves.
    level = src / "level.c"
    text = level.read_text()
    anchor = f"    const int init_player_sector = {spawn_cell};"
    text = _one(text, anchor,
        f"    {{ extern u16 m14_map_id_var; m14_map_id_var = {mapid}; }}\n" + anchor,
        "set map id")
    level.write_text(text)

    # Inventory includes the live slot list (the public accessor loses duplicates).
    inv = src / "inventory.c"
    text = inv.read_text() + """
/* M14 native-save: serialize the eight slots in their original order. */
void m14_inventory_export(u16 *slots, u16 *n) {
    u16 i;
    *n = (u16)num_items;
    for (i = 0; i < 8; ++i) slots[i] = (i < num_items) ? inventory[i] : 0;
}
void m14_inventory_import(const u16 *slots, u16 n) {
    u16 i;
    inventory_reset();
    if (n > 8) n = 8;
    for (i = 0; i < n; ++i)
        if (slots[i] < NUM_ITEM_TYPES) inventory_add_item((item_type)slots[i]);
}
"""
    inv.write_text(text)

    # The status bar is in the common linked bank and therefore safe to
    # execute while slot 5 is temporarily mapped to SRAM.
    sb = src / "doom_statusbar.c"
    text = sb.read_text() + r"""
/* M14 native checkpoint: NOT an emulator save state.
   Player position, HUD stats and inventory are persistent.
   Living enemies, triggers, lifts, door timers and projectiles are not
   serialized; a load after reboot starts a fresh world at that position. */
#include "game.h"
#include "level.h"
#include "m14_sram.h"

extern void m14_inventory_export(u16 *slots, u16 *n);
extern void m14_inventory_import(const u16 *slots, u16 n);
u16 m14_map_id_var;
/* pause / save feedback: row 26 (under the HUD, same place and font as the FPS counter); the console overlay is not visible in this layout */
void m14_ptext(const char *t) {
    u16 x = 10;
    VDP_clearTileMapRect(BG_B, 10, 26, 22, 1);
    while (*t && x < 32) { VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL3, 1, 0, 0, TILE_FONT_INDEX + (*t) - 32), x++, 26); t++; }
}

static void m14_put_long(m14_checkpoint *r, int at, m14_dw v) {
    r->w[at] = (u16)(v >> 16);
    r->w[at + 1] = (u16)v;
}
static m14_dw m14_get_long(const m14_checkpoint *r, int at) {
    return ((m14_dw)r->w[at] << 16) | r->w[at + 1];
}
static void m14_capture(m14_checkpoint *r) {
    memset(r, 0, sizeof(*r));
    r->w[3] = m14_map_id_var;
    m14_put_long(r, 4, (m14_dw)cur_player_pos.x);
    m14_put_long(r, 6, (m14_dw)cur_player_pos.y);
    m14_put_long(r, 8, (m14_dw)cur_player_pos.z);
    r->w[10] = cur_player_pos.ang;
    r->w[11] = cur_player_pos.cur_sector;
    r->w[12] = dhud_state.health;
    r->w[13] = dhud_state.armor;
    r->w[14] = dhud_state.ammo_r;
    r->w[15] = dhud_state.ammo[0];
    r->w[16] = dhud_state.ammo[1];
    r->w[17] = dhud_state.ammo[2];
    r->w[18] = dhud_state.ammo[3];
    r->w[19] = dhud_state.arms;
    r->w[20] = dhud_state.keys;
    m14_inventory_export(&r->w[21], &r->w[29]);
}
int m14_checkpoint_save(void) {
    m14_checkpoint r;
    m14_capture(&r);
    return m14_sram_save(&r);
}
static int m14_apply_checkpoint(const m14_checkpoint *r) {
    if (r->w[3] != m14_map_id_var ||
        r->w[11] >= cur_portal_map->num_sectors ||
        r->w[12] == 0) return 0;
    cur_player_pos.x = (s32)m14_get_long(r, 4);
    cur_player_pos.y = (s32)m14_get_long(r, 6);
    cur_player_pos.z = (s32)m14_get_long(r, 8);
    cur_player_pos.ang = r->w[10];
    cur_player_pos.cur_sector = r->w[11];
    dhud_state.health = r->w[12];
    dhud_state.armor = r->w[13];
    dhud_state.ammo_r = r->w[14];
    dhud_state.ammo[0] = r->w[15];
    dhud_state.ammo[1] = r->w[16];
    dhud_state.ammo[2] = r->w[17];
    dhud_state.ammo[3] = r->w[18];
    dhud_state.arms = r->w[19];
    dhud_state.keys = r->w[20];
    m14_inventory_import(&r->w[21], r->w[29]);
    dhud_have_hash = 0;
    angleCos32 = cosFix32(cur_player_pos.ang);
    angleSin32 = sinFix32(cur_player_pos.ang);
    return 1;
}
int m14_checkpoint_load_current(void) {
    m14_checkpoint r;
    return m14_sram_load(&r) && m14_apply_checkpoint(&r);
}
void m14_checkpoint_boot(void) {
    if (m14_sram_take_request(m14_map_id_var))
        (void)m14_checkpoint_load_current();
}
/* Transition to the original fixed ROM map selector only on C, not START. */
void m14_save_and_menu(void) {
    __asm volatile("move.w #0x2700,%%sr" ::: "memory");
    *(volatile u32 *)0xFF0010 = 0x4D454E55UL;
    *(volatile u32 *)0xFF0014 = 0x4C560000UL | m14_map_id_var;
    __asm volatile("move.l 0x0,%%sp\n move.l 0x4,%%a0\n jmp (%%a0)" ::: "memory");
    for (;;) { }
}
"""
    sb.write_text(text)

    game = src / "game.c"
    text = game.read_text()
    text = "void m14_ptext(const char *t);\n" + text
    # Keep the upstream START-to-pause toggle, replacing M14's unconditional
    # warm reset with a 3-button pause action handler.
    anchor = """    if(paused) {
        return 0;
    }"""
    replacement = """    if(paused) {
        static u16 m14_prev_pause_buttons = 0;
        u16 keys = JOY_readJoypad(JOY_1);
        extern int m14_checkpoint_save(void);
        extern int m14_checkpoint_load_current(void);
        extern void m14_save_and_menu(void);
        extern void m14_ptext(const char *t);
        if ((keys & BUTTON_A) && !(m14_prev_pause_buttons & BUTTON_A)) {
            if (m14_checkpoint_save())
                m14_ptext("CHECKPOINT SALVO");
            else
                m14_ptext("ERRO AO SALVAR");
        }
        if ((keys & BUTTON_B) && !(m14_prev_pause_buttons & BUTTON_B)) {
            if (m14_checkpoint_load_current())
                m14_ptext("CHECKPOINT CARREGADO");
            else
                m14_ptext("SEM SAVE VALIDO");
        }
        if ((keys & BUTTON_C) && !(m14_prev_pause_buttons & BUTTON_C))
            m14_save_and_menu();
        m14_prev_pause_buttons = keys;
        return 0;
    }"""
    text = _one(text, anchor, replacement, "pause buttons")
    # Show controls through Manifold's existing proportional-font console
    # overlay, which is already known to work in the game HUD.
    anchor = """    } else if (input_res == UNPAUSE_SCREEN) {"""
    text = _one(text, anchor,
        """        m14_ptext("A SALVA B LE C MENU");
""" + anchor, "pause message")
    anchor = """    if(paused) {
        return SAME_MODE;
    }"""
    text = _one(text, anchor,
        """    if(paused) {
        console_tick();  /* pause overlay and save/load confirmations */
        return SAME_MODE;
    }""", "pause overlay tick")
    # Upstream's PAUSE_SCREEN paints a 40x30 checkerboard over BG_B, then
    # UNPAUSE_SCREEN clears the entire plane. That destroys the native Doom
    # HUD, sky and font resources. Preserve VDP tilemaps; draw only a small
    # existing console overlay on top of the live frame instead.
    a = text.index("    } else if (input_res == PAUSE_SCREEN) {")
    b = text.index("    if(paused) {\n        console_tick();", a)
    text = text[:a] + """    } else if (input_res == PAUSE_SCREEN) {
        m14_ptext("A SALVA B LE C MENU");
    } else if (input_res == UNPAUSE_SCREEN) {
        m14_ptext("");
    }

""" + text[b:]
    anchor = """    free_tile_loc = inventory_init(free_tile_loc);"""
    text = _one(text, anchor,
        anchor + """
    { extern void m14_checkpoint_boot(void); m14_checkpoint_boot(); }""",
        "apply loaded checkpoint after player & HUD initialization")
    # The upstream run_game emitted "game initialized!" every frame,
    # overwriting the pause help and save/load feedback immediately.
    old_init = '    console_push_message_high_priority("game initialized!", 17, 2);'
    if text.count(old_init) == 1:      # not present in every base
        text = text.replace(old_init, '    /* Native checkpoint menu owns console messages while paused. */', 1)
    game.write_text(text)
    print("M14 native save: SGDK pause/resume + A save / B load / C level menu; X7 SRAM checkpoint")
