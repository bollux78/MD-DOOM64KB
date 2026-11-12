#include "nexus.h"

enum {
    SCALE = 256, FOCAL = NX_WIDTH / 2, NEAR = 2 * SCALE, LEAF = 0x8000,
    CEILING_COLOR = 1, FLOOR_COLOR = 2, UPPER_COLOR = 3, LOWER_COLOR = 4
};

typedef struct { int32_t x, z; } ViewPoint;

typedef struct {
    const NxMap *map;
    const NxCamera *camera;
    uint8_t *pixels;
    int layout;
    uint8_t top[NX_WIDTH];
    uint8_t bottom[NX_WIDTH];
    int open;
    int16_t plane_x[3], plane_y[3];
} Renderer;

static void span(Renderer *r, int x, int first, int end, unsigned color)
{
    if (first >= end)
        return;
    if (r->layout == NX_LINEAR) {
        for (int y = first; y < end; ++y)
            r->pixels[y * NX_WIDTH + x] = color;
        return;
    }

#ifdef NX_2X2
    unsigned offset = (x >> 2) * 32 + (x & 3);
    uint8_t ink = color * 17;
    for (int y = first; y < end; ++y) {
        uint8_t *dst = r->pixels + (y >> 2) * (NX_VIEW_WIDTH * 4)
                       + (y & 3) * 8 + offset;
        dst[0] = ink;
        dst[4] = ink;
    }
#else
    unsigned shift = (x & 1) ? 0 : 4;
    unsigned mask = 15u << shift;
    unsigned ink = color << shift;
    unsigned offset = (x >> 3) * 32 + ((x & 7) >> 1);
    while (first < end) {
        uint8_t *byte = r->pixels + (first >> 3) * (NX_WIDTH * 4)
                        + (first & 7) * 4 + offset;
        int stop = (first | 7) + 1;
        if (stop > end)
            stop = end;
        for (int row = 0; row < stop - first; ++row)
            byte[row * 4] = (byte[row * 4] & ~mask) | ink;
        first = stop;
    }
#endif
}

void nx_pack(const uint8_t *linear, uint8_t *tiles)
{
#ifdef NX_2X2
    for (int ty = 0; ty < NX_HEIGHT; ty += 4) {
        for (int tx = 0; tx < NX_WIDTH; tx += 4) {
            for (int row = 0; row < 4; ++row) {
                const uint8_t *src = linear + (ty + row) * NX_WIDTH + tx;
                for (int x = 0; x < 4; ++x) {
                    uint8_t ink = src[x] * 17;
                    tiles[x] = ink;
                    tiles[x + 4] = ink;
                }
                tiles += 8;
            }
        }
    }
#else
    for (int ty = 0; ty < NX_HEIGHT; ty += 8) {
        for (int tx = 0; tx < NX_WIDTH; tx += 8) {
            for (int row = 0; row < 8; ++row) {
                const uint8_t *src = linear + (ty + row) * NX_WIDTH + tx;
                for (int x = 0; x < 8; x += 2)
                    *tiles++ = (src[x] << 4) | src[x + 1];
            }
        }
    }
#endif
}

static ViewPoint view_point(const NxCamera *camera, NxVertex vertex)
{
    int32_t dx = (int32_t)vertex.x - camera->x;
    int32_t dy = (int32_t)vertex.y - camera->y;
    ViewPoint point = {
        dx * camera->sine - dy * camera->cosine,
        dx * camera->cosine + dy * camera->sine
    };
    return point;
}

static ViewPoint intersect_near(ViewPoint a, ViewPoint b)
{
    int32_t x = a.x + (int64_t)(b.x - a.x) * (NEAR - a.z) / (b.z - a.z);
    return (ViewPoint){x, NEAR};
}

static int limit(int value, int low, int high)
{
    if (value < low)
        return low;
    return value > high ? high : value;
}

/* Use the 32-bit division path when the scaled numerator fits exactly. */
static inline int32_t projected(int32_t value, int32_t depth, int factor)
{
    if (value >= INT32_MIN / factor && value <= INT32_MAX / factor)
        return value * factor / depth;
    return (int64_t)value * factor / depth;
}

/* First pixel whose center falls on or past the projected edge. */
static int edge(int32_t position)
{
    return (position + SCALE / 2 - 1) >> 8;
}

/* Height at pixel centers, stepped in screen space at Q16 precision. */
typedef struct { int64_t y, step; } Edge;

static Edge project_edge(int height, ViewPoint a, ViewPoint b,
                         int32_t ax, int32_t bx, int first)
{
    int32_t ay = projected(height, a.z, FOCAL * SCALE * SCALE);
    int32_t by = projected(height, b.z, FOCAL * SCALE * SCALE);
    int32_t delta = bx - ax;
    int32_t offset = first * SCALE + SCALE / 2 - ax;
    if (ay == by)
        return (Edge){(int64_t)NX_HEIGHT / 2 * 65536 - (int64_t)ay * SCALE, 0};

    int64_t range = (int64_t)(ay - by);
    int64_t y = (int64_t)NX_HEIGHT / 2 * 65536 - (int64_t)ay * SCALE
              + range * offset * SCALE / delta;
    int64_t step = range * 65536 / delta;

    /* Extreme projected edges may be off-screen by thousands of pixels.
       Keep interpolation wide until converting a sampled edge to a row. */
    return (Edge){y, step};
}

static void draw_seg(Renderer *r, const NxSeg *seg)
{
    const NxVertex *vertices = r->map->vertices;
    ViewPoint a = view_point(r->camera, vertices[seg->a]);
    ViewPoint b = view_point(r->camera, vertices[seg->b]);

    if ((a.z < NEAR && b.z < NEAR) ||
        (a.x <= -a.z && b.x <= -b.z) ||
        (a.x >= a.z && b.x >= b.z))
        return;
    if (a.z < NEAR)
        a = intersect_near(a, b);
    if (b.z < NEAR)
        b = intersect_near(b, a);

    int32_t ax = NX_WIDTH / 2 * SCALE + projected(a.x, a.z, FOCAL * SCALE);
    int32_t bx = NX_WIDTH / 2 * SCALE + projected(b.x, b.z, FOCAL * SCALE);
    if (bx <= ax)
        return;

    int first = limit(edge(ax), 0, NX_WIDTH);
    int end = limit(edge(bx), 0, NX_WIDTH);
    int visible = first;
    while (visible < end && r->top[visible] == r->bottom[visible])
        ++visible;
    if (visible == end)
        return;
    first = visible;

    NxSector front = r->map->sectors[seg->front];
    NxSector back = front;
    if (seg->back != 0xFFFF)
        back = r->map->sectors[seg->back];
    int low = front.floor > back.floor ? front.floor : back.floor;
    int high = front.ceiling < back.ceiling ? front.ceiling : back.ceiling;
    int solid = seg->back == 0xFFFF || low >= high;
    int wall_color = 5 + (vertices[seg->a].x == vertices[seg->b].x);

    Edge ceiling = project_edge(front.ceiling - r->camera->z, a, b, ax, bx, first);
    Edge floor = project_edge(front.floor - r->camera->z, a, b, ax, bx, first);
    Edge upper = ceiling;
    Edge lower = floor;
    if (!solid && high != front.ceiling)
        upper = project_edge(high - r->camera->z, a, b, ax, bx, first);
    if (!solid && low != front.floor)
        lower = project_edge(low - r->camera->z, a, b, ax, bx, first);

    for (int x = first; x < end; ++x) {
        int top = r->top[x];
        int bottom = r->bottom[x];
        if (top < bottom) {
            int wall_top = limit(edge(ceiling.y >> 8), top, bottom);
            int wall_end = limit(edge(floor.y >> 8), wall_top, bottom);
            span(r, x, top, wall_top, CEILING_COLOR);
            span(r, x, wall_end, bottom, FLOOR_COLOR);
            if (solid) {
                span(r, x, wall_top, wall_end, wall_color);
                r->top[x] = r->bottom[x];
            } else {
                int opening_top = limit(edge(upper.y >> 8), wall_top, wall_end);
                int opening_end = limit(edge(lower.y >> 8), opening_top, wall_end);
                span(r, x, wall_top, opening_top, UPPER_COLOR);
                span(r, x, opening_end, wall_end, LOWER_COLOR);
                r->top[x] = opening_top;
                r->bottom[x] = opening_end;
            }
            r->open -= r->top[x] == r->bottom[x];
        }
        ceiling.y += ceiling.step;
        floor.y += floor.step;
        upper.y += upper.step;
        lower.y += lower.step;
    }
}

static int camera_side(const NxCamera *camera, const NxNode *node)
{
    int32_t dx = (int32_t)camera->x - node->x;
    int32_t dy = (int32_t)camera->y - node->y;
    return dy * node->dx > dx * node->dy;
}

void nx_camera_floor(const NxMap *map, NxCamera *camera)
{
    uint16_t child = map->root;
    while (!(child & LEAF)) {
        const NxNode *node = &map->nodes[child];
        child = node->child[camera_side(camera, node)];
    }
    NxSector sector = map->sectors[map->segs[map->leaves[child & ~LEAF].first].front];
    int eye = (int)sector.floor + 41;
    camera->z = limit(eye, INT16_MIN, (int)sector.ceiling - 1);
}

static int intersects_view(const Renderer *r, NxBounds box)
{
    /* A linear plane reaches its maximum at one corner of the box. */
    for (int i = 0; i < 3; ++i) {
        int16_t px = r->plane_x[i], py = r->plane_y[i];
        int32_t x = (int32_t)(px >= 0 ? box.right : box.left) - r->camera->x;
        int32_t y = (int32_t)(py >= 0 ? box.top : box.bottom) - r->camera->y;
        if (x * px + y * py < (i == 0 ? NEAR : 0))
            return 0;
    }
    return 1;
}

static void traverse(Renderer *r, uint16_t child)
{
    while (r->open && !(child & LEAF)) {
        const NxNode *node = &r->map->nodes[child];
        int side = camera_side(r->camera, node);
        traverse(r, node->child[side]);
        if (!r->open || !intersects_view(r, node->bounds[side ^ 1]))
            return;
        child = node->child[side ^ 1];
    }
    if (!r->open)
        return;

    NxLeaf leaf = r->map->leaves[child & ~LEAF];
    for (int i = 0; i < leaf.count && r->open; ++i)
        draw_seg(r, &r->map->segs[leaf.first + i]);
}

void nx_render(const NxMap *map, const NxCamera *camera, uint8_t *pixels, int layout)
{
    Renderer r;
    r.map = map;
    r.camera = camera;
    r.pixels = pixels;
    r.layout = layout;
    r.open = NX_WIDTH;
    r.plane_x[0] = camera->cosine;
    r.plane_y[0] = camera->sine;
    r.plane_x[1] = camera->cosine + camera->sine;
    r.plane_y[1] = camera->sine - camera->cosine;
    r.plane_x[2] = camera->cosine - camera->sine;
    r.plane_y[2] = camera->sine + camera->cosine;
    for (int x = 0; x < NX_WIDTH; ++x) {
        r.top[x] = 0;
        r.bottom[x] = NX_HEIGHT;
    }
    traverse(&r, map->root);

    /* Color 7 exposes uncovered geometry instead of hiding it in the backdrop. */
    for (int x = 0; x < NX_WIDTH; ++x)
        span(&r, x, r.top[x], r.bottom[x], 7);
}
