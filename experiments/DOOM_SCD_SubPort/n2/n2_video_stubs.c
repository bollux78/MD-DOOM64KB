/* N2 + R128 drawers: the MD video module (i_genesisv.c) is linked only for its Pair-V column
 * drawers. Everything else it exports touches the VDP / ROM art and is replaced here (this
 * object links first, so these definitions win). No headers on purpose. */
int D_Wipe(void) { return 0; }
int I_FinishUpdate(void) { return 0; }
int I_InitScreenPage(void) { return 0; }
int I_InitScreenPages(void) { return 0; }
int I_ReloadPalette(void) { return 0; }
int I_SetPalette(void) { return 0; }
int R22_BeginFrame(void) { return 0; }
int R57_ChangeView(void) { return 0; }
int R59_ChangeColor(void) { return 0; }
int R59_ColorMode(void) { return 0; }
int R76_MenuOverlayFinish(void) { return 0; }
int R92_SetShadow(void) { return 0; }
int R92_ShadowOn(void) { return 0; }
int V_ClearString(void) { return 0; }
int V_ClearViewWindow(void) { return 0; }
int V_DrawBackground(void) { return 0; }
int V_DrawCharacter(void) { return 0; }
int V_DrawCharacterForeground(void) { return 0; }
int V_DrawLine(void) { return 0; }
int V_DrawRawFullScreen(void) { return 0; }
int V_DrawSTCharacter(void) { return 0; }
int V_DrawSTString(void) { return 0; }
int V_DrawString(void) { return 0; }
int V_InitDrawLine(void) { return 0; }
int V_SetSTPalette(void) { return 0; }
int V_ShutdownDrawLine(void) { return 0; }
int wipe_StartScreen(void) { return 0; }

/* R22_Alloc used SGDK MEM_alloc (MD work RAM heap): give it a PRG-RAM bump pool. */
extern void I_Error(const char *, ...);
static unsigned char n2_r22_pool[8192] __attribute__((aligned(4)));
static unsigned short n2_r22_used;
void *R22_Alloc(unsigned short n)
{
    n = (unsigned short)((n + 3u) & ~3u);
    if ((unsigned long)n2_r22_used + n > sizeof n2_r22_pool) I_Error("N2 R22 POOL %u", (unsigned)n);
    void *p = n2_r22_pool + n2_r22_used; n2_r22_used = (unsigned short)(n2_r22_used + n); return p;
}
