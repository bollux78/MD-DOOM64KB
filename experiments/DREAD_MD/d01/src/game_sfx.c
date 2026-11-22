#include <genesis.h>
#include "game_sfx.h"
#ifdef DREAD_GAMEPLAY
extern const u8 *const game_sfx[21];
extern const u32 game_sfx_len[21];
void Game_Sound(unsigned int id)
{
    if (id >= 21) return;
    if(id==0 || id==1 || id==4 || id==5)Game_Flash();
    XGM2_playPCMEx(game_sfx[id], game_sfx_len[id], id < 6 ? SOUND_PCM_CH2 : SOUND_PCM_CH3, id < 6 ? 10 : 6, TRUE, FALSE);
}
#endif
