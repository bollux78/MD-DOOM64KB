/* DREAD-MD: monsters, monster projectiles and item pickups (Doom-like rules, cheap on a 68000).
 *  - states: idle (look) -> chase (8-direction P_NewChaseDir walk) -> attack -> pain -> death -> corpse
 *  - wake by sight (REJECT table first, then a 16-bit grid trace, budgeted per frame) or by the noise of the
 *    player's shots (flood through sectors whose openings are not closed and lines without "block sound")
 *  - per-kind hit points, speed, pain chance and attacks (hitscan, shotgun, claws/bites, fireballs)
 *  - sprites: walk/attack/pain in rotations 1-5 (6-8 mirrored), death frames, corpse stays           */
#include "actors.h"
#include "game_sfx.h"
#include "world.h"
#ifdef DREAD_COMBAT
#include "mapcounts.h"

#if defined(__m68k__) || defined(__mc68000__)
static inline int32_t m16(int16_t a, int16_t b) { int32_t r = a; __asm__("muls.w %1,%0" : "+d"(r) : "dm"(b) : "cc"); return r; }
static inline int16_t d16(int32_t n, int16_t d) { __asm__("divs.w %1,%0" : "+d"(n) : "dm"(d) : "cc"); return (int16_t)n; }
#else
static inline int32_t m16(int16_t a, int16_t b) { return (int32_t)a * b; }
static inline int16_t d16(int32_t n, int16_t d) { return (int16_t)(n / d); }
#endif

enum { ST_IDLE, ST_CHASE, ST_ATK, ST_PAIN, ST_DEATH, ST_DEAD, ST_GONE };
enum { A_HITSCAN, A_SHOTGUN, A_IMP, A_BITE, A_SOUL, A_BARON, A_CACO };
#define DIR_NONE 8
#define MELEE 84                         /* melee range + radius, map units */

typedef struct {
    int16_t hp; uint8_t speed, chase, pain, attack;
    uint8_t walk0, walkn, atk0, atkn, painf, death0, deathn, corpse;
} KindInfo;
/* frames are sprite letters (A = 0); chase = VBlanks per walk step (Doom chase tics * 60/35) */
static const KindInfo kinds[8] = {
    {  20,  8, 7, 200, A_HITSCAN, 0, 4, 4, 2, 6,  7, 5, 1 },   /* zombieman   POSS */
    {  30,  8, 6, 170, A_SHOTGUN, 0, 4, 4, 2, 6,  7, 5, 1 },   /* sergeant    SPOS */
    {  60,  8, 5, 200, A_IMP,     0, 4, 4, 3, 7,  8, 5, 1 },   /* imp         TROO */
    { 150, 10, 4, 180, A_BITE,    0, 4, 4, 3, 7,  8, 6, 1 },   /* demon       SARG */
    { 150, 10, 4, 180, A_BITE,    0, 4, 4, 3, 7,  8, 6, 1 },   /* spectre     SARG */
    { 100,  8, 8, 255, A_SOUL,    0, 2, 2, 2, 4,  5, 6, 0 },   /* lost soul   SKUL */
    {1000,  8, 5,  50, A_BARON,   0, 4, 4, 3, 7,  8, 7, 1 },   /* baron       BOSS */
    { 400,  8, 5, 128, A_CACO,    0, 1, 1, 3, 4,  6, 6, 1 },   /* cacodemon   HEAD */
};
static const int16_t dirx[8] = { 256, 181, 0, -181, -256, -181, 0, 181 }, diry[8] = { 0, 181, 256, 181, 0, -181, -256, -181 };

Actor actors[MAP_NACTORS];
uint8_t actor_heads[MAP_NSUBS];
static uint16_t nactors, tick_no;
#ifdef DREAD_COMBAT_12_20
/* Experimental 60 Hz NTSC actor cadence: control=5, AI6=10, AI4=15.
 * Reducing actor dispatch ALSO slows its movement and animation. */
#ifndef DREAD_AI_PERIOD
#define DREAD_AI_PERIOD 5
#endif
#if DREAD_AI_PERIOD < 1 || DREAD_AI_PERIOD > 60
#error DREAD_AI_PERIOD must be between 1 and 60 VBlanks
#endif
#if 1
/* Keep the walking speed the control build has when the AI period is longer than 5 VBlanks.
 * A monster acts every ceil(chase/P)*P VBlanks (chase = VBlanks per walk step, P = AI period). The control
 * (P=5) therefore walks speed/gap(5) per VBlank for each kind; with a longer P one step must cover
 * speed*gap(P)/gap(5), otherwise AI6/AI4 simply slow the monsters down. blocked_from() (main.c) only looks
 * at lines within R=16 of the DESTINATION, so a step longer than 16 units could skip a thin wall: the
 * compensated step is capped at AI_STEP_MAX, and the fastest kinds end up slower than the control. */
#define AI_STEP_MAX 16
#define AI_GAP(chase, p) ((((chase) + (p) - 1) / (p)) * (p))
#endif
/* Menu option "IA": 100% = period 5 (control), 50% = period 10 with the walking speed kept (see above).
 * The period is a run-time variable so the menu can switch it; DREAD_AI_PERIOD is only its start value. */
static uint8_t ai_period = DREAD_AI_PERIOD;
static uint8_t sp_comp[8], sp_f[8], sp_for;
/* Per kind, for the current period P: step length (speed * gap(P) / gap(5)) and f = gap(P) / gap(5), how many control-rate
 * (5 VBlank) steps one AI step stands for. f = 2 for the kinds that walk every 5 VBlanks in the control. */
static void ai_comp_update(void)
{
    if (sp_for == ai_period) return;
    for (uint8_t k = 0; k < 8; k++) {
        sp_comp[k] = (uint8_t)(((uint16_t)kinds[k].speed * AI_GAP(kinds[k].chase, ai_period)) / AI_GAP(kinds[k].chase, 5));
        sp_f[k] = (uint8_t)(AI_GAP(kinds[k].chase, ai_period) / AI_GAP(kinds[k].chase, 5));
    }
    sp_for = ai_period;
}
/* Slow-AI attack tuning (run-time so it can be calibrated in the emulator): extra missile rolls per step and the reaction
 * delay after an attack starts. Control values at period 5 are fixed (3 and 1 roll) and never read these. */
volatile uint8_t ai_xroll = 0, ai_react = 1;
void Actors_SetAIHalf(uint8_t on) { ai_period = on ? 10 : 5; sp_for = 0; }
uint8_t Actors_AIHalf(void) { return ai_period != 5; }
/* VBlank-time fixed-step clocks, independent of rendered FPS.
 * 60 NTSC VBlanks/s -> AI at 12 Hz (5 VBlanks), projectiles at 20 Hz (3).
 * Remainders are carried across rendered frames so time does not drift. */
static uint8_t ai_vblank_accum, projectile_vblank_accum;
#endif
#ifdef DREAD_GAMEPLAY
#define MAXBARRELS 64
typedef struct {uint16_t thing;int16_t hp;uint8_t frame,tics,state,pad;} Barrel;
static Barrel barrels[MAXBARRELS];static uint16_t nbarrels;
/* Static solid scenery (thing type 81) as a compact list built at level start: scenery_blocked() is called for
 * every monster step and every player move test, and the old version walked ALL map things each time. */
#define MAXSCEN 255
typedef struct {int16_t x,y;uint16_t sec;} Scen;
static Scen scen[MAXSCEN];static uint8_t nscen;static uint8_t scen_overflow;
static void scen_build(void){
    nscen=0;scen_overflow=0;
    for(uint16_t i=0;i<map_nthings;i++){
        const MapThing *t=&map_things[i];if((t->flags&THING_MONSTER) || (t->flags>>8)!=81)continue;
        if(nscen>=MAXSCEN){scen_overflow=1;break;}
        scen[nscen].x=t->x;scen[nscen].y=t->y;scen[nscen].sec=map_subs[t->sub].sector;nscen++;
    }
}
static int scenery_blocked(int16_t x,int16_t y,int16_t z){
    if(scen_overflow){
        for(uint16_t i=0;i<map_nthings;i++){
            const MapThing *t=&map_things[i];if((t->flags&THING_MONSTER) || (t->flags>>8)!=81)continue;
            const int16_t f=map_sectors[map_subs[t->sub].sector].floor;
            if(z-41>=f+56 || z+15<=f)continue;
            const int32_t dx=x-t->x,dy=y-t->y;if(dx*dx+dy*dy<32*32)return 1;
        }
    }else for(uint8_t i=0;i<nscen;i++){
        const Scen *t=&scen[i];
        const int dx=x-t->x;if(dx>=32 || dx<=-32)continue;
        const int dy=y-t->y;if(dy>=32 || dy<=-32)continue;
        const int16_t f=map_sectors[t->sec].floor;
        if(z-41>=f+56 || z+15<=f)continue;
        if(m16((int16_t)dx,(int16_t)dx)+m16((int16_t)dy,(int16_t)dy)<32*32)return 1;
    }
    for(uint16_t i=0;i<nbarrels;i++)if(!barrels[i].state){
        const MapThing *t=&map_things[barrels[i].thing];
        const int dx=x-t->x;if(dx>=26 || dx<=-26)continue;
        const int dy=y-t->y;if(dy>=26 || dy<=-26)continue;
        const int16_t f=map_sectors[map_subs[t->sub].sector].floor;
        if(z-41>=f+42 || z+15<=f)continue;
        if(m16((int16_t)dx,(int16_t)dx)+m16((int16_t)dy,(int16_t)dy)<26*26)return 1;
    }return 0;
}
#endif
static uint8_t sight_budget;
volatile uint16_t combat_drop_ammo,combat_drop_shotgun;
typedef struct {int16_t x,y;uint16_t sub;uint8_t type,active;} Drop;
static Drop drops[32];static uint16_t drop_next;
volatile uint16_t combat_wakes, combat_hits, combat_kills, combat_attacks;

/* ---- random (Doom-style 0..255) */
static uint16_t rnd_s = 0x1234;
static uint8_t rnd(void) { rnd_s ^= rnd_s << 7; rnd_s ^= rnd_s >> 9; rnd_s ^= rnd_s << 8; return (uint8_t)rnd_s; }

/* ---- item pickups: taken bits for the map's static things */
static uint8_t taken[512];
int Thing_Taken(uint16_t i) { return i < 4096 && (taken[i >> 3] & (1 << (i & 7))); }
void Thing_Take(uint16_t i) { if (i < 4096) taken[i >> 3] |= (uint8_t)(1 << (i & 7)); }

/* ---- projectiles */
#define MAXPROJ 8
typedef struct { int32_t x, y, vx, vy; int16_t z,vz,zfrac; uint16_t sub; uint8_t kind, state, tics, frame; } Proj;
static Proj proj[MAXPROJ];

static inline int16_t iabs16(int16_t v) { return v < 0 ? -v : v; }
static inline uint16_t sector_of_sub(uint16_t sub) { return map_subs[sub].sector; }
static inline int16_t approx_dist(int16_t dx, int16_t dy)
{
    dx = iabs16(dx); dy = iabs16(dy);
    return dx > dy ? dx + (dy >> 1) : dy + (dx >> 1);
}
/* 8-way direction of (dx, dy): 0 = east, counter-clockwise; buckets centred on the axes and diagonals */
static uint8_t octant(int16_t dx, int16_t dy)
{
    const int16_t ax = iabs16(dx), ay = iabs16(dy);
    uint8_t o;
    if (m16(ay, 5) < m16(ax, 2)) o = 0;          /* |angle| < 22.5 (tan 22.5 ~ 0.4) */
    else if (m16(ax, 5) < m16(ay, 2)) o = 2;
    else o = 1;
    /* o is the octant in the first quadrant (0 east, 1 diagonal, 2 north): mirror to the quadrant */
    if (dx >= 0) return dy >= 0 ? o : (uint8_t)((8 - o) & 7);
    return dy >= 0 ? (uint8_t)(4 - o) : (uint8_t)(4 + o);
}

/* ---- sight: REJECT, then the line grid along the ray (16-bit products), openings at height z */
static int rejected(uint16_t s1, uint16_t s2)
{
    const uint32_t i = (uint32_t)s1 * map_counts[4] + s2;
    return (map_reject[i >> 3] >> (i & 7)) & 1;
}
static int trace3(int16_t ax,int16_t ay,int16_t az,int16_t bx,int16_t by,int16_t bz)
{
    const int16_t dx = bx - ax, dy = by - ay;
    const int16_t len = iabs16(dx) + iabs16(dy);
    if (len > 2400) return 0;
    const int16_t steps = (int16_t)((len >> 5) + 1);
    const int16_t sx = d16((int32_t)dx << 6, steps), sy = d16((int32_t)dy << 6, steps);   /* 1/64 units per step */
    int32_t x = (int32_t)ax << 6, y = (int32_t)ay << 6;
    uint16_t last = 0xFFFF;
    for (int16_t i = 0; i <= steps; i++, x += sx, y += sy) {
        const int16_t gx = (int16_t)(((x >> 6) - map_bm[0]) >> 7), gy = (int16_t)(((y >> 6) - map_bm[1]) >> 7);
        if (gx < 0 || gy < 0 || gx >= map_bm[2] || gy >= map_bm[3]) return 0;
        const uint16_t cell = (uint16_t)(gy * map_bm[2] + gx);
        if (cell == last) continue;
        last = cell;
        for (uint16_t k = map_bm_off[cell]; k < map_bm_off[cell + 1]; k++) {
            const MapLine *line = &map_lines[map_bm_list[k]];
            const int16_t *a = map_verts[line->v1], *b = map_verts[line->v2];
            const int32_t u = m16(dx, a[1] - ay) - m16(dy, a[0] - ax);
            const int32_t v = m16(dx, b[1] - ay) - m16(dy, b[0] - ax);
            if ((u < 0) == (v < 0)) continue;
            const int16_t lx = b[0] - a[0], ly = b[1] - a[1];
            const int32_t p = m16(lx, ay - a[1]) - m16(ly, ax - a[0]);
            const int32_t q = m16(lx, by - a[1]) - m16(ly, bx - a[0]);
            if ((p < 0) == (q < 0)) continue;
            if (line->back == NO_MAP_SECTOR) return 0;
            const MapSector *f = &map_sectors[line->front], *g = &map_sectors[line->back];
            const int16_t lo = f->floor > g->floor ? f->floor : g->floor, hi = sec_ceil[line->front] < sec_ceil[line->back] ? sec_ceil[line->front] : sec_ceil[line->back];
            /* Height at this actual intercept, rather than one midpoint Z
             * used for the whole ray. Grates are transparent to projectiles. */
            const int32_t den=p-q;
            const int16_t z=az+(den?(int32_t)((int64_t)(bz-az)*p/den):0);
            if (z <= lo || z >= hi) return 0;
        }
    }
    return 1;
}
static int trace(int16_t ax,int16_t ay,int16_t bx,int16_t by,int16_t z){return trace3(ax,ay,z,bx,by,z);}
/* 1 visible, 0 not, 2 not checked this frame (budget) */
static int can_see(const Actor *a, const ActorPlayer *pl, int force)
{
    if (rejected(sector_of_sub(a->sub), sector_of_sub(pl->sub))) return 0;
    if (!force) { if (!sight_budget) return 2; sight_budget--; }
    const int16_t ax = (int16_t)(a->x >> 16), ay = (int16_t)(a->y >> 16);
    const int16_t az = map_sectors[sector_of_sub(a->sub)].floor + 40;
    return trace3(pl->x,pl->y,pl->z,ax,ay,az);
}

/* ---- subsector lists */
static void unlink_actor(uint8_t i)
{
    uint8_t *link = &actor_heads[actors[i].sub];
    while (*link != i && *link != ACTOR_NONE) link = &actors[*link].next;
    if (*link == i) *link = actors[i].next;
}
static void link_actor(uint8_t i)
{
    actors[i].next = actor_heads[actors[i].sub];
    actor_heads[actors[i].sub] = i;
}

void Actors_Init(void)
{
#ifdef DREAD_GAMEPLAY
    scen_build();
    nbarrels=0;for(uint16_t i=0;i<map_nthings && nbarrels<MAXBARRELS;i++)if(!(map_things[i].flags&THING_MONSTER) && (map_things[i].flags>>8)==80){
        Barrel *b=&barrels[nbarrels++];b->thing=i;b->hp=20;b->state=b->frame=b->tics=0;
    }
#endif
    nactors = 0; tick_no = 0;drop_next=0;combat_drop_ammo=combat_drop_shotgun=0;for(uint16_t i=0;i<32;i++)drops[i].active=0;
#ifdef DREAD_COMBAT_12_20
    ai_vblank_accum = projectile_vblank_accum = 0; /* reset on every level load */
#endif
    combat_wakes = combat_hits = combat_kills = combat_attacks = 0;
    for (uint16_t i = 0; i < sizeof taken; i++) taken[i] = 0;
    for (uint16_t i = 0; i < MAXPROJ; i++) proj[i].kind = 0xFF;
    for (uint16_t i = 0; i < map_counts[2]; i++) actor_heads[i] = ACTOR_NONE;
    for (uint16_t i = 0; i < map_nthings && nactors < MAP_NACTORS && nactors < 255; i++) {
        const MapThing *t = &map_things[i];
        if (!(t->flags & THING_MONSTER)) continue;
        Actor *a = &actors[nactors];
        a->x = (int32_t)t->x << 16; a->y = (int32_t)t->y << 16; a->sub = t->sub;
        a->kind = (uint8_t)THING_KIND(t->flags);
        a->hp = kinds[a->kind].hp;
        a->state = ST_IDLE; a->frame = 0; a->tics = (uint8_t)(i & 15); a->step = 0;
        a->dir = (uint8_t)THING_DIR(t->flags);
        a->flags = (t->flags & THING_AMBUSH) ? 1 : 0;
        a->movecount = 0; a->reaction = 2;
        link_actor((uint8_t)nactors);
        nactors++;
    }
}

static void wake(Actor *a)
{
    if (a->state != ST_IDLE) return;
    a->state = ST_CHASE; a->tics = 1; a->step = 0; a->reaction = 2;
    combat_wakes++;Game_Sound(a->kind<2?12:a->kind==6?16:14);
}

/* ---- movement */
static int try_move(Actor *a, uint8_t i, uint8_t dir, const ActorPlayer *pl)
{
    if (dir >= 8) return 0;
    int16_t sp = kinds[a->kind].speed;
    if (ai_period != 5) {
        ai_comp_update();
        sp = sp_comp[a->kind] > AI_STEP_MAX ? AI_STEP_MAX : sp_comp[a->kind];
    }
    const int16_t x = (int16_t)(a->x >> 16), y = (int16_t)(a->y >> 16);
    const int16_t nx = x + (int16_t)((sp * dirx[dir]) >> 8), ny = y + (int16_t)((sp * diry[dir]) >> 8);
    if (iabs16(nx - pl->x) < 32 && iabs16(ny - pl->y) < 32) return 0;
    for (uint16_t k = 0; k < nactors; k++) {
        const Actor *o = &actors[k];
        if (k == i || o->state >= ST_DEATH) continue;
        if (iabs16((int16_t)(o->x >> 16) - nx) < 32 && iabs16((int16_t)(o->y >> 16) - ny) < 32) return 0;
    }
    const MapSector *from = &map_sectors[sector_of_sub(a->sub)];
    const uint16_t tos = map_subs[R_PointInSub(nx, ny)].sector;
    const MapSector *to = &map_sectors[tos];
    const int16_t toc = sec_ceil[tos];
    if (to->floor - from->floor > 24 || toc - to->floor < 56 || toc - from->floor < 56) return 0;
#ifdef DREAD_GAMEPLAY
    if(scenery_blocked(nx,ny,from->floor+41))return 0;
#endif
    if (ActorBlockedFrom(nx, ny,a->x>>16,a->y>>16)) return 0;
    a->x = (int32_t)nx << 16; a->y = (int32_t)ny << 16;
    const uint16_t sub = (uint16_t)R_PointInSub(nx, ny);
    if (sub != a->sub) { unlink_actor(i); a->sub = sub; link_actor(i); }
    return 1;
}
/* Doom's P_NewChaseDir */
static void new_chase_dir(Actor *a, uint8_t i, const ActorPlayer *pl)
{
    const int16_t dx = pl->x - (int16_t)(a->x >> 16), dy = pl->y - (int16_t)(a->y >> 16);
    const uint8_t old = a->dir, turn = old < 8 ? (uint8_t)((old + 4) & 7) : DIR_NONE;
    uint8_t d1 = dx > 10 ? 0 : dx < -10 ? 4 : DIR_NONE, d2 = dy < -10 ? 6 : dy > 10 ? 2 : DIR_NONE;
    if (d1 != DIR_NONE && d2 != DIR_NONE) {
        const uint8_t diag = d1 == 0 ? (d2 == 2 ? 1 : 7) : (d2 == 2 ? 3 : 5);
        if (diag != turn && try_move(a, i, diag, pl)) { a->dir = diag; a->movecount = rnd() & 15; return; }
    }
    if (rnd() > 200 || iabs16(dy) > iabs16(dx)) { const uint8_t t = d1; d1 = d2; d2 = t; }
    if (d1 == turn) d1 = DIR_NONE;
    if (d2 == turn) d2 = DIR_NONE;
    if (d1 != DIR_NONE && try_move(a, i, d1, pl)) { a->dir = d1; a->movecount = rnd() & 15; return; }
    if (d2 != DIR_NONE && try_move(a, i, d2, pl)) { a->dir = d2; a->movecount = rnd() & 15; return; }
    if (old < 8 && try_move(a, i, old, pl)) { a->movecount = rnd() & 15; return; }
    const int8_t s = (rnd() & 1) ? 1 : -1;
    for (int8_t k = 0, t = s > 0 ? 0 : 7; k < 8; k++, t = (int8_t)((t + s) & 7))
        if ((uint8_t)t != turn && try_move(a, i, (uint8_t)t, pl)) { a->dir = (uint8_t)t; a->movecount = rnd() & 15; return; }
    if (turn != DIR_NONE && try_move(a, i, turn, pl)) { a->dir = turn; a->movecount = rnd() & 15; return; }
    a->dir = DIR_NONE;
}

/* ---- damage */
static void hurt_player(ActorPlayer *pl, int16_t dmg)
{
#ifdef DREAD_GAMEPLAY
    if(World_Invulnerable())return;
#endif
#ifdef DREAD_EASY_MODE
    /* Doom easy skill: halve incoming damage before armor; keep minimum 1. */
    if (dmg > 0) dmg = (int16_t)((dmg + 1) / 2);
#endif
    if (*pl->armor) {                    /* green armor rule: 1/3 absorbed */
        int16_t save = dmg / 3;
        if (save > (int16_t)*pl->armor) save = (int16_t)*pl->armor;
        *pl->armor -= (uint16_t)save; dmg -= save;
    }
    *pl->health = (uint16_t)(*pl->health > (uint16_t)dmg ? *pl->health - dmg : 0);
    pl->hurt = 1;Game_Sound(11);
    combat_attacks++;
}
static void damage_actor(Actor *a, int16_t dmg)
{
    if (a->state >= ST_DEATH) return;
    combat_hits++;
    a->hp -= dmg;
    if (a->hp <= 0) {
        a->state = ST_DEATH; a->step = 0; a->frame = kinds[a->kind].death0; a->tics = 8;
        if(a->kind<2){Drop *d=&drops[drop_next++&31];d->x=a->x>>16;d->y=a->y>>16;d->sub=a->sub;d->type=a->kind;d->active=1;}
        combat_kills++;Game_Sound(a->kind<2?13:a->kind==6?17:15);
        return;
    }
    if (a->state == ST_IDLE) { a->state = ST_CHASE; combat_wakes++; }
    if (rnd() < kinds[a->kind].pain) { a->state = ST_PAIN; a->frame = kinds[a->kind].painf; a->tics = 6; }
}

static void spawn_ball(const Actor *a, const ActorPlayer *pl, uint8_t kind)
{
    for (uint16_t k = 0; k < MAXPROJ; k++) {
        Proj *p = &proj[k];
        if (p->kind != 0xFF) continue;
        const int16_t x = (int16_t)(a->x >> 16), y = (int16_t)(a->y >> 16);
        int16_t dx = pl->x - x, dy = pl->y - y;
#ifdef DREAD_GAMEPLAY
        if(World_Invisible()){dx+=(int16_t)((int16_t)rnd()-128);dy+=(int16_t)((int16_t)rnd()-128);}
#endif
        const int16_t d=approx_dist(dx,dy);
        const int32_t speed = kind == 1 ? 0x8C000 : 0x5D000;              /* 8.75 / 5.8 units per VBlank */
        p->x = a->x; p->y = a->y;
        p->vx = d ? (int32_t)(((int64_t)dx * speed) / d) : 0;
        p->vy = d ? (int32_t)(((int64_t)dy * speed) / d) : 0;
        p->z = map_sectors[sector_of_sub(a->sub)].floor + 32;
        p->zfrac=0;int16_t ticks=d/(kind==1?9:6);if(ticks<1)ticks=1;p->vz=((int32_t)(pl->z-8-p->z)*256)/ticks;
        p->sub = a->sub; p->kind = kind; p->state = 0; p->tics = 0; p->frame = 0;
        return;
    }
}

static void attack(Actor *a, ActorPlayer *pl, int16_t dist)
{
    Game_Sound(a->kind<2?0:12);
    const KindInfo *k = &kinds[a->kind];
    const int seen = can_see(a, pl, 1);
    if (!seen) return;
    switch (k->attack) {
    case A_HITSCAN:
    case A_SHOTGUN: {
        const uint8_t chance = dist < 128 ? 224 : dist < 512 ? 160 : 96;
        for (uint16_t n = k->attack == A_SHOTGUN ? 3 : 1; n; n--)
            if (rnd() <
#ifdef DREAD_GAMEPLAY
                (World_Invisible()?chance/3:chance)
#else
                chance
#endif
                ) hurt_player(pl, (int16_t)(((rnd() % 5) + 1) * 3));
        break;
    }
    case A_IMP:   if (dist < MELEE) hurt_player(pl, (int16_t)(((rnd() & 7) + 1) * 3)); else spawn_ball(a, pl, 0); break;
    case A_BITE:  if (dist < MELEE) hurt_player(pl, (int16_t)(((rnd() % 10) + 1) * 4)); break;
    case A_SOUL:  if (dist < MELEE) hurt_player(pl, (int16_t)(((rnd() & 7) + 1) * 3)); break;
    case A_BARON: if (dist < MELEE) hurt_player(pl, (int16_t)(((rnd() & 7) + 1) * 10)); else spawn_ball(a, pl, 1); break;
    case A_CACO:  if (dist < MELEE) hurt_player(pl, (int16_t)(((rnd() % 6) + 1) * 10)); else spawn_ball(a, pl, 2); break;
    }
}

/* one walk step of an awake monster (Doom's A_Chase, simplified) */
static void chase(Actor *a, uint8_t i, ActorPlayer *pl)
{
    const KindInfo *k = &kinds[a->kind];
    const int16_t x = (int16_t)(a->x >> 16), y = (int16_t)(a->y >> 16);
    const int16_t dist = approx_dist(pl->x - x, pl->y - y);
    /* Slow AI (period 10): one step stands for f control steps, so the reaction time counts down f at a time and the
     * missile roll is made f times; at period 5 f = 1 and this is exactly the control (same random numbers). */
    uint8_t f = 1;
    if (ai_period != 5) { ai_comp_update(); f = sp_f[a->kind]; }
    if (a->reaction) a->reaction = a->reaction > f ? (uint8_t)(a->reaction - f) : 0;
    /* melee */
    if (dist < MELEE && (k->attack == A_IMP || k->attack == A_BITE || k->attack == A_SOUL || k->attack == A_BARON || k->attack == A_CACO)) {
        if (can_see(a, pl, 0) == 1) goto start_attack;
    }
    /* missile / hitscan: Doom's P_CheckMissileRange odds */
    if (!a->reaction && k->attack != A_BITE && k->attack != A_SOUL) {
        int16_t d = dist - 64;
        if (d > 200) d = 200;
        if (d < 0) d = 0;
        for (uint8_t r = 0, nr = (uint8_t)(f + (ai_period != 5 ? ai_xroll : 0)); r < nr; r++) if (rnd() >= d && can_see(a, pl, 0) == 1) goto start_attack;
    }
    if (a->movecount) a->movecount = a->movecount > f ? (uint8_t)(a->movecount - f) : 0;
    if (!a->movecount || a->dir >= 8 || !try_move(a, i, a->dir, pl)) new_chase_dir(a, i, pl);
    a->step = (uint8_t)((a->step + 1) % k->walkn);
    a->frame = (uint8_t)(k->walk0 + a->step);
    a->tics = k->chase;
    return;
start_attack:
    a->state = ST_ATK; a->step = 0; a->frame = k->atk0; a->tics = 10;
    a->dir = octant(pl->x - x, pl->y - y);
    a->reaction = ai_period != 5 ? ai_react : 3;
}

static void look(Actor *a, const ActorPlayer *pl)
{
    const int16_t dx = pl->x - (int16_t)(a->x >> 16), dy = pl->y - (int16_t)(a->y >> 16);
    if (approx_dist(dx, dy) > 2048) return;
    if (approx_dist(dx, dy) > 64 && a->dir < 8 && m16(dx, dirx[a->dir]) + m16(dy, diry[a->dir]) < 0) return;   /* behind it */
    if (can_see(a, pl, 0) == 1) wake(a);
}

/* player's shots wake every non-ambush monster that can hear: flood through open two-sided lines */
static uint8_t secmark[MAP_NSECTORS];
static uint16_t secq[MAP_NSECTORS];
static void noise(uint16_t from)
{
    const uint16_t nsec = map_counts[4];
    for (uint16_t i = 0; i < nsec; i++) secmark[i] = 0;
    uint16_t head = 0, tail = 0;
    secq[tail++] = from; secmark[from] = 1;
    while (head < tail) {
        const uint16_t s = secq[head++];
        const MapSector *ss = &map_sectors[s];
        for (uint16_t k = map_secadj_off[s]; k < map_secadj_off[s + 1]; k++) {
            const uint16_t n = map_secadj[k];
            if (secmark[n]) continue;
            const MapSector *ns = &map_sectors[n];
            const int16_t lo = ss->floor > ns->floor ? ss->floor : ns->floor, hi = sec_ceil[s] < sec_ceil[n] ? sec_ceil[s] : sec_ceil[n];
            if (hi <= lo) continue;                                    /* closed door */
            secmark[n] = 1; secq[tail++] = n;
        }
    }
    for (uint16_t i = 0; i < nactors; i++) {
        Actor *a = &actors[i];
        if (a->state == ST_IDLE && !(a->flags & 1) && secmark[sector_of_sub(a->sub)]) wake(a);
    }
}

#ifdef DREAD_GAMEPLAY
static void damage_barrel(uint16_t i,int16_t damage){Barrel *b=&barrels[i];if(b->state)return;b->hp-=damage;if(b->hp<=0){b->state=1;b->tics=6;b->frame=0;}}
static void tick_barrels(ActorPlayer *pl){
    for(uint16_t i=0;i<nbarrels;i++){
        Barrel *b=&barrels[i];if(b->state!=1)continue;
        if(b->tics && --b->tics)continue;
        if(++b->frame==2){
            const MapThing *t=&map_things[b->thing];int16_t z=map_sectors[map_subs[t->sub].sector].floor+24;Game_Sound(5);
            for(uint16_t j=0;j<nactors;j++)if(actors[j].state<ST_DEATH){int16_t d=approx_dist((actors[j].x>>16)-t->x,(actors[j].y>>16)-t->y);if(d<128 && trace(t->x,t->y,actors[j].x>>16,actors[j].y>>16,z))damage_actor(&actors[j],128-d);}
            for(uint16_t j=0;j<nbarrels;j++)if(!barrels[j].state){const MapThing *o=&map_things[barrels[j].thing];int16_t d=approx_dist(o->x-t->x,o->y-t->y);if(d<128 && trace(t->x,t->y,o->x,o->y,z))damage_barrel(j,128-d);}
            int16_t d=approx_dist(pl->x-t->x,pl->y-t->y);if(d<128 && trace(t->x,t->y,pl->x,pl->y,z))hurt_player(pl,128-d);
        }
        if(b->frame>=5)b->state=2;else b->tics=6;
    }
}
#endif

static void fire_range(const View *view, uint16_t pellets, uint16_t damage_mul, uint16_t range)
{
    const int16_t x = (int16_t)(view->x >> 16), y = (int16_t)(view->y >> 16);
    const uint16_t ang = view->angle >> 6;
    const int16_t c = sintab[(ang + 256) & 1023], s = sintab[ang];
    const uint16_t psub = (uint16_t)R_PointInSub(x, y);
    noise(sector_of_sub(psub));
    ActorPlayer pl = { x, y, view->z, psub, 0, 0, 0 };
    for (; pellets; pellets--) {
        uint16_t target = 0xFFFF;
        int32_t nearest = range;
        for (uint16_t i = 0; i < nactors; i++) {
            const Actor *a = &actors[i];
            if (a->state >= ST_DEATH) continue;
            const int16_t dx = (int16_t)(a->x >> 16) - x, dy = (int16_t)(a->y >> 16) - y;
            if (iabs16(dx) > 2000 || iabs16(dy) > 2000) continue;
            const int32_t depth = (m16(dx, c) + m16(dy, s)) >> 14;
            if (depth <= 0 || depth >= nearest) continue;
            const int32_t lat = (m16(dx, s) - m16(dy, c)) >> 14;
            const int32_t tol = depth > 160 ? depth >> 3 : 20;      /* autoaim ~7 degrees, at least the body */
            if ((lat < 0 ? -lat : lat) > tol) continue;
            if (!can_see(a, &pl, 1)) continue;
            target = i; nearest = depth;
        }
#ifdef DREAD_GAMEPLAY
        uint16_t barrel=0xffff;
        for(uint16_t i=0;i<nbarrels;i++)if(!barrels[i].state){
            const MapThing *t=&map_things[barrels[i].thing];const int16_t dx=t->x-x,dy=t->y-y;
            const int32_t depth=(m16(dx,c)+m16(dy,s))>>14,lat=(m16(dx,s)-m16(dy,c))>>14;
            const int16_t z=map_sectors[map_subs[t->sub].sector].floor;
            if(depth>0 && depth<nearest && iabs16(lat)<16 && view->z>=z && view->z<=z+64 && trace(x,y,t->x,t->y,z+24)){nearest=depth;barrel=i;}
        }
        if(barrel!=0xffff){damage_barrel(barrel,(damage_mul&0x8000)?(damage_mul&0x7fff):damage_mul*((rnd()%3)+1));continue;}
#endif
        if (target != 0xFFFF) damage_actor(&actors[target], (int16_t)((damage_mul&0x8000)?(damage_mul&0x7fff):damage_mul * ((rnd() % 3) + 1)));
    }
}

void Actors_Fire(const View *view,uint16_t pellets,uint16_t damage_mul){fire_range(view,pellets,damage_mul,2048);}
void Actors_FireWeapon(const View *v,uint16_t weapon)
{
    if(weapon==0 || weapon==5){uint16_t damage=2*((rnd()%10)+1);
#ifdef DREAD_GAMEPLAY
        if(weapon==0 && World_Berserk())damage*=10;
#endif
        fire_range(v,1,0x8000|damage,84);return;}
#ifdef DREAD_GAMEPLAY
    if(weapon!=4)World_Shoot(v);
#endif
    if(weapon==2){
        for(uint16_t i=0;i<7;i++){View shot=*v;shot.angle+=(int16_t)((int16_t)(rnd()&255)-128)*5;fire_range(&shot,1,5,2048);}return;
    }
    /* Rocket travel and splash use a player-owned projectile slot. */
    if(weapon==4){
        for(uint16_t i=0;i<MAXPROJ;i++)if(proj[i].kind==0xff){
            Proj *p=&proj[i];const uint16_t a=v->angle>>6;
            p->x=v->x;p->y=v->y;p->vx=(int32_t)sintab[(a+256)&1023]*80;p->vy=(int32_t)sintab[a]*80;
            p->z=v->z-8;p->vz=p->zfrac=0;
            int32_t nearest=2048;
            for(uint16_t id=0;id<nactors;id++)if(actors[id].state<ST_DEATH){
                Actor *o=&actors[id];int16_t dx=(o->x-v->x)>>16,dy=(o->y-v->y)>>16;
                int32_t depth=(m16(dx,sintab[(a+256)&1023])+m16(dy,sintab[a]))>>14,lat=(m16(dx,sintab[a])-m16(dy,sintab[(a+256)&1023]))>>14;
                int16_t z=map_sectors[sector_of_sub(o->sub)].floor+28;
                if(depth>0 && depth<nearest && iabs16(lat)<(depth>160?depth>>3:20) && trace3(v->x>>16,v->y>>16,p->z,o->x>>16,o->y>>16,z)){
                    nearest=depth;int16_t ticks=depth/20;if(ticks<1)ticks=1;p->vz=((int32_t)(z-p->z)*256)/ticks;
                }
            }
            p->kind=3;p->state=0;p->tics=0;p->frame=0;p->sub=R_PointInSub(v->x>>16,v->y>>16);break;
        }return;
    }
    fire_range(v,1,5,2048);
}

static void tick_proj(ActorPlayer *pl, uint16_t dt)
{
    for (uint16_t k = 0; k < MAXPROJ; k++) {
        Proj *p = &proj[k];
        if (p->kind == 0xFF) continue;
        if (p->state) {                                   /* exploding: C D E */
            if (p->tics > dt) { p->tics -= (uint8_t)dt; continue; }
            if (++p->frame >= 3) { p->kind = 0xFF; continue; }
            p->tics = 6; continue;
        }
        /* Substeps prevent a fast projectile crossing a thin wall at low FPS. */
        int wallhit=0;
        for(uint16_t step=0;step<dt;step++) {
            const int16_t ox=p->x>>16,oy=p->y>>16;
            const int16_t oz=p->z;
            p->x+=p->vx;p->y+=p->vy;p->zfrac+=p->vz;p->z+=p->zfrac>>8;p->zfrac&=255;
            if(!trace3(ox,oy,oz,p->x>>16,p->y>>16,p->z)){wallhit=1;break;}
            if(p->kind==3){
                for(uint16_t id=0;id<nactors;id++)if(actors[id].state<ST_DEATH && approx_dist((actors[id].x-p->x)>>16,(actors[id].y-p->y)>>16)<24){
                    damage_actor(&actors[id],20*((rnd()&7)+1));wallhit=1;break;
                }
                if(wallhit)break;
            }
        }
        const int16_t x = (int16_t)(p->x >> 16), y = (int16_t)(p->y >> 16);
        p->tics += (uint8_t)dt; if (p->tics > 7) { p->tics = 0; p->frame ^= 1; }
        int boom = wallhit;
        if (p->kind!=3 && iabs16(x - pl->x) < 20 && iabs16(y - pl->y) < 20 && p->z >= pl->z - 48 && p->z <= pl->z + 16) {
            hurt_player(pl, (int16_t)(((rnd() & 7) + 1) * (p->kind == 1 ? 8 : p->kind == 2 ? 5 : 3)));
            boom = 1;
        } else {
            const int sub = R_PointInSub(x, y);
            const MapSector *sec = &map_sectors[map_subs[sub].sector];
            p->sub = (uint16_t)sub;
            if (p->z < sec->floor || p->z + 8 > sec_ceil[map_subs[sub].sector]) boom = 1;
        }
#ifdef DREAD_GAMEPLAY
        for(uint16_t bi=0;bi<nbarrels;bi++)if(!barrels[bi].state){const MapThing *t=&map_things[barrels[bi].thing];if(approx_dist(x-t->x,y-t->y)<16){damage_barrel(bi,20);boom=1;}}
#endif
        if (boom && p->kind==3) {
            for(uint16_t id=0;id<nactors;id++)if(actors[id].state<ST_DEATH){
                const int16_t d=approx_dist((actors[id].x-p->x)>>16,(actors[id].y-p->y)>>16);
                if(d<128 && trace(x,y,actors[id].x>>16,actors[id].y>>16,p->z))damage_actor(&actors[id],128-d);
            }
            const int16_t d=approx_dist(x-pl->x,y-pl->y);if(d<128)hurt_player(pl,128-d);
            Game_Sound(5);
        }
        if (boom) { p->state = 1; p->frame = 0; p->tics = 6; }
    }
}

/* Picking up drops requires only one test per rendered update. In the
 * original scheduler it was repeated once for each elapsed VBlank. */
static void tick_drops(ActorPlayer *pl)
{
    for (uint16_t i = 0; i < 32; i++)
        if (drops[i].active &&
            approx_dist(drops[i].x - pl->x, drops[i].y - pl->y) < 24 &&
            iabs16(map_sectors[map_subs[drops[i].sub].sector].floor - (pl->z - 41)) < 24) {
            if (drops[i].type) combat_drop_shotgun++;
            else combat_drop_ammo += 5;
            drops[i].active = 0;
            Game_Sound(6);
        }
}

static void actors_step(ActorPlayer *pl, uint16_t dt)
{
    tick_no++;
#ifndef DREAD_COMBAT_12_20
#ifdef DREAD_GAMEPLAY
    tick_barrels(pl);
#endif
    pl->hurt = 0;
#endif
    for (uint16_t i = 0; i < nactors; i++) {
        Actor *a = &actors[i];
        if (a->state >= ST_DEAD) continue;
        if (a->tics > dt) { a->tics -= (uint8_t)dt; continue; }
        const KindInfo *k = &kinds[a->kind];
        switch (a->state) {
        case ST_IDLE:
            a->tics = 16;
            look(a, pl);
            break;
        case ST_CHASE:
            chase(a, (uint8_t)i, pl);
            break;
        case ST_ATK:
            if (++a->step < k->atkn) {
                a->frame = (uint8_t)(k->atk0 + a->step); a->tics = 10;
                if (a->step == k->atkn - 1) {
                    const int16_t dist = approx_dist(pl->x - (int16_t)(a->x >> 16), pl->y - (int16_t)(a->y >> 16));
                    attack(a, pl, dist);
                }
            } else { a->state = ST_CHASE; a->step = 0; a->tics = k->chase; a->frame = k->walk0; }
            break;
        case ST_PAIN:
            a->state = ST_CHASE; a->tics = k->chase; a->frame = k->walk0;
            break;
        case ST_DEATH:
            if (++a->step < k->deathn) { a->frame = (uint8_t)(k->death0 + a->step); a->tics = 8; }
            else a->state = k->corpse ? ST_DEAD : ST_GONE;
            break;
        }
    }
#ifndef DREAD_COMBAT_12_20
    tick_proj(pl, dt);
    tick_drops(pl);
#endif
}

void Actors_Tick(ActorPlayer *pl,uint16_t dt)
{
    sight_budget = 3;
#ifdef DREAD_COMBAT_12_20
    /* Reaction/hit animations, wake/chase/attack states: maximum 12 updates
     * per simulated second. This avoids traversing all actors per VBlank. */
    pl->hurt = 0;
#ifdef DREAD_GAMEPLAY
    /* Barrel explosion timing stays in original 60 Hz VBlank units. */
    for (uint16_t tick = 0; tick < dt; tick++) tick_barrels(pl);
#endif
    uint16_t acc = (uint16_t)ai_vblank_accum + dt;
    while (acc >= ai_period) {
        acc -= ai_period;
        actors_step(pl, ai_period);
    }
    ai_vblank_accum = (uint8_t)acc;

    /* Physics is stepped at 20 Hz but each step still checks its three
     * one-VBlank movement substeps (tick_proj), preventing tunneling through
     * narrow walls at the expense of some retained collision work. */
    acc = (uint16_t)projectile_vblank_accum + dt;
    while (acc >= 3) {
        acc -= 3;
        tick_proj(pl, 3);
    }
    projectile_vblank_accum = (uint8_t)acc;
    tick_drops(pl);  /* once per rendered update, even if no AI step was due */
#else
    for(uint16_t tick=0;tick<dt;tick++)actors_step(pl,1);
#endif
}

/* sprite of a monster seen from the camera: rotation from the camera's direction relative to its facing */
int Actors_PlayerBlocked(int16_t x,int16_t y,int16_t z)
{
#ifdef DREAD_GAMEPLAY
    if(scenery_blocked(x,y,z))return 1;
#endif
    for(uint16_t i=0;i<nactors;i++){
        const Actor *a=&actors[i];if(a->state>=ST_DEATH)continue;
        const int16_t floor=map_sectors[map_subs[a->sub].sector].floor;
        if(z-41>=floor+56 || z+15<=floor)continue;
        const int32_t dx=(a->x>>16)-x,dy=(a->y>>16)-y;
        const int16_t radius=a->kind==3 || a->kind==4?44:36;
        if(dx*dx+dy*dy<(int32_t)radius*radius)return 1;
    }return 0;
}
uint16_t Actors_BossDone(void)
{
    uint16_t found=0;for(uint16_t i=0;i<nactors;i++)if(actors[i].kind==6){found=1;if(actors[i].state<ST_DEATH)return 0;}return found;
}
/* Per-frame lists of the dynamic things worth drawing (barrels still standing, active drops, live projectiles):
 * Actors_Draw() runs for every visible subsector, and scanning 32 drops + 8 projectiles + all barrels in each
 * call cost ~6% of the frame. Lists are built once per rendered frame, in index order, so draw order is unchanged. */
static uint8_t fd_drop[32], fd_nd, fd_proj[MAXPROJ], fd_np;
#ifdef DREAD_GAMEPLAY
static uint8_t fd_bar[MAXBARRELS], fd_nb;
#endif
/* one bit per subsector that holds at least one of those things, so Actors_Draw skips the three scans elsewhere */
static uint8_t fd_sub[(MAP_NSUBS + 7) >> 3];
#define FD_SET(s) do { if ((s) < MAP_NSUBS) fd_sub[(s) >> 3] |= (uint8_t)(1u << ((s) & 7)); } while (0)
void Actors_FrameBegin(void)
{
    for (uint8_t i = 0; i < sizeof fd_sub; i++) fd_sub[i] = 0;
    fd_nd = 0; for (uint8_t i = 0; i < 32; i++) if (drops[i].active) { fd_drop[fd_nd++] = i; FD_SET(drops[i].sub); }
    fd_np = 0; for (uint8_t k = 0; k < MAXPROJ; k++) if (proj[k].kind != 0xFF) { fd_proj[fd_np++] = k; FD_SET(proj[k].sub); }
#ifdef DREAD_GAMEPLAY
    fd_nb = 0; for (uint8_t i = 0; i < nbarrels; i++) if (barrels[i].state != 2) { fd_bar[fd_nb++] = i; FD_SET(map_things[barrels[i].thing].sub); }
#endif
}

void Actors_Draw(uint16_t sub)
{
    extern int16_t r_view_xi, r_view_yi;
    for (uint8_t id = actor_heads[sub]; id != ACTOR_NONE; id = actors[id].next) {
        const Actor *a = &actors[id];
        if (a->state == ST_GONE) continue;
        const int16_t x = (int16_t)(a->x >> 16), y = (int16_t)(a->y >> 16);
        uint8_t r = 0, flip = 0;
        if (a->state < ST_DEATH && a->dir < 8) {
            r = (uint8_t)((octant(r_view_xi - x, r_view_yi - y) - a->dir) & 7);
            if (r > 4) { r = (uint8_t)(8 - r); flip = 1; }
        }
        uint16_t spr = map_mframes[((uint16_t)a->kind * 16 + a->frame) * 5 + r];
        if (spr == 0xFFFF) spr = map_mframes[((uint16_t)a->kind * 16 + a->frame) * 5];
        if (spr == 0xFFFF) spr = map_mframes[((uint16_t)a->kind * 16) * 5];
        const MapSector *sec = &map_sectors[sector_of_sub(a->sub)];
        R_AddSprite(x, y, sec->floor, spr, flip, sec);
    }
    if (!(fd_sub[sub >> 3] & (1u << (sub & 7)))) return;   /* no barrel, drop or projectile here */
#ifdef DREAD_GAMEPLAY
    for(uint8_t n=0;n<fd_nb;n++){
        const Barrel *b=&barrels[fd_bar[n]];const MapThing *t=&map_things[b->thing];if(t->sub!=sub)continue;
        const MapSector *sec=&map_sectors[map_subs[sub].sector];
        R_AddSprite(t->x,t->y,sec->floor,b->state?map_fx[14+b->frame]:t->sprite,0,sec);
    }
#endif
    for(uint8_t n=0;n<fd_nd;n++){const uint8_t i=fd_drop[n];if(drops[i].sub!=sub)continue;
        R_AddSprite(drops[i].x,drops[i].y,map_sectors[map_subs[sub].sector].floor,map_fx[drops[i].type?12:13],0,&map_sectors[map_subs[sub].sector]);
    }
    for (uint8_t n = 0; n < fd_np; n++) {
        const Proj *p = &proj[fd_proj[n]];
        if (p->sub != sub) continue;
        uint16_t spr;
        if (p->kind==3) spr=map_fx[p->state?9+p->frame:8];
        else if (p->state) spr = map_fx[2 + p->frame];
        else spr = p->kind == 1 ? map_fx[5 + p->frame] : p->kind == 2 ? map_fx[7] : map_fx[p->frame];
        if (spr == 0xFFFF) spr = map_fx[p->frame & 1];
        R_AddSprite((int16_t)(p->x >> 16), (int16_t)(p->y >> 16), p->z, spr, 0, &map_sectors[sector_of_sub(p->sub)]);
    }
}
#endif
