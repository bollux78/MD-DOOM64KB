#!/usr/bin/env python3
"""R70-A: differential host test of the real R_RenderSegLoop text.

Compiles the function extracted from src/r_draw.c four times (control, A1 = DOOM_R21_SEGLOOP_LOCALS,
A2 = DOOM_R70A_INVARIANTS, A1+A2) with the same perf-build macro set, drives them with identical random
segments and compares every observable effect byte for byte: each draw call (kind, arguments, full
dcvars), the clip arrays, solidcol, maskedtexturecol, didsolidcol and the globals written back after
the loop. Control must equal every variant. Needs gcc only.

On any mismatch the first differing scenario is replayed with a full event trace for control and variant, and the first
concrete difference is printed: event name (routine and field / clip index / global), values, the preceding events and
the scenario inputs. Nothing is relaxed to force a PASS. Diagnostics:
  --legacy   hash ALSO the dcvars fields a routine does not read (uninitialised stack garbage), without zero-init: this is
             the harness of the first runner run and is expected to be unstable; used to prove that instability.
  --opt N    compiler optimisation level (default 1); --std STD passes -std=STD.
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
static uint64_t trace_hash; static unsigned trace_n; static int tracing;
static void EV(const char *name, uint64_t v){
    trace_hash = (trace_hash ^ v) * 1099511628211ull; trace_n++;
    if (tracing) printf("ev %u %s %llu\n", trace_n, name, (unsigned long long)v);
}
static void TD3(const char *r, int16_t x, int16_t yl, int16_t yh){
    char b[64];
    snprintf(b, sizeof b, "%s.x", r); EV(b, (uint16_t)x);
    snprintf(b, sizeof b, "%s.yl", r); EV(b, (uint16_t)yl);
    snprintf(b, sizeof b, "%s.yh", r); EV(b, (uint16_t)yh);
}
/* Wall draw reads every field. Flat reads only x, yl, yh (r22_video.inc R_DrawColumnFlat); sky writes all fields itself (r_sky.c). */
static void TDW(const char *r, const draw_column_vars_t *d){
    char b[64];
    TD3(r, d->x, d->yl, d->yh);
    snprintf(b, sizeof b, "%s.fracstep", r); EV(b, d->fracstep);
    snprintf(b, sizeof b, "%s.texturemid", r); EV(b, (uint32_t)d->texturemid);
    snprintf(b, sizeof b, "%s.source", r); EV(b, (uint64_t)(uintptr_t)d->source);
    snprintf(b, sizeof b, "%s.colormap", r); EV(b, (uint64_t)(d->colormap - &cmaps[0][0]));
}
static const uint8_t *R_LoadColorMap(int16_t l){ return cmaps[(uint16_t)l & 63]; }
static void R_DrawColumnFlat(int16_t color, draw_column_vars_t *d){
    EV("flat.color", (uint16_t)color); TD3("flat", d->x, d->yl, d->yh);
#ifdef LEGACY_UNINIT_HASH
    EV("flat.UNREAD.fracstep", d->fracstep); EV("flat.UNREAD.texturemid", (uint32_t)d->texturemid);
    EV("flat.UNREAD.source", (uint64_t)(uintptr_t)d->source); EV("flat.UNREAD.colormap", (uint64_t)(uintptr_t)d->colormap);
#endif
}
/* like r_sky.c: sets texturemid, colormap, fracstep and source, then draws the column */
static void R_DrawSky(draw_column_vars_t *d){
    d->texturemid = 100 * FRACUNIT; d->colormap = cmaps[5]; d->fracstep = 77; d->source = (const byte *)0 + 9000 + (uint16_t)d->x; TDW("sky", d); }
static void R_DrawColumnWall(const draw_column_vars_t *d){ TDW("wall", d); }
static void R_DrawSegTextureColumn(const texture_t *tex, int16_t texture, int16_t col, draw_column_vars_t *d){
    EV("segtex.tex", (uint64_t)tex->dummy); EV("segtex.texture", (uint16_t)texture); EV("segtex.col", (uint16_t)col);
    d->source = (const byte *)0 + 4096 + (uint16_t)texture * 131u + (uint16_t)col * 7u;
    R_DrawColumnWall(d);
}
'''

MAIN = r'''
static uint32_t rng = 20261026u;
static uint32_t rnd(void){ rng = rng * 1664525u + 1013904223u; return rng; }
static int pick(int lo, int hi){ return lo + (int)(rnd() % (uint32_t)(hi - lo + 1)); }
int main(int argc, char **argv){
    int scenarios = argc > 1 ? atoi(argv[1]) : 20000;
    int trace_sc = argc > 2 ? atoi(argv[2]) : -1;        /* print the full event trace and inputs of this scenario */
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
        boolean segtextured = ((midtexture | toptexture | bottomtexture | maskedtexture) > 0), markfloor = pick(0, 2) != 0, markceiling = pick(0, 2) != 0;
        trace_hash = 1469598103934665603ull; trace_n = 0; tracing = (sc == trace_sc);
        if (tracing){
            printf("scenario %d inputs: start=%d stop=%d segtextured=%d markfloor=%d markceiling=%d mid=%d top=%d bottom=%d masked=%d floorcolor=%d ceilingcolor=%d\n",
                   sc, start, stop, segtextured, markfloor, markceiling, midtexture, toptexture, bottomtexture, maskedtexture, floorplane_color, ceilingplane_color);
            printf("  distance=%d offset=%d centerangle=%d light=%d scale=%d scalestep=%d topfrac=%d topstep=%d bottomfrac=%d bottomstep=%d\n",
                   rw_distance, rw_offset, rw_centerangle, rw_lightlevel, rw_scale, rw_scalestep, topfrac, topstep, bottomfrac, bottomstep);
            printf("  pixhigh=%d pixhighstep=%d pixlow=%d pixlowstep=%d midmid=%d topmid=%d botmid=%d\n", pixhigh, pixhighstep, pixlow, pixlowstep, rw_midtexturemid, rw_toptexturemid, rw_bottomtexturemid);
            printf("  ceilingclip[start..]=%d,%d,%d floorclip[start..]=%d,%d,%d\n", ceilingclip[start], ceilingclip[start+1 < 76 ? start+1 : start], ceilingclip[start+2 < 76 ? start+2 : start], floorclip[start], floorclip[start+1 < 76 ? start+1 : start], floorclip[start+2 < 76 ? start+2 : start]);
        }
        R_RenderSegLoop((int16_t)start, segtextured, markfloor, markceiling);
        EV("end.rw_scale", (uint32_t)rw_scale); EV("end.topfrac", (uint32_t)topfrac); EV("end.bottomfrac", (uint32_t)bottomfrac);
        EV("end.pixhigh", (uint32_t)pixhigh); EV("end.pixlow", (uint32_t)pixlow);
        EV("end.rw_scalestep", (uint32_t)rw_scalestep); EV("end.topstep", (uint32_t)topstep); EV("end.bottomstep", (uint32_t)bottomstep);
        EV("end.pixhighstep", (uint32_t)pixhighstep); EV("end.pixlowstep", (uint32_t)pixlowstep);
        EV("end.didsolidcol", didsolidcol); EV("end.rw_stopx", (uint16_t)rw_stopx);
        for (int x = 0; x < VIEWWINDOWWIDTH; x++){
            char b[48];
            snprintf(b, sizeof b, "end.floorclip[%d]", x); EV(b, (uint16_t)floorclip[x]);
            snprintf(b, sizeof b, "end.ceilingclip[%d]", x); EV(b, (uint16_t)ceilingclip[x]);
            snprintf(b, sizeof b, "end.solidcol[%d]", x); EV(b, solidcol[x]);
            snprintf(b, sizeof b, "end.maskedtexturecol[%d]", x); EV(b, (uint16_t)masked[x]);
        }
        total += trace_n; tracing = 0;
        if (trace_sc < 0) printf("%d %u %016llx\n", sc, trace_n, (unsigned long long)trace_hash);
    }
    fprintf(stderr, "events %llu\n", total);
    return 0;
}
'''


def build(tmp, name, defs, opt, std, legacy):
    c = tmp / (name + '.c')
    c.write_text('#include <stdlib.h>\n' + PRELUDE + tan + '\n' + seg + '\n#include <stdlib.h>\n' + MAIN)
    exe = tmp / name
    flags = ['-O%s' % opt, '-w'] + (['-std=%s' % std] if std else [])
    flags += ['-DLEGACY_UNINIT_HASH'] if legacy else ['-ftrivial-auto-var-init=zero']
    subprocess.run(['gcc', *flags, *defs, str(c), '-o', str(exe)], check=True)
    return exe


def mutants(seg_text):
    """Deliberate one-token breakages of the real function text; each must be detected."""
    out = []
    for label, old, new in (
        ('yl off by one', 'yl = ', 'yl = 1 + '),
        ('floorclip not updated', 'floorclip[rw_x]', 'floorclip[0]'),
        ('scale step skipped', 'rw_scale += rw_scalestep', 'rw_scale += 0'),
        ('top step skipped', 'topfrac += topstep', 'topfrac += 0'),
        ('bottom step skipped', 'bottomfrac += bottomstep', 'bottomfrac += 0'),
    ):
        if old in seg_text:
            out.append((label, seg_text.replace(old, new, 1)))
    return out


def first_difference(exes, ctl, name, sc):
    """Replay scenario sc with a full event trace for control and variant; print the first concrete difference."""
    a = subprocess.run([str(exes[ctl]), '20000', str(sc)], capture_output=True, text=True, check=True).stdout.splitlines()
    b = subprocess.run([str(exes[name]), '20000', str(sc)], capture_output=True, text=True, check=True).stdout.splitlines()
    inputs = [l for l in a if not l.startswith('ev ')]
    ea = [l for l in a if l.startswith('ev ')]; eb = [l for l in b if l.startswith('ev ')]
    print('  scenario %d inputs:' % sc)
    for l in inputs: print('    ' + l.strip())
    print('  events: control %d, %s %d' % (len(ea), name, len(eb)))
    for i, (x, y) in enumerate(zip(ea, eb)):
        if x != y:
            print('  FIRST DIFFERENT EVENT #%d: control `%s`  vs  %s `%s`' % (i + 1, x[3:], name, y[3:]))
            print('  preceding events (control):')
            for l in ea[max(0, i - 6):i]: print('    ' + l[3:])
            ev = x.split()[2]
            if 'UNREAD' in ev:
                print('  => the routine does not read this field: uninitialised stack garbage in the harness, not a renderer difference')
            return
    if len(ea) != len(eb):
        print('  event counts differ (control %d vs %d); first extra event: %s' % (len(ea), len(eb), (ea[len(eb):] or eb[len(ea):])[0][3:]))


def main():
    args = sys.argv[1:]
    legacy = '--legacy' in args
    opt = args[args.index('--opt') + 1] if '--opt' in args else '1'
    std = args[args.index('--std') + 1] if '--std' in args else ''
    rest = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--opt', '--std'))]
    n = rest[0] if rest else '20000'
    variants = [('control', []), ('a1', ['-DDOOM_R21_SEGLOOP_LOCALS']), ('a2', ['-DDOOM_R70A_INVARIANTS']),
                ('a1a2', ['-DDOOM_R21_SEGLOOP_LOCALS', '-DDOOM_R70A_INVARIANTS'])]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); out, exes = {}, {}
        print('gcc: ' + subprocess.run(['gcc', '--version'], capture_output=True, text=True).stdout.splitlines()[0] +
              '  opt=-O%s std=%s mode=%s' % (opt, std or 'default', 'LEGACY (hash unread fields, no zero-init)' if legacy else 'strict'))
        for name, defs in variants:
            exes[name] = build(d, name, defs, opt, std, legacy)
            r = subprocess.run([str(exes[name]), n], capture_output=True, text=True, check=True)
            out[name] = r.stdout
            print('%-8s %s' % (name, r.stderr.strip()))
        ok = True
        for name in ('a1', 'a2', 'a1a2'):
            same = out[name] == out['control']
            ok &= same
            print('%-8s %s control over %s scenarios' % (name, 'IDENTICAL to' if same else 'DIFFERS from', n))
            if not same:
                for k, (x, y) in enumerate(zip(out['control'].splitlines(), out[name].splitlines())):
                    if x != y:
                        print('  first differing scenario %d: control %s / %s %s' % (k, x, name, y))
                        first_difference(exes, 'control', name, k)
                        break
        # sensitivity: the strict comparison must catch deliberate breakages of the real function text
        global seg
        real = seg; caught = 0; tried = 0
        for label, text in mutants(real):
            seg = text
            try:
                m = build(d, 'mut%d' % tried, [], opt, std, legacy)
            except subprocess.CalledProcessError:
                continue
            tried += 1
            r = subprocess.run([str(m), '3000'], capture_output=True, text=True).stdout
            hit = r != out['control'][:0] + subprocess.run([str(exes['control']), '3000'], capture_output=True, text=True).stdout
            caught += hit
            print('mutant %-22s %s' % (label, 'detected' if hit else 'NOT DETECTED'))
        seg = real
        if tried and caught != tried:
            print('FAIL: harness is not sensitive enough'); ok = False
        sys.exit(0 if ok else 1)


main()
