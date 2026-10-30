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
assert mode == 'f1'
name = os.environ.get('R100_NAME', 'f1diag' if diag else 'f1')
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
new = '    if (midtexture)\n    {\n' + spec + '\n    }\n    else\n    {\n' + loop_g + '\n    }'
s = s[:a] + new + s[j + 1:]
if diag:
    s = s.replace('static uint8_t *r96_fb;', '''/* R100 diagnostic counters (diagnostic build only). */
volatile struct { uint32_t cols, mid_cols, mid_wall, r60, r96_single, r96_fallback, r96_empty; } r100_diag;
static uint8_t *r96_fb;''', 1)
    s = s.replace('    if (!fb || v->colormap != r96_cmap) { R_DrawColumnWall(v); return; }',
                  '    if (!fb || v->colormap != r96_cmap) { r100_diag.r96_fallback++; R_DrawColumnWall(v); return; }', 1)
    s = s.replace('    if (yh < yl) return;\n    const uint16_t f =', '    if (yh < yl) { r100_diag.r96_empty++; return; }\n    const uint16_t f =', 1)
    s = s.replace('    if (count >= 2) { R60_WallDraw(', '    if (count >= 2) { r100_diag.r60++; R60_WallDraw(', 1)
    s = s.replace('    const uint8_t c = (uint8_t)(lut[v->source[f >> 9]] & 15u);', '    r100_diag.r96_single++;\n    const uint8_t c = (uint8_t)(lut[v->source[f >> 9]] & 15u);', 1)
    for k in ('r100_diag.r96_fallback++', 'r100_diag.r96_empty++', 'r100_diag.r60++', 'r100_diag.r96_single++'):
        assert s.count(k) == 1, k
Path(D).write_text(s)
p = Path('scripts/lab/build_r71a12mul_hud.py'); t = p.read_text()
assert "'r98-'" in t and "('sprmul', 1)" in t
p.write_text(t.replace("'r98-'", "'r100-'").replace("('sprmul', 1)", repr((name, 1))))
print('R100', mode, 'diag' if diag else 'release', 'name r100-' + name)
