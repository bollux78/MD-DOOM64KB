#!/usr/bin/env python3
"""R70-A: differential host test of the real R_RenderSegLoop text.

Compiles the function extracted from src/r_draw.c four times (control, A1 = DOOM_R21_SEGLOOP_LOCALS,
A2 = DOOM_R70A_INVARIANTS, A1+A2) with the same perf-build macro set, drives them with identical random
segments and compares every observable effect byte for byte: each draw call (kind, arguments, full
dcvars), the clip arrays, solidcol, maskedtexturecol, didsolidcol and the globals written back after
the loop. Control must equal every variant. Needs gcc only.
"""
import re, subprocess, sys, tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]


def function(src, name):
    m = re.search(r'\bstatic\s+(?:inline\s+)?\w[\w\s\*]*?\b' + name + r'\s*\(', src)
    start = src.rfind('\n', 0, m.start()) + 1
    begin = src.index('{', start); depth = 1; end = begin + 1
    while depth:
        depth += (src[end] == '{') - (src[end] == '}'); end += 1
    return src[start:end]


draw = (root / 'src/r_draw.c').read_text()
seg = function(draw, 'R_RenderSegLoop')
tan = function(draw, 'R20_TanMulU16') + '\n' + function(draw, 'R15_Mul16x32Shift16U')

PRELUDE = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
typedef bool boolean;
typedef int32_t fixed_t;
typedef uint16_t angle16_t;
typedef uint8_t byte;
#define __far
#define FRACBITS 16
#define FRACUNIT (1L<<FRACBITS)
#define ANGLETOFINESHIFT_16 3
#define VIEWWINDOWWIDTH 76
#define VIEWWINDOWHEIGHT 44
#define CENTERY 22
#define COLEXTRABITS 7
#define FLAT_SPAN 1
#define DOOM_R66_COLPAIR 1
#define DOOM_R20_TAN_MULS 1
#define DOOM_R20_TAN32 1
#define DOOM_FAST_DIVU 1
#define DOOM_R12_RECIP_LUT 65535
#define R12_RECIP_MAX 65535u
#define R37_HIT(x) ((void)0)
#define R20_COUNT(i,n) ((void)0)
#define R20_WALLCOL(w, tex, texture, col, dc) R_DrawSegTextureColumn((tex), (texture), (col), (dc))
#define R20_WALL_DRAW(v) R_DrawColumnWall(v)
#define R15_TAN_PRODUCT(a, b) R15_Mul16x32Shift16U((a), (b))
#define FixedReciprocal(v) (0xffffffffu/(v))
static inline uint32_t mulu(uint16_t a, uint16_t b){return (uint32_t)a*b;}
typedef struct { int16_t x, yl, yh; uint16_t fracstep; fixed_t texturemid; const byte *source; const uint8_t *colormap; } draw_column_vars_t;
typedef struct { int dummy; } texture_t;
static int16_t floorplane_color, ceilingplane_color;
static int16_t rw_distance, rw_stopx, rw_offset, rw_lightlevel;
static angle16_t rw_centerangle;
static fixed_t rw_scale, rw_scalestep, topfrac, topstep, bottomfrac, bottomstep, pixhigh, pixlow, pixhighstep, pixlowstep;
static fixed_t rw_midtexturemid, rw_toptexturemid, rw_bottomtexturemid;
static boolean maskedtexture, didsolidcol;
static int16_t toptexture, bottomtexture, midtexture;
static const texture_t *textoptexture, *texbottomtexture, *texmidtexture;
static int16_t *maskedtexturecol;
static int16_t floorclip[VIEWWINDOWWIDTH], ceilingclip[VIEWWINDOWWIDTH];
static uint8_t solidcol[VIEWWINDOWWIDTH];
static uint16_t xtoviewangleTable[VIEWWINDOWWIDTH + 1];
static uint16_t finetangentTable_part_3[1024];
static fixed_t finetangentTable_part_4[1024];
static uint16_t r12_recip_table[65535 - 512 + 1];
static uint8_t cmaps[64][4];
static uint64_t trace_hash; static unsigned trace_n;
static void T(uint64_t v){ trace_hash = (trace_hash ^ v) * 1099511628211ull; trace_n++; }
static void TD(int kind, const draw_column_vars_t *d){
    T(kind); T((uint16_t)d->x); T((uint16_t)d->yl); T((uint16_t)d->yh); T(d->fracstep); T((uint32_t)d->texturemid);
    T((uint64_t)(uintptr_t)d->source); T((uint64_t)(d->colormap - &cmaps[0][0]));
}
static const uint8_t *R_LoadColorMap(int16_t l){ return cmaps[(uint16_t)l & 63]; }
static void R_DrawColumnFlat(int16_t color, draw_column_vars_t *d){ T((uint16_t)color); TD(1, d); }
static void R_DrawSky(draw_column_vars_t *d){ TD(2, d); d->fracstep = (uint16_t)(d->fracstep * 3u + 1u); d->colormap = cmaps[5]; }
static void R_DrawColumnWall(const draw_column_vars_t *d){ TD(3, d); }
static void R_DrawSegTextureColumn(const texture_t *tex, int16_t texture, int16_t col, draw_column_vars_t *d){
    T((uint64_t)tex->dummy); T((uint16_t)texture); T((uint16_t)col);
    d->source = (const byte *)0 + 4096 + (uint16_t)texture * 131u + (uint16_t)col * 7u;
    TD(4, d); R_DrawColumnWall(d);
}
'''

MAIN = r'''
static uint32_t rng = 20261026u;
static uint32_t rnd(void){ rng = rng * 1664525u + 1013904223u; return rng; }
static int pick(int lo, int hi){ return lo + (int)(rnd() % (uint32_t)(hi - lo + 1)); }
int main(int argc, char **argv){
    int scenarios = argc > 1 ? atoi(argv[1]) : 20000;
    for (int i = 0; i < 64; i++) cmaps[i][0] = (uint8_t)i;
    for (int i = 0; i < 1024; i++){ finetangentTable_part_3[i] = (uint16_t)rnd(); finetangentTable_part_4[i] = (fixed_t)(rnd() & 0x3ffffff) * ((rnd() & 1) ? 1 : -1); }
    for (int i = 0; i < 65535 - 512 + 1; i++) r12_recip_table[i] = (uint16_t)(0x01ffffffu / (uint32_t)(i + 512));
    static texture_t tex[3];
    static int16_t masked[VIEWWINDOWWIDTH];
    unsigned long long total = 0;
    for (int sc = 0; sc < scenarios; sc++){
        int start = pick(0, 70), stop = pick(start + 1, VIEWWINDOWWIDTH);
        rw_stopx = (int16_t)stop;
        int mode = pick(0, 9);
        midtexture = toptexture = bottomtexture = 0; maskedtexture = 0;
        if (mode < 3) midtexture = pick(1, 30);
        else { toptexture = (mode & 1) ? pick(1, 30) : 0; bottomtexture = (mode & 2) ? pick(1, 30) : 0; maskedtexture = (mode == 9); }
        for (int k = 0; k < 3; k++) tex[k].dummy = 100 + k;
        texmidtexture = &tex[0]; textoptexture = &tex[1]; texbottomtexture = &tex[2];
        floorplane_color = (int16_t)pick(0, 255); ceilingplane_color = (pick(0, 3) == 0) ? -2 : (int16_t)pick(0, 255);
        rw_distance = (int16_t)pick(-4000, 12000); rw_offset = (int16_t)pick(-3000, 3000);
        rw_centerangle = (angle16_t)pick(0, 16383); rw_lightlevel = (int16_t)pick(0, 255);
        for (int x = 0; x <= VIEWWINDOWWIDTH; x++) xtoviewangleTable[x] = (uint16_t)pick(0, 16383);
        rw_scale = pick(100, 80000) + (pick(0, 20) == 0 ? 40000 : 0); rw_scalestep = pick(-(int)(rw_scale / 80), 700);
        topfrac = pick(-10, 40) * FRACUNIT + pick(0, 65535); topstep = pick(-30000, 30000);
        bottomfrac = pick(0, 60) * FRACUNIT + pick(0, 65535); bottomstep = pick(-30000, 30000);
        pixhigh = pick(-5, 50) * FRACUNIT + pick(0, 65535); pixhighstep = pick(-30000, 30000);
        pixlow = pick(-5, 50) * FRACUNIT + pick(0, 65535); pixlowstep = pick(-30000, 30000);
        rw_midtexturemid = pick(-200000, 600000); rw_toptexturemid = pick(-200000, 600000); rw_bottomtexturemid = pick(-200000, 600000);
        for (int x = 0; x < VIEWWINDOWWIDTH; x++){ ceilingclip[x] = (int16_t)pick(-1, 30); floorclip[x] = (int16_t)pick(10, 44); solidcol[x] = 0; masked[x] = -999; }
        maskedtexturecol = masked; didsolidcol = 0;
        boolean segtextured = pick(0, 4) != 0, markfloor = pick(0, 2) != 0, markceiling = pick(0, 2) != 0;
        trace_hash = 1469598103934665603ull; trace_n = 0;
        R_RenderSegLoop((int16_t)start, segtextured, markfloor, markceiling);
        T((uint32_t)rw_scale); T((uint32_t)topfrac); T((uint32_t)bottomfrac); T((uint32_t)pixhigh); T((uint32_t)pixlow);
        T((uint32_t)rw_scalestep); T((uint32_t)topstep); T((uint32_t)bottomstep); T((uint32_t)pixhighstep); T((uint32_t)pixlowstep);
        T(didsolidcol); T((uint16_t)rw_stopx);
        for (int x = 0; x < VIEWWINDOWWIDTH; x++){ T((uint16_t)floorclip[x]); T((uint16_t)ceilingclip[x]); T(solidcol[x]); T((uint16_t)masked[x]); }
        total += trace_n;
        printf("%d %u %016llx\n", sc, trace_n, (unsigned long long)trace_hash);
    }
    fprintf(stderr, "events %llu\n", total);
    return 0;
}
'''


def build(tmp, name, defs):
    c = tmp / (name + '.c')
    c.write_text('#include <stdlib.h>\n' + PRELUDE + tan + '\n' + seg + '\n#include <stdlib.h>\n' + MAIN)
    exe = tmp / name
    subprocess.run(['gcc', '-O1', '-w', *defs, str(c), '-o', str(exe)], check=True)
    return exe


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else '20000'
    variants = [('control', []), ('a1', ['-DDOOM_R21_SEGLOOP_LOCALS']), ('a2', ['-DDOOM_R70A_INVARIANTS']),
                ('a1a2', ['-DDOOM_R21_SEGLOOP_LOCALS', '-DDOOM_R70A_INVARIANTS'])]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); out = {}
        for name, defs in variants:
            exe = build(d, name, defs)
            r = subprocess.run([str(exe), n], capture_output=True, text=True, check=True)
            out[name] = r.stdout
            print('%-8s %s' % (name, r.stderr.strip()))
        ok = True
        for name in ('a1', 'a2', 'a1a2'):
            same = out[name] == out['control']
            ok &= same
            print('%-8s %s control over %s scenarios' % (name, 'IDENTICAL to' if same else 'DIFFERS from', n))
            if not same:
                for a, b in zip(out['control'].splitlines(), out[name].splitlines()):
                    if a != b:
                        print('  first difference: control %s / %s %s' % (a, name, b)); break
        sys.exit(0 if ok else 1)


main()
