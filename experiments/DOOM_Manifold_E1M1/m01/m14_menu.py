"""MANIFOLD_MENU=1: pause menu with test options, one line in the HUD band (needs MANIFOLD_NATIVE_SAVE=1, excludes MANIFOLD_BENCH).

START pauses (the frozen frame stays on screen); UP/DOWN choose an item, LEFT/RIGHT change its value, A confirms,
START resumes.  The line is drawn with m14_ptext (same band and routine the old pause text used), so nothing is
cleared, no HInt is touched and the level is NOT reloaded (an earlier black-screen version that cleared the planes
and reloaded through SRAM was unstable on BlastEm / real hardware):
  CONTINUAR, SALVAR CHECKP., CARREGAR CHECKP. (in place, as the old A / C), SAIR P/ FASES (old B)
  FPS MAX        LIVRE, 12, 10, 7.5   (frame held until the minimum time passed)
  COLUNAS        0, -2, -4 tiles per side  (portal window narrowed, perspective unchanged)
  LINHAS         0, -1, -2 tiles top and bottom (initial vertical clip of every column)
  DESCARTE       early back-face / window reject in visit_graph, on/off
Options take effect when the game resumes and persist (manifold_dbg bytes 0..5, no extra BSS).
Byte map: 0 cursor, 1 fps limit, 2 column crop, 3 row crop, 4 early-cull off, 5 previous buttons (bits 0-4)."""
import os


def _one(text, anchor, new, what):
    assert text.count(anchor) == 1, (what, text.count(anchor))
    return text.replace(anchor, new, 1)


CODE = r'''
/* ---- MANIFOLD_MENU: one-line pause menu ---- */
extern volatile u32 manifold_dbg[8];                       /* bytes 0..5 reused: no extra BSS */
#define M14M ((volatile u8 *)manifold_dbg)
extern int m14_checkpoint_save(void);
extern int m14_checkpoint_load_current(void);
extern void m14_save_and_menu(void);

static void m14m_show(void) {
    static const char *const nm[8] = { "CONTINUAR (A)", "SALVAR CHECKP. (A)", "CARREGAR CHECKP. (A)", "SAIR P/ FASES (A)",
                                       "FPS MAX", "COLUNAS", "LINHAS", "DESCARTE" };
    static const char *const fv[4] = { "LIVRE", "12", "10", "7.5" };
    static const char *const cv[3] = { "0", "-2 TILES", "-4 TILES" };
    static const char *const rv[3] = { "0", "-1 TILE", "-2 TILES" };
    static const char *const dv[2] = { "LIGADO", "DESLIG." };
    char ln[24]; char *p = ln; const char *s = nm[M14M[0] & 7]; const char *v = 0; u8 r = M14M[0] & 7;
    while (*s) *p++ = *s++;
    if (r >= 4) {
        if (r == 4) v = fv[M14M[1] & 3]; else if (r == 5) v = cv[M14M[2] % 3]; else if (r == 6) v = rv[M14M[3] % 3]; else v = dv[M14M[4] & 1];
        *p++ = ' '; *p++ = '<'; *p++ = ' '; while (*v) *p++ = *v++; *p++ = ' '; *p++ = '>';
    }
    *p = 0;
    m14_ptext(ln);
}
void m14_menu_draw(void) { M14M[0] = 0; M14M[5] = 0x3F; m14m_show(); }
/* paused-branch input: 0 = nothing, 1 = resume */
int m14_menu_input(u16 k) {
    u8 now = (k & BUTTON_UP ? 1 : 0) | (k & BUTTON_DOWN ? 2 : 0) | (k & BUTTON_LEFT ? 4 : 0) | (k & BUTTON_RIGHT ? 8 : 0) | (k & BUTTON_A ? 16 : 0);
    u8 e = now & ~M14M[5];
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
        if (sel == 0) return 1;
        if (sel == 1) { m14_ptext(m14_checkpoint_save() ? "CHECKPOINT SALVO" : "ERRO AO SALVAR"); return 0; }
        if (sel == 2) { m14_ptext(m14_checkpoint_load_current() ? "CHECKPOINT CARREGADO" : "SEM SAVE VALIDO"); return 0; }
        if (sel == 3) m14_save_and_menu();
    }
    m14m_show();
    return 0;
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
    g = src / "game.c"; t = g.read_text()
    t += CODE
    # paused input goes to the menu
    a = "        u16 keys = JOY_readJoypad(JOY_1);\n        extern int m14_checkpoint_save(void);"
    t = _one(t, a, "        u16 keys = JOY_readJoypad(JOY_1);\n        { extern int m14_menu_input(u16); int mr_ = m14_menu_input(keys); if (mr_) { paused = 0; return UNPAUSE_SCREEN; } return 0; }\n        extern int m14_checkpoint_save(void);", "menu input")
    a = '        m14_ptext("A SALVA B LE C MENU");'
    t = _one(t, a, '        { extern void m14_menu_draw(void); m14_menu_draw(); }', "menu draw")
    a = '    } else if (input_res == UNPAUSE_SCREEN) {\n        m14_ptext("");'
    t = _one(t, a, a + " { extern void m14_bmp_clear_both(void); m14_bmp_clear_both(); }   /* both RAM frame buffers black once: clean borders for a new crop */", "unpause hook")
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
    # both frame buffers cleared on resume
    mb = src / "my_bmp.c"; t = mb.read_text()
    t += "\nvoid m14_bmp_clear_both(void) { bmp_clear_vertical_bitmap_buffer(bmp_buffer_0); bmp_clear_vertical_bitmap_buffer(bmp_buffer_1); }\n"
    mb.write_text(t)
    # row crop: initial vertical clip of every column
    d = src / "draw.c"; t = d.read_text()
    a = "    u32 u32val = (SCREEN_HEIGHT << 16) | SCREEN_HEIGHT;"
    t = _one(t, a, "    extern volatile u32 manifold_dbg[8];\n    u32 m14r_ = (u32)(((volatile u8 *)manifold_dbg)[3] % 3) * 8;\n"
                   "    u32 u32val = (m14r_ << 24) | ((SCREEN_HEIGHT - m14r_) << 16) | (m14r_ << 8) | (SCREEN_HEIGHT - m14r_);", "row crop")
    d.write_text(t)
    print("menu: installed")
