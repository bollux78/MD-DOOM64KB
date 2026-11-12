#include "nexus.h"

enum {
    SCALE = 256, FOCAL_X = NX_WIDTH / 2, FOCAL_Y = NX_HEIGHT * 2 / 3, NEAR = 2 * SCALE, LEAF = 0x8000,
    CEILING_COLOR = 1, FLOOR_COLOR = 2, UPPER_COLOR = 3, LOWER_COLOR = 4
};

typedef struct { int32_t x, z; } ViewPoint;

typedef struct {
    const NxMap *map;
    const NxCamera *camera;
    uint8_t *pixels;
    int layout;
    int material_mode;
    uint8_t top[NX_WIDTH];
    uint8_t bottom[NX_WIDTH];
    int open;
    int first_open, end_open;
    int32_t origin_x, origin_z;
    int16_t left_x, left_y, right_x, right_y;
    int32_t left_bias, right_bias;
} Renderer;

static void span(Renderer *r, int x, int first, int end, unsigned color)
{
    if (first >= end)
        return;
    if (r->layout == NX_LINEAR) {
        uint8_t *dst = r->pixels + nx_linear_index(x, first);
        uint16_t count = end - first;
#ifdef __m68k__
        --count;
        __asm__ volatile ("1: move.b %2,(%0)+\n\tdbra %1,1b"
                          : "+a"(dst), "+d"(count) : "d"(color) : "memory", "cc");
#else
        while (count--)
            *dst++ = color;
#endif
        return;
    }

#if defined(NX_4X1)
    unsigned offset = (x >> 1) * 32 + (x & 1) * 2;
    uint8_t ink = color * 17;
    for (int y = first; y < end; ++y) {
        uint8_t *dst = r->pixels + (y >> 3) * (NX_VIEW_WIDTH * 4)
                       + (y & 7) * 4 + offset;
        dst[0] = ink;
        dst[1] = ink;
    }
#elif defined(NX_2X2)
    unsigned offset = (x >> 2) * 32 + (x & 3);
    uint8_t ink = color * 17;
    while (first < end) {
        uint8_t *dst = r->pixels + (first >> 2) * (NX_VIEW_WIDTH * 4)
                       + (first & 3) * 8 + offset;
        int stop = ((first | 3) + 1);
        if (stop > end)
            stop = end;
        for (int row = 0; row < stop - first; ++row) {
            dst[row * 8] = ink;
            dst[row * 8 + 4] = ink;
        }
        first = stop;
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

#ifdef NX_2X2
#ifndef NX_4X1
static void pack_tile(const uint8_t *src, uint8_t *tile)
{
    for (int row = 0; row < 4; ++row) {
        for (int x = 0; x < 4; ++x) {
            uint8_t ink = src[x * NX_HEIGHT] * 17;
            tile[x] = ink;
            tile[x + 4] = ink;
        }
        tile += 8;
        ++src;
    }
}

#endif
typedef uint32_t AliasWord __attribute__((__may_alias__));

unsigned nx_pack_mixed(const uint8_t *linear, uint8_t *tiles, uint16_t *map,
                       uint16_t mixed_base, uint16_t solid_base)
{
#if defined(NX_4X1)
    unsigned mixed = 0;
    for (unsigned ty = 0; ty < NX_HEIGHT; ty += 8) {
        for (unsigned tx = 0; tx < NX_WIDTH; tx += 2) {
            const uint8_t *src = linear + nx_linear_index(tx, ty);
            unsigned color = src[0];
            uint32_t uniform = color * UINT32_C(0x01010101);
            const AliasWord *col = (const AliasWord *)src;
            if (col[0] == uniform && col[1] == uniform &&
                col[NX_HEIGHT / 4] == uniform && col[NX_HEIGHT / 4 + 1] == uniform) {
                *map++ = solid_base + color;
                continue;
            }
            *map++ = mixed_base + mixed++;
            for (unsigned row = 0; row < 8; ++row) {
                unsigned a = src[row] * 17, b = src[NX_HEIGHT + row] * 17;
                tiles[0] = tiles[1] = a;
                tiles[2] = tiles[3] = b;
                tiles += 4;
            }
        }
    }
    return mixed;
#elif defined(NX_WIDE)
#define INK_ROW(n) {0u, (n), 2u*(n), 3u*(n), 4u*(n), 5u*(n), 6u*(n), 7u*(n), \
                    8u*(n), 9u*(n), 10u*(n), 11u*(n), 12u*(n), 13u*(n), 14u*(n), 15u*(n)}
    static const uint32_t ink[3][3][16] = {
        {INK_ROW(0x11100000u), INK_ROW(0x00011100u), INK_ROW(0x00000011u)},
        {INK_ROW(0x11000000u), INK_ROW(0x00111000u), INK_ROW(0x00000111u)},
        {INK_ROW(0x10000000u), INK_ROW(0x01110000u), INK_ROW(0x00001110u)},
    };
#undef INK_ROW
    static const uint8_t sample[3][8] = {
        {0,0,0,1,1,1,2,2}, {0,0,1,1,1,2,2,2}, {0,1,1,1,2,2,2,3}
    };
    unsigned mixed = 0;
    unsigned y_phase = 0, sy = 0;
    for (unsigned ty = 0; ty < NX_VIEW_HEIGHT; ty += 8) {
        const uint8_t *ys = sample[y_phase];
        unsigned logical_rows = 1 + ys[7];
        unsigned x_phase = 0, sx = 0;
        for (unsigned tx = 0; tx < NX_VIEW_WIDTH; tx += 8) {
            const uint32_t (*phase)[16] = ink[x_phase];
            const uint8_t *src = linear + nx_linear_index(sx, sy);
            uint32_t rows[4];
            for (unsigned y = 0; y < logical_rows; ++y) {
                if (sy + y >= NX_HEIGHT)
                    rows[y] = 0;
                else {
                    uint32_t pattern = phase[0][src[y]] | phase[1][src[NX_HEIGHT + y]]
                                       | phase[2][src[2 * NX_HEIGHT + y]];
                    if (x_phase == 2)
                        pattern |= src[3 * NX_HEIGHT + y];
                    rows[y] = pattern;
                }
            }
            unsigned color = rows[0] & 15;
            uint32_t uniform = color * UINT32_C(0x11111111);
            if (rows[0] == uniform && rows[1] == uniform && rows[2] == uniform &&
                (logical_rows == 3 || rows[3] == uniform)) {
                *map++ = solid_base + color;
            } else {
                *map++ = mixed_base + mixed++;
                for (unsigned y = 0; y < 8; ++y) {
                    uint32_t row = rows[ys[y]];
#ifdef __m68k__
                    *(AliasWord *)tiles = row;
#else
                    tiles[0] = row >> 24;
                    tiles[1] = row >> 16;
                    tiles[2] = row >> 8;
                    tiles[3] = row;
#endif
                    tiles += 4;
                }
            }
            sx += x_phase ? 3 : 2;
            x_phase = x_phase ? x_phase - 1 : 2;
        }
        sy += y_phase ? 3 : 2;
        y_phase = y_phase ? y_phase - 1 : 2;
    }
    return mixed;
#else
    unsigned mixed = 0;
    for (int ty = 0; ty < NX_HEIGHT; ty += 4) {
        for (int tx = 0; tx < NX_WIDTH; tx += 4) {
            const uint8_t *src = linear + nx_linear_index(tx, ty);
            const AliasWord *columns = (const AliasWord *)src;
            uint32_t color = src[0] * UINT32_C(0x01010101);
            if (columns[0] == color && columns[NX_HEIGHT / 4] == color &&
                columns[NX_HEIGHT / 2] == color && columns[NX_HEIGHT * 3 / 4] == color) {
                *map++ = solid_base + src[0];
            } else {
                *map++ = mixed_base + mixed++;
                pack_tile(src, tiles);
                tiles += 32;
            }
        }
    }
    return mixed;
#endif
}
#endif

void nx_pack(const uint8_t *linear, uint8_t *tiles)
{
#if defined(NX_4X1)
    for (unsigned ty = 0; ty < NX_HEIGHT; ty += 8)
        for (unsigned tx = 0; tx < NX_WIDTH; tx += 2) {
            const uint8_t *src = linear + nx_linear_index(tx, ty);
            for (unsigned row = 0; row < 8; ++row) {
                unsigned a = src[row] * 17, b = src[NX_HEIGHT + row] * 17;
                tiles[0] = tiles[1] = a;
                tiles[2] = tiles[3] = b;
                tiles += 4;
            }
        }
#elif defined(NX_2X2)
    for (int ty = 0; ty < NX_HEIGHT; ty += 4) {
        for (int tx = 0; tx < NX_WIDTH; tx += 4) {
            pack_tile(linear + nx_linear_index(tx, ty), tiles);
            tiles += 32;
        }
    }
#else
    for (int ty = 0; ty < NX_HEIGHT; ty += 8) {
        for (int tx = 0; tx < NX_WIDTH; tx += 8) {
            for (int row = 0; row < 8; ++row) {
                const uint8_t *src = linear + nx_linear_index(tx, ty + row);
                for (int x = 0; x < 8; x += 2)
                    *tiles++ = (src[x * NX_HEIGHT] << 4) | src[(x + 1) * NX_HEIGHT];
            }
        }
    }
#endif
}

static ViewPoint view_point(const Renderer *r, NxVertex vertex)
{
    const NxCamera *c = r->camera;
    ViewPoint point = {
        (int32_t)vertex.x * c->sine - (int32_t)vertex.y * c->cosine - r->origin_x,
        (int32_t)vertex.x * c->cosine + (int32_t)vertex.y * c->sine - r->origin_z
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

/* Perspective scale is linear in screen space and shared by all four edges. */
typedef struct {
    int32_t first, step;
#ifdef NX_UV_INCREMENTAL
    int32_t right;
#endif
} Zoom;
typedef struct { uint32_t y, step; } Edge;

static int32_t scaled_divide(int32_t value, int32_t factor, int32_t divisor)
{
    if (value >= INT16_MIN && value <= INT16_MAX && (uint32_t)factor <= 65536)
        return value * factor / divisor;
    return (int64_t)value * factor / divisor;
}

static Zoom project_zoom(ViewPoint a, ViewPoint b, int32_t ax, int32_t bx,
                         int first, int end)
{
    uint32_t numerator = FOCAL_Y * SCALE * 65536u;
    int32_t za = numerator / (uint32_t)a.z;
    int32_t zb = numerator / (uint32_t)b.z;
    int32_t delta = bx - ax;
    int32_t offset = first * SCALE + SCALE / 2 - ax;
    int32_t range = zb - za;
    if (!range)
        return (Zoom){.first = za * SCALE, .step = 0
#ifdef NX_UV_INCREMENTAL
                      , .right = zb * SCALE
#endif
        };

    /* Rebase the weighted average on the nearer horizontal endpoint. */
    if (offset > delta / 2) {
        za = zb;
        offset -= delta;
    }
    /* Keep eight extra fractional bits while advancing the scale. */
    int32_t start = za * SCALE + (int64_t)range * offset * SCALE / delta;
    int32_t step = first + 1 < end ? scaled_divide(range, 65536, delta) : 0;
    return (Zoom){.first = start, .step = step
#ifdef NX_UV_INCREMENTAL
                  , .right = zb * SCALE
#endif
    };
}

#ifdef NX_4X1
enum { EDGE_FRAC = 15 };
#else
enum { EDGE_FRAC = 16 };
#endif

static Edge project_edge(int height, Zoom zoom)
{
    int32_t first = ((int64_t)height * zoom.first) >> (24 - EDGE_FRAC);
    int32_t step = ((int64_t)height * zoom.step + (1 << (23 - EDGE_FRAC))) >> (24 - EDGE_FRAC);
    return (Edge){(NX_HEIGHT / 2u << EDGE_FRAC) - (uint32_t)first, 0u - (uint32_t)step};
}

static void update_open_bounds(Renderer *r)
{
    int left = r->first_open;
    int right = r->end_open;
    while (left < right && r->top[left] == r->bottom[left])
        ++left;
    while (right > left && r->top[right - 1] == r->bottom[right - 1])
        --right;
    r->first_open = left;
    r->end_open = right;

    const NxCamera *c = r->camera;
    int lo = left - NX_WIDTH / 2;
    int hi = right - NX_WIDTH / 2;
    r->left_x = FOCAL_X * c->sine - lo * c->cosine;
    r->left_y = -FOCAL_X * c->cosine - lo * c->sine;
    r->right_x = hi * c->cosine - FOCAL_X * c->sine;
    r->right_y = hi * c->sine + FOCAL_X * c->cosine;
    r->left_bias = (int32_t)c->x * r->left_x + (int32_t)c->y * r->left_y;
    r->right_bias = (int32_t)c->x * r->right_x + (int32_t)c->y * r->right_y;
}

#ifdef NX_WALLS
extern const NxTexture nexus_textures[];
extern const NxMaterial nexus_materials[];

typedef struct { int u, v_step; } TextureColumn;

#ifdef NX_RECIP_LUT
#include "wall_reciprocal.h"

/* zoom is positive Q24. Normalize its mantissa into [2048,4096). */
static int vertical_step(uint32_t zoom)
{
    if (!zoom)
        return 0;
    if (zoom < 2048)
        return UINT32_MAX / zoom;
    unsigned shift = 0;
    uint32_t mantissa = zoom;
    if (mantissa >= (4096u << 8)) {
        mantissa >>= 8;
        shift += 8;
    }
    if (mantissa >= (4096u << 4)) {
        mantissa >>= 4;
        shift += 4;
    }
    while (mantissa >= 4096) {
        mantissa >>= 1;
        ++shift;
    }
    int a = wall_reciprocal[mantissa - 2048];
    int b = wall_reciprocal[mantissa - 2047];
    unsigned fraction = shift >= 8 ? (zoom >> (shift - 8)) & 255u
                                   : (zoom << (8 - shift)) & 255u;
    unsigned estimate = (a * 256 + (b - a) * (int)fraction + 128) >> 8;
    return shift <= 6 ? estimate << (6 - shift) : estimate >> (shift - 6);
}
#else
static int vertical_step(uint32_t zoom)
{
    return zoom ? (int)(UINT32_MAX / zoom) : 0;
}
#endif

#ifdef NX_UV_INCREMENTAL
typedef struct { int32_t first, step; } Weight;

static Weight wall_weight(int32_t ax, int32_t bx, int first, int end, Zoom zoom)
{
    int32_t width = bx - ax;
    int32_t offset = limit(first * SCALE + SCALE / 2 - ax, 0, width);
    int32_t start = (int64_t)offset * zoom.right / width;
    int32_t step = first + 1 < end ? (int64_t)SCALE * zoom.right / width : 0;
    return (Weight){start, step};
}

static TextureColumn sample_incremental(int32_t scale, int32_t weight,
                                         int32_t ua, int32_t ub)
{
    if (scale <= 0)
        return (TextureColumn){ua >> 8, 0};
    int32_t z = scale;
    int32_t weighted = limit(weight, 0, z);
    /* Normalize both terms together before the Q12 division. */
    while ((uint32_t)z > 0x000fffff) {
        weighted >>= 4;
        z >>= 4;
    }
    int32_t t = ((uint32_t)weighted << 12) / (uint32_t)z;
    int u = (ua + ((int64_t)(ub - ua) * t >> 12)) >> 8;
    return (TextureColumn){u, vertical_step(scale)};
}
#else
static TextureColumn sample_wall(int x, int32_t ax, int32_t bx, ViewPoint a,
                                 ViewPoint b, int32_t ua, int32_t ub, int32_t zoom)
{
    int32_t offset = limit(x * SCALE + SCALE / 2 - ax, 0, bx - ax);
    int64_t left = (int64_t)offset * a.z;
    int64_t total = left + (int64_t)(bx - ax - offset) * b.z;
    /* Preserve a 12-bit interpolation factor using 32-bit division. */
    if (total > UINT32_MAX) {
        left >>= 16;
        total >>= 16;
    }
    while (total > 0x000fffff) {
        left >>= 4;
        total >>= 4;
    }
    int32_t t = ((uint32_t)left << 12) / (uint32_t)total;
    int u = (ua + ((int64_t)(ub - ua) * t >> 12)) >> 8;
    return (TextureColumn){u, vertical_step(zoom > 0 ? zoom : 0)};
}
#endif

static void material_span(Renderer *r, int x, int first, int end, unsigned color,
                          const NxTexture *texture, int anchor, TextureColumn column)
{
    if (first >= end)
        return;
    if (!texture->width) {
        span(r, x, first, end, color);
        return;
    }
    int u = column.u % texture->width;
    if (u < 0)
        u += texture->width;
    const uint8_t *src = texture->pixels + u * texture->height;
    int height = texture->height * 256;
    int v = ((anchor - r->camera->z) * 256
             + (first * 2 + 1 - NX_HEIGHT) * column.v_step / 2) % height;
    if (v < 0)
        v += height;
    unsigned step = column.v_step % height;
    uint8_t *dst = r->pixels + nx_linear_index(x, first);
#if defined(NX_COLUMN_ASM) && defined(__m68k__)
    if (height <= 32768) {
        uint16_t rows = end - first - 1;
        uint16_t fraction = v, advance = step, period = height, index;
        __asm__ volatile (
            "1: move.w %[fraction],%[index]\n\t"
            "lsr.w #8,%[index]\n\t"
            "move.b (%[source],%[index].w),(%[dest])+\n\t"
            "add.w %[advance],%[fraction]\n\t"
            "cmp.w %[period],%[fraction]\n\t"
            "bcs.s 2f\n\t"
            "sub.w %[period],%[fraction]\n"
            "2: dbra %[rows],1b"
            : [dest] "+&a"(dst), [fraction] "+&d"(fraction),
              [rows] "+&d"(rows), [index] "=&d"(index)
            : [source] "a"(src), [advance] "d"(advance), [period] "d"(period)
            : "memory", "cc");
        return;
    }
#endif
    for (int y = first; y < end; ++y) {
        *dst++ = src[v >> 8];
        v += step;
        if (v >= height)
            v -= height;
    }
}
#endif

static void draw_seg(Renderer *r, const NxSeg *seg)
{
    const NxVertex *vertices = r->map->vertices;
    ViewPoint a = view_point(r, vertices[seg->a]);
    ViewPoint b = view_point(r, vertices[seg->b]);

    if ((a.z < NEAR && b.z < NEAR) ||
        (a.x <= -a.z && b.x <= -b.z) ||
        (a.x >= a.z && b.x >= b.z))
        return;
#ifdef NX_WALLS
    const NxMaterial *material = 0;
    int32_t ua = 0, ub = 0;
    if (r->material_mode) {
        material = &nexus_materials[seg - r->map->segs];
        ua = material->u;
        ub = ua + material->length;
        if (a.z < NEAR)
            ua += (int64_t)(ub - ua) * (NEAR - a.z) / (b.z - a.z);
        else if (b.z < NEAR)
            ub += (int64_t)(ua - ub) * (NEAR - b.z) / (a.z - b.z);
    }
#endif
    if (a.z < NEAR)
        a = intersect_near(a, b);
    if (b.z < NEAR)
        b = intersect_near(b, a);

    int32_t ax = NX_WIDTH / 2 * SCALE + projected(a.x, a.z, FOCAL_X * SCALE);
    int32_t bx = NX_WIDTH / 2 * SCALE + projected(b.x, b.z, FOCAL_X * SCALE);
    if (bx <= ax)
        return;

    int first = limit(edge(ax), r->first_open, r->end_open);
    int end = limit(edge(bx), r->first_open, r->end_open);
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

    Zoom zoom = project_zoom(a, b, ax, bx, first, end);
    Edge ceiling = project_edge(front.ceiling - r->camera->z, zoom);
    Edge floor = project_edge(front.floor - r->camera->z, zoom);
    Edge upper = ceiling;
    Edge lower = floor;
    if (!solid && high != front.ceiling)
        upper = project_edge(high - r->camera->z, zoom);
    if (!solid && low != front.floor)
        lower = project_edge(low - r->camera->z, zoom);

#ifdef NX_WALLS
    const NxTexture *middle = 0, *high_texture = 0, *low_texture = 0;
    int middle_anchor = 0, high_anchor = 0, low_anchor = 0;
    if (material) {
        unsigned mid = material->middle;
        if (!mid && solid)
            mid = material->upper ? material->upper : material->lower;
        middle = &nexus_textures[mid];
        high_texture = &nexus_textures[material->upper];
        low_texture = &nexus_textures[material->lower];
        middle_anchor = material->offset + ((material->flags & 16)
                       ? front.floor + middle->height : front.ceiling);
        high_anchor = material->offset + ((material->flags & 8)
                     ? front.ceiling : back.ceiling + high_texture->height);
        low_anchor = material->offset + ((material->flags & 16)
                    ? front.ceiling : back.floor);
    }
    TextureColumn column = {0,0}, block_first = {0,0}, block_last = {0,0};
    int block_start = -1, block_end = -1;
#ifdef NX_UV_INCREMENTAL
    Weight weight = {0, 0};
    int weight_ready = 0;
    int32_t column_scale = zoom.first, column_weight = 0;
#define SAMPLE_COLUMN(at) sample_incremental(zoom.first + zoom.step * ((at) - first), \
                                             weight.first + weight.step * ((at) - first), ua, ub)
#else
#define SAMPLE_COLUMN(at) sample_wall((at), ax, bx, a, b, ua, ub, \
                                      zoom.first + (int32_t)((int64_t)zoom.step * ((at) - first)))
#endif
#endif
    int before = r->open;
    for (int x = first; x < end; ++x) {
        int top = r->top[x];
        int bottom = r->bottom[x];
        if (top < bottom) {
            int wall_top = limit(edge((int32_t)ceiling.y >> (EDGE_FRAC - 8)), top, bottom);
            int wall_end = limit(edge((int32_t)floor.y >> (EDGE_FRAC - 8)), wall_top, bottom);
            span(r, x, top, wall_top, CEILING_COLOR);
            span(r, x, wall_end, bottom, FLOOR_COLOR);
#ifdef NX_WALLS
            int opening_top = wall_top;
            int opening_end = wall_end;
            if (!solid) {
                opening_top = limit(edge((int32_t)upper.y >> (EDGE_FRAC - 8)), wall_top, wall_end);
                opening_end = limit(edge((int32_t)lower.y >> (EDGE_FRAC - 8)), opening_top, wall_end);
            }
            if (material && (solid ? middle->width && wall_top < wall_end :
                (high_texture->width && wall_top < opening_top) ||
                (low_texture->width && opening_end < wall_end))) {
#ifdef NX_UV_INCREMENTAL
                if (!weight_ready) {
                    weight = wall_weight(ax, bx, first, end, zoom);
                    column_weight = weight.first + weight.step * (x - first);
                    weight_ready = 1;
                }
#endif
                if (r->material_mode == NX_PERSPECTIVE) {
#ifdef NX_UV_INCREMENTAL
                    column = sample_incremental(column_scale, column_weight, ua, ub);
#else
                    column = SAMPLE_COLUMN(x);
#endif
                } else {
                    int start = first + ((x - first) & ~3);
                    if (start != block_start) {
                        int stop = limit(start + 4, start, end - 1);
                        block_first = start == block_end ? block_last : SAMPLE_COLUMN(start);
                        block_last = stop == start ? block_first : SAMPLE_COLUMN(stop);
                        block_start = start;
                        block_end = stop;
                    }
                    column = block_first;
                    if (x == block_end)
                        column = block_last;
                    else if (x != block_start) {
                        int n = x - block_start;
                        int width = block_end - block_start;
                        int du = (block_last.u - block_first.u) * n;
                        int dv = (block_last.v_step - block_first.v_step) * n;
                        column.u += width == 4 ? du / 4 : du / width;
                        column.v_step += width == 4 ? dv / 4 : dv / width;
                    }
                }
            }
#endif
            if (solid) {
#ifdef NX_WALLS
                if (material)
                    material_span(r, x, wall_top, wall_end, wall_color, middle, middle_anchor, column);
                else
#endif
                    span(r, x, wall_top, wall_end, wall_color);
                r->top[x] = r->bottom[x];
            } else {
#ifndef NX_WALLS
                int opening_top = limit(edge((int32_t)upper.y >> (EDGE_FRAC - 8)), wall_top, wall_end);
                int opening_end = limit(edge((int32_t)lower.y >> (EDGE_FRAC - 8)), opening_top, wall_end);
#endif
#ifdef NX_WALLS
                if (material) {
                    material_span(r, x, wall_top, opening_top, UPPER_COLOR, high_texture, high_anchor, column);
                    material_span(r, x, opening_end, wall_end, LOWER_COLOR, low_texture, low_anchor, column);
                } else
#endif
                {
                    span(r, x, wall_top, opening_top, UPPER_COLOR);
                    span(r, x, opening_end, wall_end, LOWER_COLOR);
                }
                r->top[x] = opening_top;
                r->bottom[x] = opening_end;
            }
            r->open -= r->top[x] == r->bottom[x];
        }
        ceiling.y += ceiling.step;
        floor.y += floor.step;
        upper.y += upper.step;
        lower.y += lower.step;
#if defined(NX_WALLS) && defined(NX_UV_INCREMENTAL)
        column_scale += zoom.step;
        column_weight += weight.step;
#endif
    }
#undef SAMPLE_COLUMN
    if (r->open != before && (first == r->first_open || end == r->end_open))
        update_open_bounds(r);
}

static int camera_side(const NxCamera *camera, const NxNode *node)
{
    return (int32_t)camera->y * node->dx - (int32_t)camera->x * node->dy > node->partition;
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

static inline int32_t box_max(const NxBounds *box, int16_t px, int16_t py)
{
    int16_t x = px >= 0 ? box->right : box->left;
    int16_t y = py >= 0 ? box->top : box->bottom;
    return (int32_t)x * px + (int32_t)y * py;
}

static int intersects_view(const Renderer *r, const NxBounds *box)
{
    const NxCamera *c = r->camera;
    /* A linear plane reaches its maximum at one corner of the box. */
    return box_max(box, c->cosine, c->sine) >= r->origin_z + NEAR
           && box_max(box, r->left_x, r->left_y) >= r->left_bias
           && box_max(box, r->right_x, r->right_y) >= r->right_bias;
}

static void traverse(Renderer *r, uint16_t child)
{
    while (r->open && !(child & LEAF)) {
        const NxNode *node = &r->map->nodes[child];
        int side = camera_side(r->camera, node);
        if (intersects_view(r, &node->bounds[side]))
            traverse(r, node->child[side]);
        if (!r->open || !intersects_view(r, &node->bounds[side ^ 1]))
            return;
        child = node->child[side ^ 1];
    }
    if (!r->open)
        return;

    NxLeaf leaf = r->map->leaves[child & ~LEAF];
    for (int i = 0; i < leaf.count && r->open; ++i)
        draw_seg(r, &r->map->segs[leaf.first + i]);
}

static void render(const NxMap *map, const NxCamera *camera, uint8_t *pixels, int layout, int mode)
{
    Renderer r;
    r.map = map;
    r.camera = camera;
    r.pixels = pixels;
    r.layout = layout;
    r.material_mode = mode;
    r.open = NX_WIDTH;
    r.origin_x = (int32_t)camera->x * camera->sine - (int32_t)camera->y * camera->cosine;
    r.origin_z = (int32_t)camera->x * camera->cosine + (int32_t)camera->y * camera->sine;
    r.first_open = 0;
    r.end_open = NX_WIDTH;
    for (int x = 0; x < NX_WIDTH; ++x) {
        r.top[x] = 0;
        r.bottom[x] = NX_HEIGHT;
    }
    update_open_bounds(&r);
    traverse(&r, map->root);

    /* Color 7 exposes uncovered geometry instead of hiding it in the backdrop. */
    for (int x = 0; x < NX_WIDTH; ++x)
        span(&r, x, r.top[x], r.bottom[x], 7);
}


void nx_render(const NxMap *map, const NxCamera *camera, uint8_t *pixels, int layout)
{
    render(map, camera, pixels, layout, NX_FLAT);
}

void nx_render_walls(const NxMap *map, const NxCamera *camera, uint8_t *pixels, int mode)
{
    render(map, camera, pixels, NX_LINEAR, mode);
}
