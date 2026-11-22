#ifndef DREAD_ACTORS_H
#define DREAD_ACTORS_H
#include "render.h"

#ifdef DREAD_COMBAT
#define ACTOR_NONE 0xFFu

/* monsters (RAM copy of the map's monster things), Doom-like states */
typedef struct {
    int32_t x, y;                   /* 16.16 map units */
    uint16_t sub;
    int16_t hp;
    uint8_t kind, state, frame, tics;   /* frame = sprite letter (0 = A), tics in VBlanks */
    uint8_t dir, flags, movecount, reaction;
    uint8_t next, step;             /* subsector list link; animation step inside the state */
} Actor;

typedef struct {                    /* player state the monsters read and hurt */
    int16_t x, y, z;                /* z = eye height */
    uint16_t sub;
    uint16_t *health, *armor;
    uint8_t hurt;                   /* set when damaged this frame (HUD face) */
} ActorPlayer;

extern uint8_t actor_heads[];
extern Actor actors[];
void Actors_Init(void);
uint16_t Actors_BossDone(void);
int Actors_PlayerBlocked(int16_t x,int16_t y,int16_t z);
void Actors_Fire(const View *view, uint16_t pellets, uint16_t damage_mul);   /* hitscan from the view; wakes by noise */
void Actors_FireWeapon(const View *view, uint16_t weapon);
void Actors_Tick(ActorPlayer *pl, uint16_t dt);
void Actors_Draw(uint16_t sub);
int  Thing_Taken(uint16_t index);
void Thing_Take(uint16_t index);
int ActorBlockedFrom(int16_t x,int16_t y,int16_t ox,int16_t oy);
int  ActorBlocked(int16_t x, int16_t y);               /* player collision test (main.c), radius 16 */
extern volatile uint16_t combat_drop_ammo,combat_drop_shotgun;
extern volatile uint16_t combat_wakes, combat_hits, combat_kills, combat_attacks;
#endif
#endif
