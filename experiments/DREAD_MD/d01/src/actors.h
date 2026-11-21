#ifndef DREAD_ACTORS_H
#define DREAD_ACTORS_H
#include "render.h"

#ifdef DREAD_COMBAT
#define ACTOR_NONE 0xFFFFu
typedef struct {
    MapThing thing;
    uint16_t next, hp, cooldown;
    uint8_t awake;
} Actor;

extern uint16_t actor_heads[];
extern Actor actors[];
void Actors_Init(void);
void Actors_Fire(const View *view);
void Actors_Tick(const View *view, uint16_t dt, uint16_t *health);
int ActorBlocked(int16_t x, int16_t y);
#endif
#endif
