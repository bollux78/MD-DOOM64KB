#ifndef GAME_HUD_H
#define GAME_HUD_H
#include "render.h"
#define VIEW_ROW0   2                          /* tile row of the 3D view (H40, 144 lines on screen) */
#define VIEW_TOP_PX (VIEW_ROW0 * 8)
#define HUD_ROW0    (VIEW_ROW0 + 18)           /* status bar right below the 144-line view */
#define HUD_COL0    4                          /* 32-tile bar centred in H40 */

typedef struct {
    uint16_t health, armor, ammo_cur;
    uint16_t ammo[4], maxammo[4];
    uint16_t arms, keys;
    int16_t face;
} HudState;

#ifdef DREAD_GEOMETRY_ONLY
static inline void HUD_Opening(void) {}
static inline void HUD_Init(uint16_t row0) { (void)row0; }
static inline void HUD_Draw(const HudState *st) { (void)st; }
static inline void HUD_WeaponFrame(uint16_t f) { (void)f; }
static inline void HUD_VBlank(void) {}
static inline void HUD_Text(uint16_t line, const char *s) { (void)line; (void)s; }
static inline void HUD_WeaponBob(int16_t dx, int16_t dy) { (void)dx; (void)dy; }
static inline void HUD_SetLayout(uint16_t col0, int16_t dx) { (void)col0; (void)dx; }
#else
void HUD_Opening(void);
void HUD_ShowOpening(void);
void HUD_ClearOpening(void);
void HUD_Init(uint16_t row0);
void HUD_Draw(const HudState *st);
void HUD_WeaponFrame(uint16_t f);
void HUD_VBlank(void);
void HUD_Text(uint16_t line, const char *s);
void HUD_WeaponBob(int16_t dx, int16_t dy);
void HUD_SetLayout(uint16_t col0, int16_t dx);
#endif
#endif
