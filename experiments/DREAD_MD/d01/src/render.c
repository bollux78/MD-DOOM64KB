/* DREAD-MD D01 renderer.
 *
 * Dread-style column renderer for one Doom map:
 *  - walls front to back (Doom BSP order), each screen pixel written exactly once;
 *  - floor and ceiling are one flat colour per sector, painted in the same column pass
 *    (no visplanes, no spans), so the cost is roughly columns x rows and barely
 *    depends on the scene;
 *  - textures are pre-lit per sector light bucket, one byte per texel = a pair of
 *    4bpp pixels (two palette colours side by side: colour mixing like Dread MD);
 *  - perspective-correct u and the vertical texture step are computed every 8 columns
 *    (16-bit divu) and interpolated in between; the 68000 has no 32-bit mul/div,
 *    so the hot path only uses 16x16 multiplies and 32/16 divides.
 * Portable C: the same file builds for the Mega Drive and for the host test harness. */
#include "render.h"

#define NEAR4 16                   /* near plane, map units * 4 (= 4 units) */
#define ANCHOR 8                   /* columns between perspective-correct samples */
#ifndef MAXV
#define MAXV  1024
#endif

MapSector map_sectors[256];
RenderStats rstats;
#ifdef PVS_GEN
uint8_t pvs_seen[4096];                 /* generator: subsectors that drew something */
static uint16_t cur_sub;
#else
extern const uint8_t pvs_nodes[], pvs_subs[];   /* pvs.c (generated): bitsets per subsector */
extern const uint16_t pvs_nbytes, pvs_sbytes;
static const uint8_t *pv_n, *pv_s;
int r_pvs_off;   /* host checks only */
static const uint8_t pv_all[1024] = {[0 ... 1023] = 0xFF};
#endif
volatile uint16_t dbg_flags;
uint32_t tm_setup, tm_loop, tm_total, tm_anchor, tm_fill, tm_tex;   /* test only: scanline-resolution timers */
#if defined(__m68k__) || defined(__mc68000__)
extern volatile uint16_t vints;
static inline uint32_t now_lines(void) { for (;;) { const uint16_t a = vints; const uint8_t v = *(volatile uint8_t *)0xC00008; if (a == vints) return (uint32_t)a * 262 + v; } }
#else
static inline uint32_t now_lines(void) { return 0; }
#endif   /* test only: 1 = skip textured spans, 2 = skip fills, 4 = skip column work entirely */

static int16_t vtz[MAXV], vtx[MAXV];   /* camera space, map units * 4 (clamped) */
static uint16_t vstamp[MAXV];
static uint16_t frame_id;
static uint16_t RCP4[1024];        /* 2^20 / z, z = 16..1023 */

static uint8_t clipbuf[2 * VIEW_W];          /* [0..W) ceiling clip (top), [W..2W) floor clip (bottom) */
#define ceilclip clipbuf
#define floorclip (clipbuf + VIEW_W)
/* next open column at or after c (union-find with path halving); closed columns are skipped
 * in O(1) instead of being walked by every seg behind them */
static uint8_t nxt[VIEW_W + 1];
static inline int find_open(int c)
{
    while (nxt[c] != c) { nxt[c] = nxt[nxt[c]]; c = nxt[c]; }
    return c;
}
static inline void close_col(int c) { ceilclip[c] = floorclip[c] = 0; nxt[c] = (uint8_t)(c + 1); }
static int16_t closed;

static int16_t view_xi, view_yi;   /* integer map position */
static int32_t frac_tz, frac_tx;   /* camera-space offset of the fractional position, * 4 */
static int32_t view_x4, view_y4;
static int16_t view_z;
static int16_t vsin, vcos;         /* Q14 */
static uint8_t *rfb;

/* ---------------------------------------------------------------- 68000 arithmetic */
#if defined(__m68k__) || defined(__mc68000__)
static inline uint16_t divu16(uint32_t n, uint16_t d)
{ __asm__("divu.w %1,%0" : "+d"(n) : "dm"(d) : "cc"); return (uint16_t)n; }
static inline int16_t divs16(int32_t n, int16_t d)
{ __asm__("divs.w %1,%0" : "+d"(n) : "dm"(d) : "cc"); return (int16_t)n; }
static inline int32_t muls16(int16_t a, int16_t b)
{ int32_t r = a; __asm__("muls.w %1,%0" : "+d"(r) : "dm"(b) : "cc"); return r; }
static inline uint32_t mulu16(uint16_t a, uint16_t b)
{ uint32_t r = a; __asm__("mulu.w %1,%0" : "+d"(r) : "dm"(b) : "cc"); return r; }
extern void col_fill(uint8_t *p, uint16_t n, uint16_t c);
extern void col_tex(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t vbot, int32_t negstep, uint16_t hmask);
extern void col_tex_nm(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t vbot, int32_t negstep);
#else
static inline uint16_t divu16(uint32_t n, uint16_t d) { return (uint16_t)(n / d); }
static inline int16_t divs16(int32_t n, int16_t d) { return (int16_t)(n / d); }
static inline int32_t muls16(int16_t a, int16_t b) { return (int32_t)a * b; }
static inline uint32_t mulu16(uint16_t a, uint16_t b) { return (uint32_t)a * b; }
static void col_fill(uint8_t *p, uint16_t n, uint16_t c)
{ for (; n; n--) { *p = (uint8_t)c; p += 4; } }
/* draws bottom-up like the 68000 version: vbot = v of the last row, negstep = -vstep */
static void col_tex(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t v, int32_t negstep, uint16_t hmask)
{ p += (n - 1) * 4; for (; n; n--) { *p = tc[(uint16_t)(v >> 16) & hmask]; p -= 4; v += negstep; } }
static void col_tex_nm(uint8_t *p, uint16_t n, const uint8_t *tc, int32_t v, int32_t negstep)
{ p += (n - 1) * 4; for (; n; n--) { *p = tc[(uint16_t)(v >> 16)]; p -= 4; v += negstep; } }
#endif

/* signed 32 x small signed 16 (|k| <= 255) */
static inline int32_t mul32k(int32_t a, int16_t k)
{
    const int32_t lo = (int32_t)mulu16((uint16_t)a, (uint16_t)(k < 0 ? -k : k));
    return (muls16((int16_t)(a >> 16), k) << 16) + (k < 0 ? -lo : lo);
}

/* full 32-bit quotient of n / d with two 16-bit divides (d < 65536) */
static inline uint32_t udiv32_16(uint32_t n, uint16_t d)
{
    const uint16_t hi = divu16(n >> 16, d);
    const uint16_t lo = divu16((((n >> 16) - mulu16(hi, d)) << 16) | (n & 0xFFFF), d);
    return ((uint32_t)hi << 16) | lo;
}
/* (a * k) >> 15 for 0 <= k <= 32767, a signed 32-bit */
static inline int32_t mulhi15(int32_t a, int16_t k)
{
    return (muls16((int16_t)(a >> 16), k) << 1) + (int32_t)(mulu16((uint16_t)a, (uint16_t)k) >> 15);
}
/* a + delta * f8 / 256, f8 = 0..32767 (sub-column offset in 1/256 column) */
static inline int32_t advance(int32_t a, int32_t delta, int32_t f8)
{
    const int16_t whole = (int16_t)(f8 >> 8), part = (int16_t)(f8 & 255);   /* whole <= 8192 columns */
    return a + mul32k(delta, whole) + mul32k(delta >> 8, part);
}

void R_Init(void)
{
    for (int z = 16; z < 1024; z++) { const uint32_t r = (1UL << 20) / (uint32_t)z; RCP4[z] = r > 65535 ? 65535 : (uint16_t)r; }
    for (int i = 0; i < map_counts[4]; i++) map_sectors[i] = map_sectors_init[i];
    for (int i = 0; i < MAXV; i++) vstamp[i] = 0xFFFF;
}

static inline int16_t clamp16(int32_t v) { return v > 32767 ? 32767 : (v < -32767 ? -32767 : (int16_t)v); }

/* map point (integer units) -> camera space (units * 4) */
static inline void cam(int16_t px, int16_t py, int32_t *x4, int32_t *z4)
{
    const int16_t dx = px - view_xi, dy = py - view_yi;
    *z4 = ((muls16(dx, vcos) + muls16(dy, vsin)) >> 12) - frac_tz;
    *x4 = ((muls16(dx, vsin) - muls16(dy, vcos)) >> 12) - frac_tx;
}

static void xform(uint16_t v)
{
    if (vstamp[v] == frame_id) return;
    vstamp[v] = frame_id;
    int32_t x, z;
    cam(map_verts[v][0], map_verts[v][1], &x, &z);
    vtz[v] = clamp16(z); vtx[v] = clamp16(x);
}

/* screen x in 16.16 for a camera-space point (x4, z4), z4 >= NEAR4 */
/* reciprocal table: RCP4[z] = 2^20 / z for z in 16..1023 (larger z are normalised by shifting) */
static inline uint16_t rcp_norm(int32_t z, int *sh)
{
    int s2 = 0;
    while (z >= 1024) { z >>= 1; s2++; }
    *sh = s2;
    return RCP4[z < 16 ? 16 : z];
}
/* 2^24 / z4 */
static inline int32_t inv_z(int32_t z4)
{
    int sh; const uint16_t r = rcp_norm(z4, &sh);
    return ((int32_t)r << 4) >> sh;
}
/* screen x in 16.16: HALF_W + x*FOCAL/z  (FOCAL = 64) */
__attribute__((noinline)) static int32_t proj(int32_t x4, int32_t z4)
{
    int32_t ax = x4 < 0 ? -x4 : x4;
    if (ax >= (z4 << 6)) ax = (z4 << 6) - 1;
    int sh; const uint16_t r = rcp_norm(z4, &sh);
    /* ax * 2^14 / z = ax * (2^20/zn) >> (6 + sh) ; result as 24.8 then << 8 */
    int32_t q = (int32_t)(mulu16((uint16_t)ax, r) >> (6 + sh));
    if (x4 < 0) q = -q;
    return ((int32_t)HALF_W << 16) + (q << 8);
}

/* height dh (map units) at inverse depth iz (= 2^24 / z4) -> screen row, 16.16 */
static int32_t yrow(int16_t dh, int32_t iz)
{
    int32_t b = iz >> 5; if (b > 32767) b = 32767;
    int32_t a = (int32_t)dh * (VFOCAL / 4);
    if (a > 32767) a = 32767;
    if (a < -32767) a = -32767;
    int32_t r = ((int32_t)HORIZON << 16) - (muls16((int16_t)a, (int16_t)b) << 1);
    return r;
}

/* z4 = 2^24 / iz and u = uz / iz with 16-bit divides */
static inline uint16_t z4_of(int32_t iz)
{
    if (iz >= 65536) return divu16(65536, (uint16_t)(iz >> 8));
    if (iz < 257) return 65535;
    return divu16(1UL << 24, (uint16_t)iz);
}
static inline uint16_t u_of(uint32_t uz, int32_t iz)
{
    if (iz >= 65536) { const uint16_t d = (uint16_t)(iz >> 5); return (uz >> 5) >= ((uint32_t)d << 16) ? 65535 : divu16(uz >> 5, d); }
    if (iz <= 0) return 0;
    return (uz >= ((uint32_t)iz << 16)) ? 65535 : divu16(uz, (uint16_t)iz);
}

static inline int ceil16(int32_t y) { return (y + 0xFFFF) >> 16; }
static inline int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }

/* layout shared with colasm.s (offsets 0,4,6,8,10,12) */
typedef struct {
    const uint8_t *tex; uint16_t wmask, hs2, hmask, pal;   /* pal = view palette of this texture */
    int32_t vbase16;              /* (textop - viewz + yoff) << 16 */
} Part;

/* one seg's column job, consumed by seg_columns() (offsets used by colasm.s) */
typedef struct {
    uint8_t *fb;                                  /* 0 */
    int16_t *yc, *yf, *ybc, *ybf;                 /* 4 8 12 16  ceil(row) per column */
    uint16_t *u;                                  /* 20 */
    int32_t *zpp;                                 /* 24 */
    int16_t c0, xe;                               /* 28 30 */
    uint16_t ccol, fcol;                          /* 32 34 */
    uint16_t flags;                               /* 36: 1 solid, 2 mid, 4 upper, 8 lower */
    uint16_t closed;                              /* 38 */
    Part mid, up, lo;                             /* 40 56 72 */
    uint16_t cpal, ccol2, fpal, fcol2;            /* 88 90 92 94: fill spans {palette, colour} */
    uint16_t toff;                                /* 96 (scratch: tile column * TROWS) */
} ColJob;
static int16_t a_yc[VIEW_W], a_yf[VIEW_W], a_ybc[VIEW_W], a_ybf[VIEW_W];
static uint16_t a_u[VIEW_W];
static int32_t a_zpp[VIEW_W];
static ColJob job;
/* per 8x8 tile: the palette of the first (= nearest, front-to-back) span drawn in it; later spans of
 * another colour family are drawn through pal_remap so no pixel ever shows in the wrong palette */
#define TROWS (VIEW_H / 8)
#define TILES (32 * TROWS)
uint8_t tilepal[TILES];
uint8_t *const r_tilepal = tilepal;
const uint8_t *const r_remap = &pal_remap[0][0];
#if defined(__m68k__) || defined(__mc68000__)
extern void seg_columns(ColJob *j);
uint8_t *const r_clipbuf = clipbuf;   /* exported for colasm.s */
uint8_t *const r_nxt = nxt;
#else
static void draw_part(uint8_t *col, int y0, int y1, const Part *p, uint16_t u, int32_t zpp);
static inline uint8_t claim(int c, int y, uint8_t pal)
{
    uint8_t *t = &tilepal[(c >> 2) * TROWS + (y >> 3)];
    if (*t == 0xFF) *t = pal;
    return *t;
}
static inline uint8_t remap(uint8_t from, uint8_t to, uint8_t b) { return from == to ? b : pal_remap[from * num_palettes + to][b ^ 0x80]; }
static void span_fill(int c, int y0, int n, uint8_t pal, uint8_t col)
{
    uint8_t *p = FB_COL(rfb, c);
    for (int y = y0; y < y0 + n; y++) p[y << 2] = remap(pal, claim(c, y, pal), col);
}
static void seg_columns(ColJob *j)
{
    int c = j->c0;
    while (c < j->xe) {
        const int top = ceilclip[c], bot = floorclip[c];
        uint8_t *col = FB_COL(j->fb, c);
        int yc = j->yc[c]; if (yc < top) yc = top; if (yc > bot) yc = bot;
        int yf = j->yf[c]; if (yf < yc) yf = yc; if (yf > bot) yf = bot;
        if (yc > top) span_fill(c, top, yc - top, (uint8_t)j->cpal, (uint8_t)j->ccol);
        if (bot > yf) span_fill(c, yf, bot - yf, (uint8_t)j->fpal, (uint8_t)j->fcol);
        if (j->flags & 1) {
            if ((j->flags & 2) && yf > yc) draw_part(col, yc, yf, &j->mid, j->u[c], j->zpp[c]);
            close_col(c); j->closed++;
        } else {
            int ntop = yc, nbot = yf;
            if (j->flags & 4) {
                int y = j->ybc[c]; if (y < yc) y = yc; if (y > yf) y = yf;
                if (y > yc) draw_part(col, yc, y, &j->up, j->u[c], j->zpp[c]);
                ntop = y;
            }
            if (j->flags & 8) {
                int y = j->ybf[c]; if (y < ntop) y = ntop; if (y > yf) y = yf;
                if (yf > y) draw_part(col, y, yf, &j->lo, j->u[c], j->zpp[c]);
                nbot = y;
            }
            if (ntop >= nbot) { close_col(c); j->closed++; }
            else { ceilclip[c] = (uint8_t)ntop; floorclip[c] = (uint8_t)nbot; }
        }
        c = find_open(c + 1);
    }
}
#endif

static void setup_part(Part *p, uint8_t t, uint8_t bucket, int16_t textop, int16_t yoff)
{
    const MapTex *m = &map_tex[t];
    p->tex = tex_blob + m->off[bucket];
    p->wmask = (1u << m->wshift) - 1;
    p->hs2 = m->hshift + 1;                       /* columns are stored twice */
    p->hmask = (1u << m->hshift) - 1;
    p->pal = m->pal[bucket];
    p->vbase16 = ((int32_t)(textop - view_z + yoff)) << 16;
}

static inline void draw_part(uint8_t *col, int y0, int y1, const Part *p, uint16_t u, int32_t zpp)
{
    if (dbg_flags & 1) return;
#if !(defined(__m68k__) || defined(__mc68000__))
    {   /* host reference of the 68000 path: draw, then remap rows whose tile belongs to another palette */
        const int c = (int)(((col - rfb) / (VIEW_H * 4)) * 4 + ((col - rfb) % (VIEW_H * 4)));
        const uint8_t *tc = p->tex + ((u & p->wmask) << p->hs2);
        const int32_t vbot = p->vbase16 - mul32k(zpp, (int16_t)(HORIZON - (y1 - 1)));
        for (int y = y1 - 1, k = 0; y >= y0; y--, k++) {
            const int32_t v = vbot - zpp * k;
            const uint8_t b = tc[(uint16_t)(v >> 16) & p->hmask];
            col[y << 2] = remap((uint8_t)p->pal, claim(c, y, (uint8_t)p->pal), b);
        }
        return;
    }
#endif
    /* texture columns are stored twice (2H texels): no wrap mask needed while the span fits in H */
    const uint8_t *tc = p->tex + ((u & p->wmask) << p->hs2);
    const uint16_t n = (uint16_t)(y1 - y0);
    int32_t vbot = p->vbase16 - mul32k(zpp, (int16_t)(HORIZON - (y1 - 1)));
    const int32_t span = mul32k(zpp, (int16_t)(n - 1));
    if (span < ((int32_t)p->hmask << 16)) {
        vbot = (vbot & (((int32_t)p->hmask << 16) | 0xFFFF)) + ((int32_t)(p->hmask + 1) << 16);
        col_tex_nm(col + (y0 << 2), n, tc, vbot, -zpp);
    } else
        col_tex(col + (y0 << 2), n, tc, vbot, -zpp, p->hmask);
}

/* per-column delta of a value over the span: (b - a) * 256 / span8, with rcp = 2^23 / span8 */
static int32_t lspan8;   /* span of the current seg, columns * 256 */
static inline int32_t lstep(int32_t a, int32_t b, int16_t rcp)
{
    if (lspan8 <= 65535) return mulhi15(b - a, rcp);
    /* very wide projected span (a wall passing right beside the camera): exact 32/16 divide */
    const int32_t d = b - a; const uint16_t n = (uint16_t)(lspan8 >> 8);
    return d < 0 ? -(int32_t)udiv32_16((uint32_t)-d, n) : (int32_t)udiv32_16((uint32_t)d, n);
}

__attribute__((noinline)) static void draw_seg(const MapSeg *s)
{
    xform(s->v1); xform(s->v2);
    int16_t x1 = vtx[s->v1], z1 = vtz[s->v1], x2 = vtx[s->v2], z2 = vtz[s->v2];
    if (z1 < NEAR4 && z2 < NEAR4) return;
    /* back face: the seg's front side faces the viewer when x1*z2 - x2*z1 < 0 */
    if (muls16(x1, z2) - muls16(x2, z1) >= 0) return;
    int32_t t1 = 0, t2 = 65536;            /* Q16 position along the seg */
    if (z1 < NEAR4 || z2 < NEAR4) {
        const int32_t dz = (int32_t)z2 - z1, dx = (int32_t)x2 - x1;
        const int16_t ox1 = x1, oz1 = z1;
        if (oz1 < NEAR4) {
            t1 = (int32_t)(((int64_t)(NEAR4 - oz1) << 16) / dz);
            x1 = (int16_t)(ox1 + (int32_t)(((int64_t)dx * t1) >> 16)); z1 = NEAR4;
        }
        if (z2 < NEAR4) {
            t2 = (int32_t)(((int64_t)(NEAR4 - oz1) << 16) / dz);
            x2 = (int16_t)(ox1 + (int32_t)(((int64_t)dx * t2) >> 16)); z2 = NEAR4;
        }
    }
    const int32_t sx1 = proj(x1, z1), sx2 = proj(x2, z2);
    if (sx1 >= sx2) return;
    int xs = ceil16(sx1), xe = ceil16(sx2);
    if (xs < 0) xs = 0;
    if (xe > VIEW_W) xe = VIEW_W;
    if (xs >= xe) return;
    int c = find_open(xs);
    if (c >= xe) return;                    /* fully hidden behind closed columns */
    rstats.segs_drawn++;
#ifdef PVS_GEN
    pvs_seen[cur_sub] = 1;
#endif

    const MapSector *fs = &map_sectors[s->front];
    const MapSector *bs = (s->back != 0xFF) ? &map_sectors[s->back] : 0;
    const uint8_t bucket = fs->bucket;

    /* inverse depth (2^24 / z4) and u (half texels) at both ends */
    const int32_t iz1 = inv_z(z1), iz2 = inv_z(z2);
    int32_t u1 = s->xoff, u2 = s->xoff + s->len;
    if (t1) u1 += (int32_t)(((int64_t)s->len * t1) >> 16);
    if (t2 != 65536) u2 = s->xoff + (int32_t)(((int64_t)s->len * t2) >> 16);
    u1 >>= 1; u2 >>= 1;
    const int32_t ub = u1 & ~1023;
    /* u/z / 256: (u - ub) < 2048, iz < 2^20 -> fits after the shift */
    const int32_t uz1 = muls16((int16_t)(u1 - ub), (int16_t)(iz1 >> 8)), uz2 = muls16((int16_t)(u2 - ub), (int16_t)(iz2 >> 8));

    const int32_t span8 = (sx2 - sx1) >> 8;       /* columns * 256 */
    const int16_t rcp = span8 > 256 ? (int16_t)divu16(1UL << 23, (uint16_t)(span8 > 65535 ? 65535 : span8)) : 32767;
    int32_t f8 = (((int32_t)xs << 16) - sx1) >> 8;
    lspan8 = span8;

    const int32_t diz = lstep(iz1, iz2, rcp);
    int32_t iz = advance(iz1, diz, f8);
    const int32_t duz = lstep(uz1, uz2, rcp);
    int32_t uz = advance(uz1, duz, f8);

    const int16_t fc = fs->ceil - view_z, ff = fs->floor - view_z;
    const int32_t Yc1 = yrow(fc, iz1), Yc2 = yrow(fc, iz2), Yf1 = yrow(ff, iz1), Yf2 = yrow(ff, iz2);
    const int32_t dYc = lstep(Yc1, Yc2, rcp), dYf = lstep(Yf1, Yf2, rcp);
    int32_t Yc = advance(Yc1, dYc, f8), Yf = advance(Yf1, dYf, f8);

    Part mid = {0}, up = {0}, lo = {0};
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
            dYbc = lstep(a, b, rcp); Ybc = advance(a, dYbc, f8);
        }
        if (bs->floor > fs->floor && s->lower != 0xFF) {
            has_lo = 1;
            const int16_t textop = (s->flags & 2) ? fs->ceil : bs->floor;
            setup_part(&lo, s->lower, bucket, textop, s->yoff);
            const int16_t bf = bs->floor - view_z;
            const int32_t a = yrow(bf, iz1), b = yrow(bf, iz2);
            dYbf = lstep(a, b, rcp); Ybf = advance(a, dYbf, f8);
        }
    }
    const int need_tex = has_mid | has_up | has_lo;
    const int32_t diz8 = diz << 3, duz8 = duz << 3;
    if (dbg_flags & 4) { for (int k = xs; k < xe; k++) if (ceilclip[k] < floorclip[k]) { close_col(k); closed++; } return; }

    /* only the open part of the span matters: [c, xe2) */
    int xe2 = xe;
    while (xe2 > c && ceilclip[xe2 - 1] >= floorclip[xe2 - 1]) xe2--;
    if (c > xs) {   /* move every interpolant to the first open column */
        const int16_t k = (int16_t)(c - xs);
        iz += mul32k(diz, k); uz += mul32k(duz, k);
        Yc += mul32k(dYc, k); Yf += mul32k(dYf, k);
        if (has_up) Ybc += mul32k(dYbc, k);
        if (has_lo) Ybf += mul32k(dYbf, k);
        xs = c;
    }
    xe = xe2;

    /* phase A: per-column values in plain arrays (cheap linear loops) */
    for (int k = xs; k < xe; k++) { a_yc[k] = (int16_t)ceil16(Yc); a_yf[k] = (int16_t)ceil16(Yf); Yc += dYc; Yf += dYf; }
    if (has_up) for (int k = xs; k < xe; k++) { a_ybc[k] = (int16_t)ceil16(Ybc); Ybc += dYbc; }
    if (has_lo) for (int k = xs; k < xe; k++) { a_ybf[k] = (int16_t)ceil16(Ybf); Ybf += dYbf; }
    if (need_tex) {
        /* exact u and texel step every ANCHOR columns, linear in between */
        for (int k = xs; k < xe; ) {
            int n = xe - 1 - k; if (n > ANCHOR) n = ANCHOR;
            rstats.anchors++;
            const int32_t izA = iz > 1 ? iz : 1, uzA = uz > 0 ? uz : 0;
            const uint16_t uA = u_of((uint32_t)uzA << 8, izA), zA = z4_of(izA);
            int32_t ua8 = (int32_t)uA << 8, zp = (int32_t)zA << 7, du8 = 0, dzp = 0;
            if (n > 0) {
                int32_t izB, uzB;
                if (n == ANCHOR) { izB = iz + diz8; uzB = uz + duz8; }
                else { izB = iz + mul32k(diz, (int16_t)n); uzB = uz + mul32k(duz, (int16_t)n); }
                if (izB < 1) izB = 1;
                if (uzB < 0) uzB = 0;
                const uint16_t uB = u_of((uint32_t)uzB << 8, izB), zB = z4_of(izB);
                if (n == ANCHOR) { du8 = ((int32_t)uB - (int32_t)uA) << 5; dzp = ((int32_t)zB - (int32_t)zA) << 4; }
                else {
                    const int32_t du = (int32_t)uB - (int32_t)uA, dz = (int32_t)zB - (int32_t)zA;
                    du8 = (du > -128 && du < 128) ? divs16(du << 8, (int16_t)n) : (du << 8) / n;
                    dzp = (dz > -256 && dz < 256) ? divs16(dz << 7, (int16_t)n) : (dz << 7) / n;
                }
            }
            const int m = n > 0 ? n : 1;
            for (int q = 0; q < m && k < xe; q++, k++) { a_u[k] = (uint16_t)(ua8 >> 8); a_zpp[k] = zp; ua8 += du8; zp += dzp; }
            if (n == ANCHOR) { iz += diz8; uz += duz8; } else { iz += mul32k(diz, (int16_t)m); uz += mul32k(duz, (int16_t)m); }
        }
    }

    /* phase B: clip, fill, texture and close, column by column (68000: colasm.s) */
    job.fb = rfb; job.c0 = (int16_t)c; job.xe = (int16_t)xe;
    job.ccol = fs->ceilcol; job.fcol = fs->floorcol;
    job.cpal = fs->ceilpal; job.ccol2 = fs->ceilcol; job.fpal = fs->floorpal; job.fcol2 = fs->floorcol;
    job.flags = (bs ? 0 : 1) | (has_mid ? 2 : 0) | (has_up ? 4 : 0) | (has_lo ? 8 : 0);
    job.mid = mid; job.up = up; job.lo = lo;
    job.closed = 0;
    seg_columns(&job);
    closed += job.closed;
    rstats.col_visits++;
}

/* Doom's R_CheckBBox idea: only the two silhouette corners of the box matter */
static const uint8_t checkcoord[12][4] = {
    {3,0,2,1}, {3,0,2,0}, {3,1,2,0}, {0,0,0,0},
    {2,0,2,1}, {0,0,0,0}, {3,1,3,0}, {0,0,0,0},
    {2,0,3,1}, {2,1,3,1}, {2,1,3,0}, {0,0,0,0}
};
__attribute__((noinline)) static int bbox_visible(const int16_t *bb)
{
    /* bb = top, bottom, left, right */
    const int bx = view_xi <= bb[2] ? 0 : (view_xi < bb[3] ? 1 : 2);
    const int by = view_yi >= bb[0] ? 0 : (view_yi > bb[1] ? 4 : 8);
    const int pos = bx + by;
    if (pos == 5) return 1;
    const uint8_t *cc = checkcoord[pos];
    int32_t x1, z1, x2, z2;
    cam(bb[cc[0]], bb[cc[1]], &x1, &z1);
    cam(bb[cc[2]], bb[cc[3]], &x2, &z2);
    if (z1 < NEAR4 || z2 < NEAR4) {
        if (z1 < 0 && z2 < 0) return 0;      /* both silhouette corners behind: the box (< 180 deg wide) is behind */
        return 1;
    }
    if (z1 > 32767) z1 = 32767;
    if (z2 > 32767) z2 = 32767;
    if (x1 > 32767) x1 = 32767; else if (x1 < -32767) x1 = -32767;
    if (x2 > 32767) x2 = 32767; else if (x2 < -32767) x2 = -32767;
    int32_t s1 = proj(x1, z1), s2 = proj(x2, z2);
    if (s1 > s2) { const int32_t t = s1; s1 = s2; s2 = t; }
    int a = ceil16(s1), b = ceil16(s2);
    if (a < 0) a = 0;
    if (b > VIEW_W) b = VIEW_W;
    return a < b && find_open(a) < b;
}

static void render_node(uint16_t n)
{
    if (closed >= VIEW_W) return;
    if (n & 0x8000) {
#ifdef PVS_GEN
        cur_sub = n & 0x7FFF;
#else
        if (!(pv_s[(n & 0x7FFF) >> 3] & (1 << (n & 7)))) return;
#endif
        const MapSub *ss = &map_subs[n & 0x7FFF];
        rstats.subs_visited++;
        for (uint16_t i = 0; i < ss->count; i++) draw_seg(&map_segs[ss->first + i]);
        return;
    }
#ifndef PVS_GEN
    if (!(pv_n[n >> 3] & (1 << (n & 7)))) return;   /* nothing in this subtree is visible from here */
#endif
    const MapNode *nd = &map_nodes[n];
    rstats.nodes_visited++;
    const int16_t dx = view_xi - nd->x, dy = view_yi - nd->y;
    const int side = (muls16(nd->dy, dx) > muls16(nd->dx, dy)) ? 0 : 1;
    render_node(nd->child[side]);
    if (bbox_visible(nd->bbox[side ^ 1])) render_node(nd->child[side ^ 1]);
}

int R_PointInSub(int16_t x, int16_t y)
{
    uint16_t n = map_counts[3] - 1;
    while (!(n & 0x8000)) {
        const MapNode *nd = &map_nodes[n];
        const int16_t dx = x - nd->x, dy = y - nd->y;
        n = nd->child[(muls16(nd->dy, dx) > muls16(nd->dx, dy)) ? 0 : 1];
    }
    return n & 0x7FFF;
}

void R_RenderView(const View *v, uint8_t *fb)
{
    rfb = fb;
    job.yc = a_yc; job.yf = a_yf; job.ybc = a_ybc; job.ybf = a_ybf; job.u = a_u; job.zpp = a_zpp;
    frame_id++;
    if (frame_id == 0xFFFF) { frame_id = 0; for (int i = 0; i < MAXV; i++) vstamp[i] = 0xFFFF; }
    view_x4 = v->x >> 14; view_y4 = v->y >> 14; view_z = v->z;
    view_xi = (int16_t)(v->x >> 16); view_yi = (int16_t)(v->y >> 16);
    const uint16_t a = v->angle >> 6;
    vsin = sintab[a]; vcos = sintab[(a + 256) & 1023];
    /* fractional part of the position (0..1 unit), in camera space * 4 */
    const int16_t fx = (int16_t)((v->x & 0xFFFF) >> 2), fy = (int16_t)((v->y & 0xFFFF) >> 2);   /* Q14 units */
    /* Q14 units * Q14 = Q28 units; camera space is units * 4 -> >> 26 */
    frac_tz = (muls16(fx, vcos) + muls16(fy, vsin)) >> 26;
    frac_tx = (muls16(fx, vsin) - muls16(fy, vcos)) >> 26;
    for (int c = 0; c < VIEW_W; c++) { ceilclip[c] = 0; floorclip[c] = VIEW_H; nxt[c] = (uint8_t)c; }
#if !defined(NPAL) || NPAL != 1
    { uint32_t *t = (uint32_t *)tilepal; for (int i = 0; i < (int)(sizeof tilepal / 4); i++) t[i] = 0xFFFFFFFFUL; }
#endif
    nxt[VIEW_W] = VIEW_W;
    closed = 0;
    rstats.segs_drawn = rstats.nodes_visited = rstats.subs_visited = rstats.col_visits = rstats.anchors = 0;
    const uint32_t t0 = now_lines();
#ifndef PVS_GEN
    {
        const int sub = R_PointInSub(view_xi, view_yi);
        pv_n = pvs_nodes + (uint32_t)sub * pvs_nbytes;
        pv_s = pvs_subs + (uint32_t)sub * pvs_sbytes;
        if (r_pvs_off) pv_n = pv_s = pv_all;
    }
#endif
    render_node(map_counts[3] - 1);
    tm_total += now_lines() - t0;
    rstats.cols_closed = closed;
}

/* name table entries for the view (row-major, TROWS x 32): tile index | majority palette << 13 */
void R_BuildNametable(uint16_t *nt, uint16_t tilebase)
{
    for (int tc = 0; tc < 32; tc++)
        for (int tr = 0; tr < TROWS; tr++) {
            const int i = tc * TROWS + tr;
            const uint16_t k = tilepal[i] == 0xFF ? 0 : tilepal[i];
            nt[tr * 32 + tc] = (uint16_t)(tilebase + i) | (uint16_t)(k << 13);
        }
}
