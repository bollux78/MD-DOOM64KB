#ifndef GAME_SFX_H
#define GAME_SFX_H
#ifdef DREAD_GAMEPLAY
void Game_Flash(void);
void Game_Sound(unsigned int id);
#else
#define Game_Sound(id) ((void)0)
#endif
#endif
