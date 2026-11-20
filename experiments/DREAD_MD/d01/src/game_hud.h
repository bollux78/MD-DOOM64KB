#ifndef GAME_HUD_H
#define GAME_HUD_H
#include "render.h"
#define VIEW_ROW0   6                          /* tile row of the 3D view */
#define VIEW_TOP_PX (VIEW_ROW0 * 8)
#define HUD_ROW0    (VIEW_ROW0 + VIEW_H / 8)   /* status bar right below the view */

typedef struct {
    uint16_t health, armor, ammo_cur;
    uint16_t ammo[4], maxammo[4];
    uint16_t arms, keys;
    int16_t face;
} HudState;

void HUD_Opening(void);
void HUD_Init(uint16_t row0);
void HUD_Draw(const HudState *st);
void HUD_WeaponFrame(uint16_t f);
void HUD_WeaponVBlank(void);
void HUD_WeaponBob(int16_t dx, int16_t dy);
#endif
