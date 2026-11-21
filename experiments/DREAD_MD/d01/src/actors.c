#include "actors.h"
#ifdef DREAD_COMBAT
#include "mapcounts.h"

Actor actors[MAP_NACTORS];
uint16_t actor_heads[MAP_NSUBS];
static uint16_t actor_count, group, elapsed[4];
/* Also read by emulator diagnostics. */
volatile uint16_t combat_wakes, combat_hits, combat_kills, combat_attacks;

static int32_t magnitude(int32_t n) { return n < 0 ? -n : n; }

static const MapSector *sector_at(int16_t x, int16_t y)
{
    return &map_sectors[map_subs[R_PointInSub(x, y)].sector];
}

/* As in the Manifold collision test, walk only grid cells along the ray.
   The converter expands each line's cell coverage, so a 32-unit step
   also covers crossings close to grid boundaries. */
static int visible(int16_t ax, int16_t ay, int16_t bx, int16_t by, int16_t z)
{
    int32_t dx = (int32_t)bx - ax, dy = (int32_t)by - ay;
    int32_t length = magnitude(dx) + magnitude(dy);
    if (length > 1024) return 0;
    uint16_t steps = (uint16_t)(length / 32 + 1), last = ACTOR_NONE;
    for (uint16_t i = 0; i <= steps; i++) {
        int32_t x = ax + dx * i / steps, y = ay + dy * i / steps;
        int32_t gx = (x - map_bm[0]) >> 7, gy = (y - map_bm[1]) >> 7;
        if (gx < 0 || gy < 0 || gx >= map_bm[2] || gy >= map_bm[3]) return 0;
        uint16_t cell = (uint16_t)(gy * map_bm[2] + gx);
        if (cell == last) continue;
        last = cell;
        for (uint16_t k = map_bm_off[cell]; k < map_bm_off[cell + 1]; k++) {
            const MapLine *line = &map_lines[map_bm_list[k]];
            const int16_t *a = map_verts[line->v1], *b = map_verts[line->v2];
            int32_t u = dx * (a[1] - ay) - dy * (a[0] - ax);
            int32_t v = dx * (b[1] - ay) - dy * (b[0] - ax);
            if ((u < 0) == (v < 0)) continue;
            int32_t lx = b[0] - a[0], ly = b[1] - a[1];
            u = lx * (ay - a[1]) - ly * (ax - a[0]);
            v = lx * (by - a[1]) - ly * (bx - a[0]);
            if ((u < 0) == (v < 0)) continue;
            if (line->back == NO_MAP_SECTOR) return 0;
            const MapSector *f = &map_sectors[line->front], *bsec = &map_sectors[line->back];
            if (z <= f->floor || z <= bsec->floor || z >= f->ceil || z >= bsec->ceil) return 0;
        }
    }
    return 1;
}

void Actors_Init(void)
{
    actor_count = group = 0;
    combat_wakes = combat_hits = combat_kills = combat_attacks = 0;
    for (uint16_t i = 0; i < 4; i++) elapsed[i] = 0;
    for (uint16_t i = 0; i < map_counts[2]; i++) actor_heads[i] = ACTOR_NONE;
    for (uint16_t i = 0; i < map_nthings; i++) {
        const MapThing *thing = &map_things[i];
        if (!(thing->flags & 1)) continue;
        const uint16_t id = actor_count++;
        actors[id] = (Actor){*thing, actor_heads[thing->sub], 30, 0, 0};
        actor_heads[thing->sub] = id;
    }
}

static void wake(Actor *actor)
{
    if (!actor->awake) { actor->awake = 1; combat_wakes++; }
}

void Actors_Fire(const View *view)
{
    int16_t x = view->x >> 16, y = view->y >> 16;
    uint16_t angle = view->angle >> 6;
    int32_t c = sintab[(angle + 256) & 1023], s = sintab[angle];
    uint16_t target = ACTOR_NONE;
    int32_t nearest = 641;
    for (uint16_t i = 0; i < actor_count; i++) {
        Actor *a = &actors[i];
        if (!a->hp) continue;
        int32_t dx = a->thing.x - x, dy = a->thing.y - y;
        if (magnitude(dx) + magnitude(dy) > 768) continue;
        int32_t depth = (dx*c + dy*s) >> 14;
        if (depth <= 0 || depth >= nearest || magnitude((dx*s - dy*c) >> 14) > 16) continue;
        if (!visible(x, y, a->thing.x, a->thing.y, view->z)) continue;
        target = i;
        nearest = depth;
    }
    if (target == ACTOR_NONE) return;
    Actor *a = &actors[target];
    wake(a);
    combat_hits++;
    a->hp -= 10;
    if (!a->hp) combat_kills++;
}

void Actors_Tick(const View *view, uint16_t dt, uint16_t *health)
{
    for (uint16_t i = 0; i < 4; i++) elapsed[i] += dt;
    uint16_t step_time = elapsed[group];
    elapsed[group] = 0;
    int16_t x = view->x >> 16, y = view->y >> 16;
    for (uint16_t i = group; i < actor_count; i += 4) {
        Actor *a = &actors[i];
        if (!a->hp) continue;
        int32_t dx = x - a->thing.x, dy = y - a->thing.y;
        int32_t distance = magnitude(dx) + magnitude(dy);
        if (distance > 512) continue;
        if (!a->awake) {
            if (!visible(a->thing.x, a->thing.y, x, y, view->z)) continue;
            wake(a);
        }
        a->cooldown = a->cooldown > step_time ? a->cooldown - step_time : 0;
        if (distance < 176 && !a->cooldown && visible(a->thing.x, a->thing.y, x, y, view->z)) {
            a->cooldown = 60;
            combat_attacks++;
            *health = *health > 5 ? *health - 5 : 0;
        }
        if (distance <= 32) continue;
        int32_t step = step_time > 16 ? 16 : step_time;
        int16_t nx = a->thing.x + dx * step / distance;
        int16_t ny = a->thing.y + dy * step / distance;
        const MapSector *from = &map_sectors[map_subs[a->thing.sub].sector];
        const MapSector *to = sector_at(nx, ny);
        if (to->floor - from->floor > 24 || to->ceil - to->floor < 56 || ActorBlocked(nx, ny)) continue;
        a->thing.x = nx;
        a->thing.y = ny;
        uint16_t sub = (uint16_t)R_PointInSub(nx, ny);
        if (sub != a->thing.sub) {
            uint16_t *link = &actor_heads[a->thing.sub];
            while (*link != i) link = &actors[*link].next;
            *link = a->next;
            a->next = actor_heads[sub];
            actor_heads[sub] = i;
            a->thing.sub = sub;
        }
    }
    group = (group + 1) & 3;
}
#endif
