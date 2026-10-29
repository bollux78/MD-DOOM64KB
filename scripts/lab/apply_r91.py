#!/usr/bin/env python3
"""After R90-control: A2/L3-only selector and fast joint S/H experiment."""
from pathlib import Path
import os
mode=os.environ['R91_CANDIDATE'];assert mode in ('control','sh1','sh2')
def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:100],s.count(a));p.write_text(s.replace(a,b))
f='src/r22_video.inc'
patch(f,'static struct {uint8_t mode,dirty,palette;} r77_color_state;','static struct {uint8_t mode,dirty,palette;} r77_color_state={1,0,0};')
patch(f,'uint8_t R59_ColorMode(void){return r59_color_mode;}','uint8_t R59_ColorMode(void){return (uint8_t)(r59_color_mode-1u);}')
patch(f,'''    if(right)r59_color_mode=(uint8_t)((r59_color_mode+1u)%R59_COLOR_MODES);
    else r59_color_mode=(uint8_t)((r59_color_mode+R59_COLOR_MODES-1u)%R59_COLOR_MODES);''','''    (void)right;
    r59_color_mode=(r59_color_mode==1u)?2u:1u;''')
patch('src/m_text.c','static const char *const r59_names[4]={"Hybrid Blue+","A2 Full","L3 Detail","HN Smooth"};','static const char *const r59_names[2]={"A2 Full  ","L3 Detail"};')
# R59 regression test expects the six-mode circular selector. R91 deliberately
# replaces it with an A2/L3 toggle; assert the actual R91 contract instead.
patch('scripts/lab/test_r59_colorview.py',
      'assert "R59_COLOR_MODES-1u)%R59_COLOR_MODES" in video',
      'assert "r59_color_mode=(r59_color_mode==1u)?2u:1u;" in video')
# R76 validates the original four hardware tables, which R91 retains,
# but the R91 menu intentionally exposes only A2 and L3.
patch('scripts/lab/test_r76_profiles.py',
      "assert 'Hybrid Blue' in menu and 'A2 Full' in menu and 'L3 Detail' in menu and 'HN Smooth' in menu",
      "assert 'A2 Full' in menu and 'L3 Detail' in menu and 'Hybrid Blue' not in menu and 'HN Smooth' not in menu")
patch('scripts/lab/build_r71a12mul_hud.py',"'r90-'","'r91-'")
patch('scripts/lab/build_r71a12mul_hud.py',"('control', 0)",repr((mode,0 if mode=='control' else int(mode[-1]))))
if mode!='control':
 patch(f,'#include "r79_shadow.inc"','#include "r79_shadow.inc"\n#include "r91_shadow.inc"')
 patch(f,'#define R79_PAL0 (r79_pal[r59_color_mode][0])','#define R79_PAL0 (r79_pal[r59_color_mode-1u][0])')
 patch(f,'#define R79_PAL1 (r79_pal[r59_color_mode][1])','#define R79_PAL1 (r79_pal[r59_color_mode-1u][1])')
 for bank in (0,1):
  patch('scripts/lab/test_r59_colorview.py',f'r79_pal[r59_color_mode][{bank}]',f'r79_pal[r59_color_mode-1u][{bank}]')
 patch(f,'''        R79_Convert((uint16_t *)(void *)r22_fb.pixels,
            r79_map[r59_color_mode][p],r79_cost[r59_color_mode][p]);''','''        if(p==0u)R91_ConvertFast((uint16_t *)(void *)r22_fb.pixels,r91_joint[r59_color_mode-1u]);
        else R79_Convert((uint16_t *)(void *)r22_fb.pixels,
            r79_map[r59_color_mode-1u][p],r79_cost[r59_color_mode-1u][p]);''')
 needle='                            python3 scripts/lab/test_r79_shadow.py --generated; or exit 1'
 patch('scripts/lab/build_r35_linear.fish',needle,needle+'\n                            python3 scripts/lab/gen_r91_shadow.py; or exit 1')
 needle="            for file in ('r79_shadow_report.json','r79_shadow_pairs.csv'):"
 patch('scripts/lab/build_r71a12mul_hud.py',needle,"            for file in ('r79_shadow_report.json','r79_shadow_pairs.csv','r91_shadow_report.json'):")
print('R91',mode,'R90-control base, A2/L3 only, Normal AI, PLAY')
