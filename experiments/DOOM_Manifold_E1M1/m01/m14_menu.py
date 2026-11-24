"""MANIFOLD_MENU=1: black-screen pause menu with test options (needs MANIFOLD_NATIVE_SAVE=1, excludes MANIFOLD_BENCH).

START pauses and opens a menu on a cleared screen (planes cleared, HInt that blanks the 3D borders switched off):
  CONTINUAR / SALVAR CHECKPOINT / CARREGAR CHECKPOINT / SAIR PARA FASES
  LIMITE DE FPS      LIVRE, 12, 10, 7.5   (frame is held until the minimum time passed; weapon timing is time based)
  RECORTE COLUNAS    0, -2, -4 tiles per side  (portal window narrowed, perspective unchanged, borders stay black)
  RECORTE LINHAS     0, -1, -2 tiles top and bottom (initial vertical clip of every column)
  DESCARTE           on/off for the early back-face / window reject in visit_graph
CONTINUAR (or START again) saves an automatic checkpoint and reloads the level from it, which rebuilds the screen;
monsters and doors restart.  The options live in manifold_dbg bytes 0..5 (no extra BSS: RAM is full) and survive the
reload.  Byte map: 0 cursor, 1 fps limit, 2 column crop, 3 row crop, 4 early-cull off, 5 previous buttons."""
import os


def _one(text, anchor, new, what):
    assert text.count(anchor) == 1, (what, text.count(anchor))
    return text.replace(anchor, new, 1)


CODE = r'''
/* ---- MANIFOLD_MENU: black-screen pause menu ---- */
extern volatile u32 manifold_dbg[8];                       /* bytes 0..5 reused: no extra BSS */
#define M14M ((volatile u8 *)manifold_dbg)
extern int m14_checkpoint_request(void);
extern int m14_checkpoint_loadreq(void);
extern int m14_checkpoint_save(void);
extern void m14_save_and_menu(void);

static void m14m_put(const char *t, u16 x, u16 y) {
    VDP_setTextPalette(PAL3); VDP_setTextPriority(1); VDP_drawTextBG(BG_B, t, x, y);     /* one call per line: the game is paused, no DMA to dodge */
}
static void m14m_row(u8 r) {
    static const char *const nm[8] = { "CONTINUAR", "SALVAR CHECKPOINT", "CARREGAR CHECKPOINT", "SAIR PARA FASES",
                                       "LIMITE DE FPS", "RECORTE COLUNAS", "RECORTE LINHAS", "DESCARTE" };
    static const char *const fv[4] = { "LIVRE", "12", "10", "7.5" };
    static const char *const cv[3] = { "0", "-2 TILES", "-4 TILES" };
    static const char *const rv[3] = { "0", "-1 TILE", "-2 TILES" };
    static const char *const dv[2] = { "LIGADO", "DESLIGADO" };
    char ln[41]; char *p = ln; const char *s = nm[r]; const char *v = 0;
    *p++ = (M14M[0] == r) ? '>' : ' '; *p++ = ' ';
    while (*s) *p++ = *s++;
    if (r >= 4) {
        if (r == 4) v = fv[M14M[1] & 3]; else if (r == 5) v = cv[M14M[2] % 3]; else if (r == 6) v = rv[M14M[3] % 3]; else v = dv[M14M[4] & 1];
        while (p < ln + 20) *p++ = ' ';
        *p++ = '<'; *p++ = ' '; while (*v) *p++ = *v++; *p++ = ' '; *p++ = '>';
    }
    while (p < ln + 40) *p++ = ' ';
    *p = 0;
    m14m_put(ln, 0, r < 4 ? 6 + r : 7 + r);
}
static void m14m_msg(const char *t) {
    char ln[41]; char *p = ln; while (*t && p < ln + 40) *p++ = *t++; while (p < ln + 40) *p++ = ' '; *p = 0;
    m14m_put(ln, 0, 20);
}
void m14_menu_draw(void) {
    u8 r;
    SYS_setHIntCallback(NULL); VDP_setHInterrupt(0); VDP_setEnable(1);      /* the 3D view blanks its borders from an HInt */
    VDP_clearPlane(BG_A, TRUE); VDP_clearPlane(BG_B, TRUE);
    VDP_setVerticalScroll(BG_A, 0); VDP_setVerticalScroll(BG_B, 0); VDP_setHorizontalScroll(BG_A, 0); VDP_setHorizontalScroll(BG_B, 0);
    VDP_resetSprites(); VDP_updateSprites(1, CPU);
    SYS_doVBlankProcess(); SYS_doVBlankProcess();
    PAL_setColor(48, 0x000); PAL_setColor(49, 0xEEE);
    M14M[0] = 0; M14M[5] = 0x3F;
    m14m_put("PAUSA", 1, 3);
    for (r = 0; r < 8; r++) m14m_row(r);
    m14m_put("CIMA/BAIXO ESCOLHE  ESQ/DIR MUDA", 1, 17);
    m14m_put("A CONFIRMA   START = CONTINUAR", 1, 18);
}
/* paused-branch input: 0 = nothing, 7 = leave the menu (reload from the checkpoint) */
int m14_menu_input(u16 k) {
    u8 now = (k & BUTTON_UP ? 1 : 0) | (k & BUTTON_DOWN ? 2 : 0) | (k & BUTTON_LEFT ? 4 : 0) | (k & BUTTON_RIGHT ? 8 : 0) | (k & BUTTON_A ? 16 : 0);
    u8 e = now & ~M14M[5]; u8 r;
    M14M[5] = now;
    if (!e) return 0;
    if ((e & 1) && M14M[0] > 0) M14M[0]--;
    if ((e & 2) && M14M[0] < 7) M14M[0]++;
    if (e & 12) {
        s8 d = (e & 8) ? 1 : -1; u8 sel = M14M[0];
        if (sel == 4) { s8 v = (s8)M14M[1] + d; if (v >= 0 && v <= 3) M14M[1] = (u8)v; }
        else if (sel == 5) { s8 v = (s8)M14M[2] + d; if (v >= 0 && v <= 2) M14M[2] = (u8)v; }
        else if (sel == 6) { s8 v = (s8)M14M[3] + d; if (v >= 0 && v <= 2) M14M[3] = (u8)v; }
        else if (sel == 7) M14M[4] ^= 1;
    }
    if (e & 16) {
        u8 sel = M14M[0];
        if (sel == 0) return 7;
        if (sel == 1) m14m_msg(m14_checkpoint_save() ? "CHECKPOINT SALVO" : "ERRO AO SALVAR");
        if (sel == 2) { if (m14_checkpoint_loadreq()) return 7; m14m_msg("SEM SAVE VALIDO"); }
        if (sel == 3) m14_save_and_menu();
    }
    for (r = 0; r < 8; r++) m14m_row(r);
    return 0;
}
game_mode m14_menu_resume(void) {
    VDP_setHilightShadow(0);
    VDP_clearPlane(BG_A, TRUE); VDP_clearPlane(BG_B, TRUE);      /* no menu text left behind when the level is rebuilt */
    m14_checkpoint_request();
    return RESET_MODE;
}
/* hold the frame until the minimum time has passed (FPS limit) */
void m14_menu_wait(u32 st) {
    u8 f = M14M[1]; u32 lim;
    if (!f) return;
    lim = (f == 1) ? 25 : (f == 2) ? 30 : 40;
    while (getTick() - st < lim) { }
}
'''


def m14_menu(out):
    if os.environ.get("MANIFOLD_MENU", "0") != "1":
        return
    assert os.environ.get("MANIFOLD_NATIVE_SAVE", "0") == "1", "menu needs NATIVE_SAVE (checkpoints)"
    assert os.environ.get("MANIFOLD_BENCH", "0") != "1", "menu and bench share manifold_dbg"
    src = out / "src"
    # checkpoint helpers next to the boot loader (same file as m14_sram.h users)
    sb = src / "doom_statusbar.c"; t = sb.read_text()
    a = "void m14_checkpoint_boot(void) {"
    t = _one(t, a, "int m14_checkpoint_request(void) { return m14_checkpoint_save() && m14_sram_request(m14_map_id_var); }\n"
                   "int m14_checkpoint_loadreq(void) { return m14_sram_request(m14_map_id_var); }\n" + a, "request helpers")
    sb.write_text(t)
    g = src / "game.c"; t = g.read_text()
    t += CODE
    # paused input goes to the menu
    a = "        u16 keys = JOY_readJoypad(JOY_1);\n        extern int m14_checkpoint_save(void);"
    t = _one(t, a, "        u16 keys = JOY_readJoypad(JOY_1);\n        { extern int m14_menu_input(u16); int mr_ = m14_menu_input(keys); if (mr_) { paused = 0; return 7; } return 0; }\n        extern int m14_checkpoint_save(void);", "menu input")
    a = '        m14_ptext("A SALVA B LE C MENU");\n    } else if (input_res == UNPAUSE_SCREEN) {\n        m14_ptext("");\n    }'
    t = _one(t, a, '        { extern void m14_menu_draw(void); m14_menu_draw(); }\n    } else if (input_res == UNPAUSE_SCREEN || input_res == 7) {\n        { extern game_mode m14_menu_resume(void); return m14_menu_resume(); }\n    }', "menu draw/resume")
    a = "        console_tick();  /* pause overlay and save/load confirmations */"
    t = _one(t, a, "        /* menu: no console overlay */", "console tick")
    a = "    u32 end_ticks = getTick();\n    last_frame_ticks = end_ticks - start_ticks;"
    t = _one(t, a, "    { extern void m14_menu_wait(u32); m14_menu_wait(start_ticks); }\n" + a, "fps limit")
    g.write_text(t)
    # column crop: narrow the portal window
    p = src / "portal.c"; t = p.read_text()
    a = "            visit_graph(src_sector, src_sector, 0, RENDER_WIDTH, cur_frame, 0);"
    t = _one(t, a, "            { u16 cc_ = (u16)(((volatile u8 *)manifold_dbg)[2] % 3) * 4;   /* tiles per side x 2 columns */\n"
                   "              visit_graph(src_sector, src_sector, cc_, RENDER_WIDTH - cc_, cur_frame, 0); }", "column crop")
    # early cull switch (only present with EARLY_CULL / WALL_LOOP)
    a = "        if (sector != src_sector || !is_portal) {\n            s32 ecx1 = trans_v1.x"
    if t.count(a) == 1:
        t = t.replace(a, "        if (!(((volatile u8 *)manifold_dbg)[4] & 1) && (sector != src_sector || !is_portal)) {\n            s32 ecx1 = trans_v1.x", 1)
    p.write_text(t)
    # row crop: initial vertical clip of every column
    d = src / "draw.c"; t = d.read_text()
    a = "    u32 u32val = (SCREEN_HEIGHT << 16) | SCREEN_HEIGHT;"
    t = _one(t, a, "    extern volatile u32 manifold_dbg[8];\n    u32 m14r_ = (u32)(((volatile u8 *)manifold_dbg)[3] % 3) * 8;\n"
                   "    u32 u32val = (m14r_ << 24) | ((SCREEN_HEIGHT - m14r_) << 16) | (m14r_ << 8) | (SCREEN_HEIGHT - m14r_);", "row crop")
    d.write_text(t)
    print("menu: installed")
