#include "logic_packet.h"

typedef struct { uint16_t to, next, blocks; } Arc;
typedef struct {
    LogicNode nodes[MAX_NODES];
    Arc arcs[MAX_PORTALS * 2];
    uint16_t head[MAX_SECTORS], node_count, sector_count;
} Resident;
#define MAP ((Resident *)0x20000UL)
#define NONE UINT16_MAX
_Static_assert(sizeof(Resident) < 0x50000UL, "map must leave space for sub CPU stack");

static unsigned side(int32_t x, int32_t y, const LogicNode *node)
{
    const int32_t nx = (int32_t)node->x * 65536, ny = (int32_t)node->y * 65536;
    if (!node->dx)
        return x == nx ? 2u : (unsigned)(x <= nx ? node->dy > 0 : node->dy < 0);
    if (!node->dy)
        return y == ny ? 2u : (unsigned)(y <= ny ? node->dx < 0 : node->dx > 0);
    const int32_t right = (int32_t)(y - ny) >> 16;
    const int32_t left = (int32_t)(x - nx) >> 16;
    const int32_t r = right * node->dx, l = left * node->dy;
    return r < l ? 0u : r == l ? 2u : 1u;
}

static int bsp(LogicPacket *p)
{
    uint16_t pending[32], used = 0, leaves = 0;
    uint16_t node = MAP->node_count - 1u;
    unsigned budget = MAX_NODES * 2u + 1u;
    for (;;)
    {
        while (!(node & 0x8000u))
        {
            if (node >= MAP->node_count || !budget--)
                return 1;
            const LogicNode *n = &MAP->nodes[node];
            const unsigned a = side(p->data.sight.x1, p->data.sight.y1, n) & 1u;
            const unsigned b = side(p->data.sight.x2, p->data.sight.y2, n);
            if (a != b)
            {
                if (used == 32)
                    return 1;
                pending[used++] = n->child[a ^ 1u];
            }
            node = n->child[a];
        }
        if (leaves == MAX_LEAVES)
            return 1;
        p->data.sight.leaf[leaves++] = node == NONE ? 0 : node & 0x7fffu;
        if (!used)
            break;
        node = pending[--used];
    }
    p->result = leaves;
    return 0;
}

static int load_portals(const LogicPacket *p)
{
    if (p->origin > MAX_SECTORS || p->count > MAX_PORTALS)
        return 1;
    MAP->sector_count = p->origin;
    for (uint16_t i = 0; i < p->origin; ++i)
        MAP->head[i] = NONE;
    for (uint16_t i = 0; i < p->count; ++i)
    {
        const LogicPortal *edge = &p->data.portals[i];
        const uint16_t a = edge->a, b = edge->b, slot = i * 2u;
        if (a >= p->origin || b >= p->origin)
            return 1;
        MAP->arcs[slot] = (Arc){b, MAP->head[a], edge->blocks};
        MAP->arcs[slot + 1u] = (Arc){a, MAP->head[b], edge->blocks};
        MAP->head[a] = slot;
        MAP->head[b] = slot + 1u;
    }
    return 0;
}

static int flood(LogicPacket *p)
{
    if (p->origin >= p->count || p->count != MAP->sector_count || p->count > MAX_SECTORS)
        return 1;
    uint16_t queue[2 * MAX_SECTORS], read = 0, write = 0;
    uint8_t *seen = p->data.sound.visited;
    const LogicHeight *height = p->data.sound.height;
    for (uint16_t i = 0; i < p->count; ++i)
        seen[i] = 0;
    seen[p->origin] = 1;
    queue[write++] = p->origin;
    while (read < write)
    {
        const uint16_t a = queue[read++];
        for (uint16_t i = MAP->head[a]; i != NONE; i = MAP->arcs[i].next)
        {
            const Arc *arc = &MAP->arcs[i];
            const uint16_t b = arc->to, cost = seen[a] + arc->blocks;
            if (cost > 2 || (seen[b] && seen[b] <= cost))
                continue;
            if (height[a].ceiling <= height[b].floor ||
                height[b].ceiling <= height[a].floor ||
                height[a].ceiling <= height[a].floor ||
                height[b].ceiling <= height[b].floor)
                continue;
            seen[b] = cost;
            queue[write++] = b;
        }
    }
    return 0;
}

static int sort(LogicPacket *p)
{
    if (p->count > MAX_INTERCEPTS)
        return 1;
    uint16_t out = 0;
    p->origin = 0;
    for (uint16_t i = 0; i < p->count; ++i)
    {
        const int32_t frac = p->data.ray.frac[i];
        if (frac > 65536)
        {
            if (frac != INT32_MAX)
                p->origin = 1;
            continue;
        }
        uint16_t j = out++;
        while (j && p->data.ray.frac[p->data.ray.order[j - 1u]] > frac)
        {
            p->data.ray.order[j] = p->data.ray.order[j - 1u];
            --j;
        }
        p->data.ray.order[j] = i;
    }
    p->result = out;
    return 0;
}

uint32_t scd_logic_dispatch(LogicPacket *p, uint32_t sequence)
{
    if (p->sequence != sequence)
        return 1;
    switch (p->command)
    {
    case 0: return 0;
    case LOAD_NODES:
        if (!p->count || p->count > MAX_NODES)
            return 1;
        MAP->node_count = p->count;
        for (uint16_t i = 0; i < p->count; ++i)
            MAP->nodes[i] = p->data.nodes[i];
        return 0;
    case SIGHT_BSP: return bsp(p);
    case LOAD_PORTALS: return load_portals(p);
    case SOUND_FLOOD: return flood(p);
    case SORT_INTERCEPTS: return sort(p);
    default: return 1;
    }
}
