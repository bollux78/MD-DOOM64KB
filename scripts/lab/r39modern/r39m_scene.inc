/* Original R39f palette selection, full tile words and immutable tile patterns. */
#include "gen_pal.h"
#include "r39f_dither.h"
#include "r39d_dither.h"
#define SOLID_TILE_INDEX 16u
#include "colormap_cells.h"
#include "r20_colorcell.h"
#include "r39m_draw.h"
static const uint16_t (*r39d_active_colormap)[256]=doom_colormap_cells;
static uint16_t r39f_dither_mode=R39F_CHECKER;
static uint8_t r39m_palette,r39m_scene_active;
static void R39M_FramePalette(void);
static void R39M_HudPalette(void);
void R39M_EnableScene(void){r39m_scene_active=1;}
uint16_t R39F_DitherMode(void){return r39f_dither_mode;}
void __attribute__((noinline,used)) R39F_SetDitherMode(uint16_t mode){
    if(mode>R39F_VERTICAL)return;
    R20_StopVideo();r39f_dither_mode=mode;
    if(mode==R39F_SOLID){r39d_active_colormap=r39d_colormap_cells_solid;colorcell=r39d_colorcell_solid;}
    else if(mode==R39F_VERTICAL){r39d_active_colormap=r39f_colormap_cells_vertical;colorcell=r39f_colorcell_vertical;}
    else{r39d_active_colormap=doom_colormap_cells;colorcell=r39d_colorcell_checker;}
}
uint16_t R39D_DitherEnabled(void){return r39f_dither_mode!=R39F_SOLID;}
void R39D_SetDither(uint16_t on){R39F_SetDitherMode(on?R39F_CHECKER:R39F_SOLID);}
uint8_t *R39M_Framebuffer(void){return r22_fb.pixels;}
uint16_t R39M_FlatCell(uint8_t c){return colorcell[c];}
static const uint16_t *R39M_Map(const uint8_t *map){
    if(!map || !fullcolormap)return 0;
    uintptr_t off=(uintptr_t)map-(uintptr_t)fullcolormap;
    return off<8192u && !(off&255u)?r39d_active_colormap[off>>8]:0;
}
void R39M_DrawFast(const draw_column_vars_t *v,const uint16_t *map){
    R39M_Texture(r22_fb.pixels,v,map,colorcell,v->colormap);
}
