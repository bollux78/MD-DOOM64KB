#ifndef GAME_WORLD_H
#define GAME_WORLD_H
#include "game_hud.h"
#ifdef DREAD_GAMEPLAY
void World_Init(uint16_t map);
uint16_t World_Tint(void);
void World_Power(uint16_t kind);
uint16_t World_Invulnerable(void);
uint16_t World_Invisible(void);
uint16_t World_Berserk(void);
void World_Shoot(const View *view);
void World_Door(uint16_t sector, uint16_t manual);
void World_Activate(uint16_t line, uint16_t crossing, View *view);
uint16_t World_Tick(uint16_t dt, View *view, HudState *hud);
#endif
#endif
