#!/usr/bin/env python3
"""R100 (Claudio) after the R98 sprmul chain: F1 = seg-loop specialisation in C.

R100_MODE=f1  The R_RenderSegLoop column loop is generated twice FROM THE SAME SOURCE TEXT at build
              time: a copy where the wall-tier test `if (midtexture)` is the constant 1 (the
              compiler drops the two-sided top/bottom/masked/solidcol branch), selected once
              before the loop when midtexture != 0, and the untouched original loop for every
              other seg. Everything else (flats, sky, clip updates, rounding, stepping, R66 pair
              reuse, fallbacks) is the same text in both copies.
R100_DIAG=1   Diagnostic build only (never delivered): per-COLUMN counters in BSS (28 B) read by
              r100_diag_read.py. Requires R100_MODE=f1.
"""
from pathlib import Path
import os
mode = os.environ.get('R100_MODE', 'f1'); diag = os.environ.get('R100_DIAG') == '1'
assert mode in ('f1', 'f1b', 'f1t')
name = os.environ.get('R100_NAME', mode + ('diag' if diag else ''))
D = 'src/r_draw.c'
s = Path(D).read_text()
assert 'R98 sprmul' in s, 'R98 sprmul chain first'
A = '    for ( ; rw_x < rw_stopx ; rw_x++)\n    {\n        R37_HIT(R37_COLUMNS);'
assert s.count(A) == 1
a = s.index(A); b = s.index('{', a); d = 0
for j in range(b, len(s)):
    if s[j] == '{': d += 1
    elif s[j] == '}':
        d -= 1
        if d == 0: break
loop = s[a:j + 1]
assert s[j + 1:].lstrip().startswith('#if defined(DOOM_R70A_INVARIANTS)\n#undef rw_offset'), 'loop end not where expected'
TIER = '        if (midtexture)\n        {\n\n            dcvars.yl = yl;     // single sided line'
assert loop.count(TIER) == 1
spec = loop.replace(TIER, '        if (1) /* R100 F1: midtexture path, selected before the loop */\n        {\n\n            dcvars.yl = yl;     // single sided line')
if diag:
    spec = spec.replace('        R37_HIT(R37_COLUMNS);', '        R37_HIT(R37_COLUMNS); r100_diag.cols++; r100_diag.mid_cols++;', 1)
    spec = spec.replace('            dcvars.yl = yl;     // single sided line', '            dcvars.yl = yl;     // single sided line\n            if (yl <= yh) r100_diag.mid_wall++;', 1)
    loop_g = loop.replace('        R37_HIT(R37_COLUMNS);', '        R37_HIT(R37_COLUMNS); r100_diag.cols++;', 1)
else:
    loop_g = loop
MASK = '            if (maskedtexture)\n                maskedtexturecol[rw_x] = texturecolumn;'
two = None
if mode == 'f1b':
    # F1b: second generated copy for two-sided segs without a masked mid texture.
    assert loop.count(MASK) == 1
    two = loop.replace(TIER, '        if (0) /* R101 F1b: two-sided, midtexture == 0 */\n        {\n\n            dcvars.yl = yl;     // single sided line')
    two = two.replace(MASK, '            if (0) /* R101 F1b: maskedtexture == 0 */\n                maskedtexturecol[rw_x] = texturecolumn;')
    if diag:
        two = two.replace('        R37_HIT(R37_COLUMNS);', '        R37_HIT(R37_COLUMNS); r100_diag.cols++; r100_diag.two_cols++;', 1)
TOP = '            if (toptexture)\n'
BOT = '            if (bottomtexture)          // bottom wall'
quad = None
if mode == 'f1t':
    # R102 twoface: two-sided, no masked texture, top/bottom presence fixed per generated copy.
    assert loop.count(MASK) == 1 and loop.count(TOP) == 1 and loop.count(BOT) == 1
    base2 = loop.replace(TIER, '        if (0) /* R102: two-sided, midtexture == 0 */\n        {\n\n            dcvars.yl = yl;     // single sided line')
    base2 = base2.replace(MASK, '            if (0) /* R102: maskedtexture == 0 */\n                maskedtexturecol[rw_x] = texturecolumn;')
    quad = {}
    for t in (1, 0):
        for b_ in (1, 0):
            q = base2.replace(TOP, '            if (%d) /* R102: toptexture %s */\n' % (t, '!= 0' if t else '== 0'))
            q = q.replace(BOT, '            if (%d) /* R102: bottomtexture %s */' % (b_, '!= 0' if b_ else '== 0'))
            quad[(t, b_)] = q
if quad is not None:
    new = ('    if (midtexture)\n    {\n' + spec + '\n    }\n    else if (!maskedtexture)\n    {\n'
           '        if (toptexture)\n        {\n            if (bottomtexture)\n            {\n' + quad[(1, 1)] + '\n            }\n            else\n            {\n' + quad[(1, 0)] +
           '\n            }\n        }\n        else\n        {\n            if (bottomtexture)\n            {\n' + quad[(0, 1)] + '\n            }\n            else\n            {\n' + quad[(0, 0)] +
           '\n            }\n        }\n    }\n    else\n    {\n' + loop_g + '\n    }')
elif two is None:
    new = '    if (midtexture)\n    {\n' + spec + '\n    }\n    else\n    {\n' + loop_g + '\n    }'
else:
    new = ('    if (midtexture)\n    {\n' + spec + '\n    }\n    else if (!maskedtexture)\n    {\n' + two +
           '\n    }\n    else\n    {\n' + loop_g + '\n    }')
s = s[:a] + new + s[j + 1:]
if diag:
    s = s.replace('static uint8_t *r96_fb;', '''/* R100 diagnostic counters (diagnostic build only). */
volatile struct { uint32_t cols, mid_cols, mid_wall, r60, r96_single, r96_fallback, r96_empty, two_cols; } r100_diag;
static uint8_t *r96_fb;''', 1)
    s = s.replace('    if (!fb || v->colormap != r96_cmap) { R_DrawColumnWall(v); return; }',
                  '    if (!fb || v->colormap != r96_cmap) { r100_diag.r96_fallback++; R_DrawColumnWall(v); return; }', 1)
    s = s.replace('    if (yh < yl) return;\n    const uint16_t f =', '    if (yh < yl) { r100_diag.r96_empty++; return; }\n    const uint16_t f =', 1)
    s = s.replace('    if (count >= 2) { R60_WallDraw(', '    if (count >= 2) { r100_diag.r60++; R60_WallDraw(', 1)
    s = s.replace('    const uint8_t c = (uint8_t)(lut[v->source[f >> 9]] & 15u);', '    r100_diag.r96_single++;\n    const uint8_t c = (uint8_t)(lut[v->source[f >> 9]] & 15u);', 1)
    for k in ('r100_diag.r96_fallback++', 'r100_diag.r96_empty++', 'r100_diag.r60++', 'r100_diag.r96_single++'):
        assert s.count(k) == 1, k
Path(D).write_text(s)
# R15 source preflight counts the four tangent products of ONE loop body; F1 generates two copies.
t = Path('scripts/lab/test_r15_wallmul.py'); u = t.read_text()
old = 'assert src.count("R15_TAN_PRODUCT(rw_distance, tan)") == 4'
assert u.count(old) == 1
copies = {'f1': 2, 'f1b': 3, 'f1t': 6}[mode]
t.write_text(u.replace(old, 'assert src.count("R15_TAN_PRODUCT(rw_distance, tan)") == %d  # R100/R101: generated loop copies' % (4 * copies)))
p = Path('scripts/lab/build_r71a12mul_hud.py'); t = p.read_text()
assert "'r98-'" in t and "('sprmul', 1)" in t
prefix = os.environ.get('R100_PREFIX', 'r100')
p.write_text(t.replace("'r98-'", "'%s-'" % prefix).replace("('sprmul', 1)", repr((name, 1))))
print('R100', mode, 'diag' if diag else 'release', 'name %s-%s' % (prefix, name))
