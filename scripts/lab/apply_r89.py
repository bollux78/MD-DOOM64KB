#!/usr/bin/env python3
"""Runtime Normal/Low selector on R88 AI PLAY, approved Low default."""
from pathlib import Path

def patch(f,a,b):
 p=Path(f);s=p.read_text();assert s.count(a)==1,(f,a[:80],s.count(a));p.write_text(s.replace(a,b))
Path('src/r89_ai.h').write_text('''#ifndef R89_AI_H
#define R89_AI_H
#include <stdint.h>
uint8_t R89_AIMode(void);
void R89_SetAIMode(uint8_t low);
#endif
''')
patch('src/p_enemy2.c','#include "globdata.h"','''#include "globdata.h"
#include "r89_ai.h"
static uint8_t r89_ai_low=1;
uint8_t R89_AIMode(void){return r89_ai_low;}
void R89_SetAIMode(uint8_t low){r89_ai_low=(low!=0);}''')
patch('src/p_enemy2.c','if(!_g_player.mo || !((_g_leveltime+a->type)&3u))return 0;', 'if(!r89_ai_low || !_g_player.mo || !((_g_leveltime+a->type)&3u))return 0;')
patch('src/m_text.c','#include "r81_save.h"','''#include "r81_save.h"
#include "r89_ai.h"
static void M_R89ChangeAI(int16_t choice){(void)choice;R89_SetAIMode(!R89_AIMode());}''')
patch('src/m_text.c','  alwaysrun,','  alwaysrun,\n  ai_mode,')
patch('src/m_text.c','  {1,"Always Run:",  M_ChangeAlwaysRun},','  {1,"Always Run:",  M_ChangeAlwaysRun},\n  {2,"AI mode:",     M_R89ChangeAI},')
patch('src/m_text.c','static void M_DrawOptions(void)\n{','''static void M_DrawOptions(void)
{
    V_DrawString(OptionsDef.x+13,OptionsDef.y+LINEHEIGHT*ai_mode,12,R89_AIMode()?"Low   ":"Normal");''')
patch('src/r22_benchmark.inc','/* Shared R21 benchmark implementation. */','/* Shared R21 benchmark implementation. */\n#include "r89_ai.h"')
patch('src/r22_benchmark.inc','    VDP_drawText("AVERAGE FPS", 5, 8);','    VDP_drawText(R89_AIMode()?"AI MODE: LOW":"AI MODE: NORMAL",5,6);\n    VDP_drawText("AVERAGE FPS", 5, 8);')
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text();assert "'r88-'" in s and "('ai',0)" in s;p.write_text(s.replace("'r88-'","'r89-'").replace("('ai',0)","('ai-menu',0)"))
print('R89 AI mode Normal/Low; default Low; PLAY only')
