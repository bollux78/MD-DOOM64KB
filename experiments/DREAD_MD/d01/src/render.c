/* DREAD-MD D01 renderer.
 *
 * Dread-style column renderer for one Doom map:
 *  - walls front to back (Doom BSP order), each screen pixel written exactly once;
 *  - floor and ceiling are one flat colour per sector, painted in the same column pass
 *    (no visplanes, no spans), so the cost is roughly columns x rows and barely
 *    depends on the scene;
 *  - textures are pre-lit per sector light bucket and pre-doubled (one byte = 2 pixels).
 * Portable C: the same file builds for the Mega Drive and for the host test harness. */
#include "render.h"

#define NEAR4 16                   /* near plane, map units * 4 (= 4 units) */
#ifndef MAXV
#define MAXV  1024
#endif

MapSector map_sectors[256];
RenderStats rstats;

static int32_t vtz[MAXV], vtx[MAXV];
static uint16_t vstamp[MAXV];
static uint16_t frame_id;

static uint8_t ceilclip[VIEW_W], floorclip[VIEW_W];
static int16_t closed;

static int32_t view_x4, view_y4;   /* map units * 4 */
static int16_t view_z;
static int32_t vsin, vcos;         /* Q14 */
static uint8_t *rfb;

void R_Init(void)
{
    for (int i = 0; i < map_counts[4]; i++) map_sectors[i] = map_sectors_init[i];
    for (int i = 0; i < MAXV; i++) vstamp[i] = 0xFFFF;
}

static void xform(uint16_t v)
{
    if (vstamp[v] == frame_id) return;
    vstamp[v] = frame_id;
    const int32_t dx = ((int32_t)map_verts[v][0] << 2) - view_x4;
    const int32_t dy = ((int32_t)map_verts[v][1] << 2) - view_y4;
    vtz[v] = (dx * vcos + dy * vsin) >> 14;
    vtx[v] = (dx * vsin - dy * vcos) >> 14;
}

/* screen x in 16.16 for a camera-space point (x4, z4), z4 >= NEAR4 */
static int32_t proj(int32_t x4, int32_t z4)
{
    int32_t q = (x4 * FOCAL << 8) / z4;
    if (q > (1 << 22)) q = 1 << 22;
    if (q < -(1 << 22)) q = -(1 << 22);
    return ((int32_t)HALF_W << 16) + (q << 8);
}

static inline void fill_col(uint8_t *col, int y0, int y1, uint8_t c)
{
    uint8_t *p = col + (y0 << 2);
    for (int n = y1 - y0; n > 0; n--) { *p = c; p += 4; }
}

static inline void tex_col(uint8_t *col, int y0, int y1, const uint8_t *tc, int32_t v, int32_t vstep, uint16_t hmask)
{
    uint8_t *p = col + (y0 << 2);
    for (int n = y1 - y0; n > 0; n--) { *p = tc[(uint16_t)(v >> 16) & hmask]; p += 4; v += vstep; }
}

/* height h (map units) -> screen row in 16.16 for inverse depth iz (= 2^24 / z4) */
static int32_t yrow(int32_t dh, int32_t iz)
{
    int64_t r = ((int64_t)HORIZON << 16) - (((int64_t)dh * VFOCAL * iz) >> 6);
    if (r > ((int64_t)8000 << 16)) r = (int64_t)8000 << 16;
    if (r < -((int64_t)8000 << 16)) r = -((int64_t)8000 << 16);
    return (int32_t)r;
}

static inline int ceil16(int32_t y) { return (y + 0xFFFF) >> 16; }
static inline int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }

typedef struct {
    const uint8_t *tex; uint16_t wmask, hmask; uint8_t hshift;
    int32_t vbase16;              /* (textop - viewz + yoff) << 16 */
} Part;

static void setup_part(Part *p, uint8_t t, uint8_t bucket, int16_t textop, int16_t yoff)
{
    const MapTex *m = &map_tex[t];
    p->tex = tex_blob + m->off[bucket];
    p->wmask = (1u << m->wshift) - 1;
    p->hshift = m->hshift;
    p->hmask = (1u << m->hshift) - 1;
    p->vbase16 = ((int32_t)(textop - view_z + yoff)) << 16;
}

static void draw_seg(const MapSeg *s)
{
    xform(s->v1); xform(s->v2);
    int32_t x1 = vtx[s->v1], z1 = vtz[s->v1], x2 = vtx[s->v2], z2 = vtz[s->v2];
    if (z1 < NEAR4 && z2 < NEAR4) return;
    int32_t t1 = 0, t2 = 65536;            /* Q16 position along the seg */
    const int32_t ox1 = x1, oz1 = z1, ox2 = x2, oz2 = z2;
    if (oz1 < NEAR4) {
        t1 = (int32_t)(((int64_t)(NEAR4 - oz1) << 16) / (oz2 - oz1));
        x1 = ox1 + (int32_t)(((int64_t)(ox2 - ox1) * t1) >> 16); z1 = NEAR4;
    }
    if (oz2 < NEAR4) {
        t2 = (int32_t)(((int64_t)(NEAR4 - oz1) << 16) / (oz2 - oz1));
        x2 = ox1 + (int32_t)(((int64_t)(ox2 - ox1) * t2) >> 16); z2 = NEAR4;
    }
    const int32_t sx1 = proj(x1, z1), sx2 = proj(x2, z2);
    if (sx1 >= sx2) return;                /* back face */
    int xs = ceil16(sx1), xe = ceil16(sx2);
    if (xs < 0) xs = 0;
    if (xe > VIEW_W) xe = VIEW_W;
    if (xs >= xe) return;
    rstats.segs_drawn++;

    const MapSector *fs = &map_sectors[s->front];
    const MapSector *bs = (s->back != 0xFF) ? &map_sectors[s->back] : 0;
    const uint8_t bucket = fs->bucket;

    /* inverse depth and u/z at both ends; u in half texels (textures are stored half width) */
    const int32_t iz1 = (1L << 24) / z1, iz2 = (1L << 24) / z2;
    const int32_t u1 = (s->xoff + (int32_t)(((int64_t)s->len * t1) >> 16)) >> 1;
    const int32_t u2 = (s->xoff + (int32_t)(((int64_t)s->len * t2) >> 16)) >> 1;
    const int32_t ub = u1 & ~1023;         /* keep u small; textures are <= 1024 half texels */
    const int32_t uz1 = (u1 - ub) * iz1, uz2 = (u2 - ub) * iz2;

    const int32_t span8 = (sx2 - sx1) >> 8; /* columns * 256 */
    if (span8 <= 0) return;
    const int32_t frac8 = (((int32_t)xs << 16) - sx1) >> 8;   /* 0..255 + whole columns */
#define STEP(a, b) (((b) - (a)) / span8 * 256 + ((((b) - (a)) % span8) * 256) / span8)
    const int32_t diz = STEP(iz1, iz2);
    int32_t iz = iz1 + (int32_t)(((int64_t)diz * frac8) >> 8);
    const int32_t duz = STEP(uz1, uz2);
    int32_t uz = uz1 + (int32_t)(((int64_t)duz * frac8) >> 8);

    const int16_t fc = fs->ceil - view_z, ff = fs->floor - view_z;
    int32_t Yc1 = yrow(fc, iz1), Yc2 = yrow(fc, iz2);
    int32_t Yf1 = yrow(ff, iz1), Yf2 = yrow(ff, iz2);
    const int32_t dYc = STEP(Yc1, Yc2), dYf = STEP(Yf1, Yf2);
    int32_t Yc = Yc1 + (int32_t)(((int64_t)dYc * frac8) >> 8);
    int32_t Yf = Yf1 + (int32_t)(((int64_t)dYf * frac8) >> 8);

    Part mid, up, lo;
    int has_mid = 0, has_up = 0, has_lo = 0;
    int32_t Ybc = 0, Ybf = 0, dYbc = 0, dYbf = 0;
    if (!bs) {
        if (s->mid != 0xFF) {
            has_mid = 1;
            const int16_t textop = (s->flags & 2) ? fs->floor + map_tex[s->mid].realh : fs->ceil;
            setup_part(&mid, s->mid, bucket, textop, s->yoff);
        }
    } else {
        if (bs->ceil < fs->ceil && !(fs->sky && bs->sky) && s->upper != 0xFF) {
            has_up = 1;
            const int16_t textop = (s->flags & 1) ? fs->ceil : bs->ceil + map_tex[s->upper].realh;
            setup_part(&up, s->upper, bucket, textop, s->yoff);
            const int16_t bc = bs->ceil - view_z;
            const int32_t a = yrow(bc, iz1), b = yrow(bc, iz2);
            dYbc = STEP(a, b); Ybc = a + (int32_t)(((int64_t)dYbc * frac8) >> 8);
        }
        if (bs->floor > fs->floor && s->lower != 0xFF) {
            has_lo = 1;
            const int16_t textop = (s->flags & 2) ? fs->ceil : bs->floor;
            setup_part(&lo, s->lower, bucket, textop, s->yoff);
            const int16_t bf = bs->floor - view_z;
            const int32_t a = yrow(bf, iz1), b = yrow(bf, iz2);
            dYbf = STEP(a, b); Ybf = a + (int32_t)(((int64_t)dYbf * frac8) >> 8);
        }
    }
    const uint8_t ccol = fs->ceilcol * 0x11, fcol = fs->floorcol * 0x11;
    const int need_tex = has_mid | has_up | has_lo;

    for (int c = xs; c < xe; c++,
         iz += diz, uz += duz, Yc += dYc, Yf += dYf, Ybc += dYbc, Ybf += dYbf) {
        int top = ceilclip[c], bot = floorclip[c];
        if (top >= bot) continue;
        uint8_t *col = FB_COL(rfb, c);
        const int yc = clampi(ceil16(Yc), top, bot);
        const int yf = clampi(ceil16(Yf), yc, bot);
        if (yc > top) fill_col(col, top, yc, ccol);
        if (bot > yf) fill_col(col, yf, bot, fcol);

        int32_t zpp = 0; uint16_t u = 0;
        if (need_tex && iz > 0) {
            const int32_t q = (1L << 30) / iz;            /* z * 256 */
            zpp = (q << 8) / VFOCAL;                       /* texels per row, 16.16 */
            u = (uint16_t)(uz / iz);
        }
        if (!bs) {
            if (has_mid && yf > yc) {
                const uint8_t *tc = mid.tex + ((u & mid.wmask) << mid.hshift);
                tex_col(col, yc, yf, tc, mid.vbase16 - (HORIZON - yc) * zpp, zpp, mid.hmask);
            }
            ceilclip[c] = floorclip[c] = 0;
            closed++;
            continue;
        }
        int ntop = yc, nbot = yf;
        if (has_up) {
            const int ybc = clampi(ceil16(Ybc), yc, yf);
            if (ybc > yc) {
                const uint8_t *tc = up.tex + ((u & up.wmask) << up.hshift);
                tex_col(col, yc, ybc, tc, up.vbase16 - (HORIZON - yc) * zpp, zpp, up.hmask);
            }
            ntop = ybc;
        }
        if (has_lo) {
            const int ybf = clampi(ceil16(Ybf), ntop, yf);
            if (yf > ybf) {
                const uint8_t *tc = lo.tex + ((u & lo.wmask) << lo.hshift);
                tex_col(col, ybf, yf, tc, lo.vbase16 - (HORIZON - ybf) * zpp, zpp, lo.hmask);
            }
            nbot = ybf;
        }
        if (ntop >= nbot) { ceilclip[c] = floorclip[c] = 0; closed++; }
        else { ceilclip[c] = ntop; floorclip[c] = nbot; }
    }
}

static int bbox_visible(const int16_t *bb)
{
    /* bb = top, bottom, left, right */
    const int32_t vx = view_x4 >> 2, vy = view_y4 >> 2;
    if (vx >= bb[2] && vx <= bb[3] && vy >= bb[1] && vy <= bb[0]) return 1;
    int32_t minx = 0x7FFFFFFF, maxx = -0x7FFFFFFF;
    int behind = 0;
    for (int k = 0; k < 4; k++) {
        const int32_t px = (k & 1) ? bb[3] : bb[2], py = (k & 2) ? bb[0] : bb[1];
        const int32_t dx = (px << 2) - view_x4, dy = (py << 2) - view_y4;
        const int32_t z = (dx * vcos + dy * vsin) >> 14;
        const int32_t x = (dx * vsin - dy * vcos) >> 14;
        if (z < NEAR4) { behind++; continue; }
        const int32_t sx = proj(x, z);
        if (sx < minx) minx = sx;
        if (sx > maxx) maxx = sx;
    }
    if (behind == 4) return 0;
    if (behind) return 1;                  /* straddles the near plane: assume visible */
    int a = ceil16(minx), b = ceil16(maxx);
    if (a < 0) a = 0;
    if (b > VIEW_W) b = VIEW_W;
    for (int c = a; c < b; c++)
        if (ceilclip[c] < floorclip[c]) return 1;
    return 0;
}

static void render_node(uint16_t n)
{
    if (closed >= VIEW_W) return;
    if (n & 0x8000) {
        const MapSub *ss = &map_subs[n & 0x7FFF];
        rstats.subs_visited++;
        for (uint16_t i = 0; i < ss->count; i++) draw_seg(&map_segs[ss->first + i]);
        return;
    }
    const MapNode *nd = &map_nodes[n];
    rstats.nodes_visited++;
    const int32_t dx = (view_x4 >> 2) - nd->x, dy = (view_y4 >> 2) - nd->y;
    const int side = ((int32_t)nd->dy * dx > (int32_t)nd->dx * dy) ? 0 : 1;
    render_node(nd->child[side]);
    if (bbox_visible(nd->bbox[side ^ 1])) render_node(nd->child[side ^ 1]);
}

int R_PointInSub(int16_t x, int16_t y)
{
    uint16_t n = map_counts[3] - 1;
    while (!(n & 0x8000)) {
        const MapNode *nd = &map_nodes[n];
        const int32_t dx = x - nd->x, dy = y - nd->y;
        n = nd->child[((int32_t)nd->dy * dx > (int32_t)nd->dx * dy) ? 0 : 1];
    }
    return n & 0x7FFF;
}

void R_RenderView(const View *v, uint8_t *fb)
{
    rfb = fb;
    frame_id++;
    if (frame_id == 0xFFFF) { frame_id = 0; for (int i = 0; i < MAXV; i++) vstamp[i] = 0xFFFF; }
    view_x4 = v->x >> 14; view_y4 = v->y >> 14; view_z = v->z;
    const uint16_t a = v->angle >> 6;
    vsin = sintab[a]; vcos = sintab[(a + 256) & 1023];
    for (int c = 0; c < VIEW_W; c++) { ceilclip[c] = 0; floorclip[c] = VIEW_H; }
    closed = 0;
    rstats.segs_drawn = rstats.nodes_visited = rstats.subs_visited = 0;
    render_node(map_counts[3] - 1);
    rstats.cols_closed = closed;
}
