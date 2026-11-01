/* Scene uses all four original R39 palettes; HUD keeps its two original banks.
 * Swap while display is blank in the bottom crop gap, then restore at VBlank.
 * A minimum 8px bottom crop reserves a safe gap without clipping the HUD.
 */
static void R39M_HudPalette(void){
    PAL_setColors(32,hudw_fpal,16,CPU);PAL_setColors(48,hudw_pal,16,CPU);
}
static HINTERRUPT_CALLBACK R39M_HInt(void){
    VDP_setHInterrupt(FALSE);
    if(!r39m_scene_active || _g_gamestate!=GS_LEVEL || _g_menuactive || r35_native_active>=0)return;
    /* The scene has ended; all pixels here are in the reserved black gap. */
    VDP_setEnable(FALSE);R39M_HudPalette();VDP_setEnable(TRUE);
}
static void R39M_FramePalette(void){
    VDP_setHInterrupt(FALSE);
    if(r35_native_active>=0 || !r39m_scene_active)return;
    if(_g_gamestate!=GS_LEVEL || _g_menuactive){R39M_HudPalette();return;}
    PAL_setColors(0,genpal_cram[r39m_palette],64,CPU);
    SYS_setHIntCallback(R39M_HInt);
    VDP_setHIntCounter((uint8_t)(r57_view.yend*4u));
    VDP_setHInterrupt(TRUE);
}
