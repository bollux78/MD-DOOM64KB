#!/usr/bin/env python3
"""After R91 sh1: O1, snapshot, runtime toggle, natural stone menu."""
from pathlib import Path
import os
mode=os.environ.get('R92_CANDIDATE','toggle');assert mode in ('toggle','full')
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:90],s.count(a));p.write_text(s.replace(a,b))
f='src/r22_video.inc'
patch(f,'#define R59_CURRENT (r59_color_tables[r59_color_mode])','#define R59_CURRENT (r59_color_tables[r59_color_mode])\n#include "r92_shadow.h"')
for bank in (0,1):
 old=f'#define R79_PAL{bank} (r79_pal[r59_color_mode-1u][{bank}])'
 new=f'#define R79_PAL{bank} (R92_ShadowOn()?r79_pal[r59_color_mode-1u][{bank}]:R59_CURRENT.pal{bank})'
 patch(f,old,new)
 patch('scripts/lab/test_r59_colorview.py',f'assert "{old}" in video',f'assert "{new}" in video')
# Define helpers after palette/framebuffer state declarations, before ISR.
patch(f,'void R20_VBlankVideo(void){','#include "r92_shadow.inc"\nvoid R20_VBlankVideo(void){')
a='''        first_row=R57_TILE_YMIN;end_row=R57_TILE_YEND;
        words_per_row=R57_DMA_WORDS;
        srca+=(first_row-1)*76+R57_TILE_XMIN;
        srcb+=(first_row-1)*76+R57_TILE_XMIN;
        dsta+=(first_row-1)*128+R57_TILE_XMIN*2;
        dstb+=(first_row-1)*128+R57_TILE_XMIN*2;'''
b='''        first_row=r92_rect.y0;end_row=r92_rect.y1;
        words_per_row=r92_rect.x1-r92_rect.x0;
        srca+=(first_row-1)*76+r92_rect.x0;
        srcb+=(first_row-1)*76+r92_rect.x0;
        dsta+=(first_row-1)*128+r92_rect.x0*2;
        dstb+=(first_row-1)*128+r92_rect.x0*2;'''
patch(f,a,b)
patch(f,'    r57_queued_crop=(_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE);','    r57_queued_crop=(_g_gamestate==GS_LEVEL && R57_CROP_ACTIVE);\n    R92_Snapshot();')
patch(f,'    if(_g_gamestate==GS_LEVEL && !R76_InGameMenu()){','    if(_g_gamestate==GS_LEVEL && !R76_InGameMenu() && R92_ShadowOn()){')
a='''        if(p==0u)R91_ConvertFast((uint16_t *)(void *)r22_fb.pixels,r91_joint[r59_color_mode-1u]);
        else R79_Convert((uint16_t *)(void *)r22_fb.pixels,
            r79_map[r59_color_mode-1u][p],r79_cost[r59_color_mode-1u][p]);'''
b='''        R92_ShadowPass((uint16_t *)(void *)r22_fb.pixels,r91_joint[r59_color_mode-1u],
            r79_map[r59_color_mode-1u][p],r79_cost[r59_color_mode-1u][p],p);'''
if mode=='toggle':patch(f,a,b)
# Off always forces normal S/H state in gameplay; menu handles its own state.
patch(f,'        VDP_setHilightShadow(TRUE);\n    }','        VDP_setHilightShadow(TRUE);\n    }else if(!R76_InGameMenu())VDP_setHilightShadow(FALSE);\n    R92_AfterPass();')
f='src/r77_menu.inc';p=Path(f);s=p.read_text();a=s.index('static const uint16_t r77_menu_pal');b=s.index('static uint16_t R77_MenuWord',a)
s=s[:a]+'''/* Stone uses HUD indices 0..14. Index15 is reserved white for text.
 * Generator regression checks that the sampled stone never uses index15. */
static uint32_t R77_StoneRow(uint16_t phase,uint16_t row,uint16_t shadow){
 (void)shadow;uint16_t id=hudw_bgmap[1][HUDW_HEALTH_C+1u+(phase&1u)];
 return hudw_tiles[id][row];
}
'''+s[b:]
s=s.replace('PAL_setColors(0,r77_menu_pal,16,CPU);','PAL_setColors(0,hudw_pal,15,CPU);PAL_setColor(15,0xEEE);')
s=s.replace('VDP_setHilightShadow(TRUE);','VDP_setHilightShadow(FALSE);')
# The R79 leave path is conditional; all menu exit states remain off until the pass.
s=s.replace('#if defined(DOOM_R79_SHADOW)\n    VDP_setHilightShadow(FALSE);\n#else\n    VDP_setHilightShadow(FALSE);\n#endif','VDP_setHilightShadow(FALSE);')
p.write_text(s)
f='src/m_text.c';patch(f,'#include "r89_ai.h"','#include "r89_ai.h"\n#include "r92_shadow.h"\nstatic void M_R92Shadow(int16_t c){(void)c;R92_SetShadow(!R92_ShadowOn());}')
patch(f,'  ai_mode,','  ai_mode,\n  shadow_mode,')
patch(f,'  {2,"AI mode:",     M_R89ChangeAI},','  {2,"AI mode:",     M_R89ChangeAI},\n  {2,"Shadow:",      M_R92Shadow},')
patch(f,'static void M_DrawOptions(void)\n{','static void M_DrawOptions(void)\n{\n V_DrawString(OptionsDef.x+13,OptionsDef.y+LINEHEIGHT*shadow_mode,12,R92_ShadowOn()?"On ":"Off");')
f='src/r22_benchmark.inc';patch(f,'#include "r89_ai.h"','#include "r89_ai.h"\n#include "r92_shadow.h"')
patch(f,'    VDP_drawText("AVERAGE FPS", 5, 8);','    VDP_drawText(R92_ShadowOn()?"SHADOW: ON":"SHADOW: OFF",5,7);\n    VDP_drawText("AVERAGE FPS", 5, 8);')
patch('scripts/lab/build_r71a12mul_hud.py',"'r91-'","'r92-'")
patch('scripts/lab/build_r71a12mul_hud.py',"('sh1', 1)",repr((mode,1)))
print('R92',mode,'SH1, Off default, A2/L3, natural stone, O1 snapshot')
patch('scripts/lab/build_r35_linear.fish','                        python3 scripts/lab/test_r77.py --generated; or exit 1','                        python3 scripts/lab/test_r92.py --generated; or exit 1')
