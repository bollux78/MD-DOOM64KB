#!/usr/bin/env python3
"""R81 menu font, cheats and a versioned full-state SRAM slot on R79 base."""
from pathlib import Path
import subprocess
subprocess.run(['python3','scripts/lab/apply_r79.py'],check=True)
subprocess.run(['python3','scripts/lab/apply_r81_sram.py'],check=True)
subprocess.run(['python3','scripts/lab/gen_r81_archives.py'],check=True)
def patch(file,old,new):
 p=Path(file);s=p.read_text();assert s.count(old)==1,(file,old[:100],s.count(old));p.write_text(s.replace(old,new))
def function(file,name,body):
 p=Path(file);s=p.read_text();a=s.index('{',s.index(name));depth=1;b=a+1
 while depth:
  depth+=(s[b]=='{')-(s[b]=='}');b+=1
 p.write_text(s[:a]+'{\n'+body+'\n}'+s[b:])
patch('src/d_player.h','CF_GODMODE          = 2','CF_GODMODE          = 2,\n  CF_INFAMMO = 4')
p=Path('src/p_pspr.c');s=p.read_text();s=s.replace('if (ammo == am_noammo ||','if ((player->cheats&CF_INFAMMO) || ammo == am_noammo ||')
s=s.replace('player->ammo[weaponinfo[player->readyweapon].ammo]--;','if(!(player->cheats&CF_INFAMMO))player->ammo[weaponinfo[player->readyweapon].ammo]--;')
s=s.replace('if (!player->ammo[weaponinfo[player->readyweapon].ammo])','if (!(player->cheats&CF_INFAMMO) && !player->ammo[weaponinfo[player->readyweapon].ammo])');p.write_text(s)
patch('src/globdata.h','extern char _g_savegamestrings[8][8];','extern char _g_savegamestrings[1][8];')
p=Path('src/m_text.c');s=p.read_text().replace('#define DISABLE_SAVE_GAME','#if !defined(DOOM_R81_SAVE)\n#define DISABLE_SAVE_GAME\n#endif')
s=s.replace('char _g_savegamestrings[8][8];','char _g_savegamestrings[1][8];\n#include "r81_save.h"')
s=s.replace('  main_end\n','  r81_cheats,\n  main_end\n')
s=s.replace('static const menuitem_t MainMenu[]=','static void R81_OpenCheats(int16_t choice);\nstatic const menuitem_t MainMenu[]=')
s=s.replace('  {1,"New Game",  M_NewGame},','  {1,"New Game",  M_NewGame},')
s=s.replace('#if !defined DISABLE_QUIT_DOOM\n  {1,"Quit Game", M_QuitDOOM}\n#endif','#if !defined DISABLE_QUIT_DOOM\n  {1,"Quit Game", M_QuitDOOM},\n#endif\n  {1,"Cheats", R81_OpenCheats},')
a=s.index('static const menu_t MainDef =');b=s.index('\n};',a)+3;s=s[:b]+'\n#include "r81_cheats.inc"\n'+s[b:]
a=s.index('    load1,');b=s.index('    load_end',a);s=s[:a]+'    load1,\n'+s[b:]
s=s.replace('(R22_TEXTWIDTH - 5) / 2,5,','(R22_TEXTWIDTH - 5) / 2,4,')
s=s.replace('&MainDef,2,','&MainDef,loadgame,').replace('&MainDef,3,','&MainDef,savegame,');p.write_text(s)
function('src/m_text.c','static void M_LoadSelect(int16_t choice)\n',' (void)choice;const char *error=R81_LoadGame();\n if(error)M_StartMessage(error,NULL);else M_ClearMenus();')
function('src/m_text.c','static void M_DoSave(int16_t slot)\n',' (void)slot;const char *error=R81_SaveGame();\n if(error)M_StartMessage(error,NULL);else M_ClearMenus();')
function('src/m_text.c','static void M_ReadSaveStrings(void)\n',' R81_UpdateSaveStrings();')
function('src/g_game.c','void G_UpdateSaveGameStrings()',' R81_UpdateSaveStrings();')
function('src/g_game.c','static void G_DoLoadGame(void)\n',' const char *error=R81_LoadGame();if(error)_g_player.message=error;_g_gameaction=ga_nothing;')
function('src/g_game.c','static void G_DoSaveGame(void)\n',' const char *error=R81_SaveGame();if(error)_g_player.message=error;_g_gameaction=ga_nothing;')
p=Path('src/g_game.c');s=p.read_text().replace('static void G_InitNew(', 'static void __attribute__((noinline,used)) G_InitNew(').replace('#include "r24_romthings.h"','#include "r24_romthings.h"\n#include "r81_save.h"');p.write_text(s+'\n#include "r81_save_core.inc"\n')
p=Path('src/r22_video.inc');s=p.read_text();s='#include "r81_menu_font.h"\n'+s
needle='    /* Explicit solid tiles also guarantee transparent tile0 for Window.';assert needle in s
s=s.replace(needle,'    VDP_loadTileData((const uint32_t*)r81_menu_font,TILE_FONT_INDEX,96,CPU);\n'+needle)
s+='\nvoid *R81_SaveScratch(void){R20_StopVideo();return r22_fb.pixels;}\n';p.write_text(s)
p=Path('src/d_main.c');s=p.read_text();s+='''
void R81_ResyncInput(void){
 maketic=_g_gametic;
#if defined(DOOM_R50_PLAY_BENCH)
 r50_lastmadetic=I_GetTime();
#endif
 memset(&_g_player.cmd,0,sizeof(_g_player.cmd));
}
''';p.write_text(s)
patch('scripts/build_silent.fish','|HUD_WAD)','|HUD_WAD|R81_SAVE)')
patch('scripts/lab/build_r35_linear.fish',"            set defs $defs '-DDOOM_R78_ART'","            set defs $defs '-DDOOM_R78_ART' '-DDOOM_R81_SAVE'")
p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text().replace("for label,strength in (('base',0),('sh1',1),('sh2',2))","for label,strength in (('menu',0),)").replace("'r79-'+label","'r81-'+label").replace('assert len(records) == 6','assert len(records) == 2');p.write_text(s)
print('PASS R81 patches')

p=Path('scripts/lab/build_r35_linear.fish');s=p.read_text();needle='        tail -n 100 "$dest/build-$id.log"';assert s.count(needle)==1
s=s.replace(needle,'        grep -a -i -C 2 error "$dest/build-$id.log"\n'+needle);p.write_text(s)
