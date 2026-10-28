#!/usr/bin/env python3
"""Exercise the real cheat toggle handler with a minimal player fixture."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
handler=(root/'src/r81_cheats.inc').read_text().split('static void R81_DrawCheats')[0]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)
 (p/'test.c').write_text('''#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#define CF_NOCLIP 1
#define CF_GODMODE 2
#define CF_INFAMMO 4
#define MF_NOCLIP 4096
#define GS_LEVEL 1
#define PST_DEAD 1
#define NUMWEAPONS 9
#define NUMAMMO 4
#define NUMCARDS 6
#define true 1
enum {wp_fist,wp_pistol,wp_shotgun,wp_chaingun,wp_missile,wp_plasma,wp_bfg,wp_chainsaw,wp_supershotgun};
typedef struct{int health;uint32_t flags;} mo_t;
static struct{int cheats,health,armorpoints,armortype,playerstate;int weaponowned[9],ammo[4],maxammo[4],cards[6];mo_t *mo;} _g_player;
static int _g_gamestate=GS_LEVEL,_g_usergame=1,_g_demoplayback=0,messages;
static void M_StartMessage(const char *s,void *cb){(void)s;(void)cb;messages++;}
'''+handler+'''
int main(void){
 mo_t mo={50,0};_g_player.mo=&mo;_g_player.health=50;
 for(int i=0;i<4;i++)_g_player.maxammo[i]=100+i;
 R81_ToggleCheat(0);assert(_g_player.cheats==2&&mo.health==100&&_g_player.health==100);
 R81_ToggleCheat(0);assert(!_g_player.cheats);
 R81_ToggleCheat(1);assert(_g_player.cheats==4&&_g_player.armorpoints==200&&_g_player.armortype==2);
 for(int i=0;i<4;i++)assert(_g_player.ammo[i]==100+i);
 for(int i=0;i<6;i++)assert(_g_player.cards[i]);
 assert(_g_player.weaponowned[wp_chainsaw]&&!_g_player.weaponowned[wp_plasma]&&!_g_player.weaponowned[wp_bfg]&&!_g_player.weaponowned[wp_supershotgun]);
 R81_ToggleCheat(2);assert(_g_player.cheats==5&&(mo.flags&MF_NOCLIP));
 R81_ToggleCheat(2);assert(_g_player.cheats==4&&!(mo.flags&MF_NOCLIP));
 R81_ToggleCheat(1);assert(!_g_player.cheats);
 _g_demoplayback=1;R81_ToggleCheat(0);assert(!_g_player.cheats&&messages==1);
 _g_demoplayback=0;_g_player.playerstate=PST_DEAD;R81_ToggleCheat(1);assert(!_g_player.cheats&&messages==2);
 puts("PASS actual cheat handler: independent toggles, IDKFA grants, noclip flag, live-game guards");
}''')
 subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
