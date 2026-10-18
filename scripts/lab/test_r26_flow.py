#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess
R=Path(__file__).resolve().parents[2]
def fn(s,name):
 a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);level=0
 for i in range(b,len(s)):
  level+=(s[i]=='{')-(s[i]=='}')
  if not level:return s[a:i+1]
g=(R/'src/g_game.c').read_text();d=(R/'src/d_main.c').read_text();m=(R/'src/m_text.c').read_text()
popup=m[m.index('    if (!_g_menuactive)'):m.index('    // From here on, these navigation keys')]
code='''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#define __far
#define false 0
#define true 1
#define MAXPLAYERS 1
#define MIN_MAXPLAYERS 4
typedef unsigned char byte;typedef int skill_t;
int _g_basetic,_g_gametic,demolength=13,_g_gameaction,ga_loadgame=9;
struct {int cheats;} _g_player;
int chosen_map,chosen_skill;
void I_Error(const char *s){abort();}
void G_InitNew(int skill,int map){chosen_skill=skill;chosen_map=map;}
int pagetic=5,advances,levels,normal,sounds,_g_menuactive,_g_gamestate;
#define GS_DEMOSCREEN 1
#define key_menu_escape 7
#define sfx_swtchn 1
void D_AdvanceDemo(void){advances++;}
void M_R24OpenLevels(void){levels++;}
void M_StartControlPanel(void){normal++;}
void S_StartSound(void *p,int n){sounds++;}
'''+fn(g,'static void CheckForOverrun(')+'\n'+fn(g,'static const byte __far* G_ReadDemoHeader(')+'\n'+fn(d,'void D_PageTicker(')+'\nint popup(int ch){\n'+popup+'return 0;}\n'+'''
int main(void){
 byte header[13]={109,2,1,7,0,0,0,0,0,1,0,0,0};
 assert(G_ReadDemoHeader(header)==header+13 && chosen_skill==2);
#ifdef TIMEDEMO
 assert(chosen_map==1);
#else
 assert(chosen_map==7);
#endif
 _g_gamestate=GS_DEMOSCREEN;D_PageTicker();assert(pagetic==5 && !advances);
 assert(!popup(0) && !levels && !normal);
 assert(popup(7) && levels==1 && !normal);
 _g_gamestate=2;assert(popup(7) && normal==1 && levels==1);
 _g_menuactive=1;assert(!popup(7) && normal==1 && levels==1);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(code)
 for defs in [[],['-DTIMEDEMO']]:
  subprocess.run(['cc','-O2','-DDOOM_R26_FLOW','-DDOOM_R24_EPISODE',*defs,str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
print('PASS actual title ticker, Start routing and demo header: timedemo E1M1, playable demo retains original map')
