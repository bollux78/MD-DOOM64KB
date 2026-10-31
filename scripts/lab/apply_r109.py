#!/usr/bin/env python3
"""R109 sprites at half height (after the R107 direct chain; walls stay full height).

Data: build step r109_half_sprites.py halves every sprite patch (S_START..S_END) after the
episode conversion (colour generators keep the original data). Render: R_DrawMaskedColumn scales
half-unit posts back by 2 for screen placement/texturemid while drawing sprites (masked walls keep
shift 0), and R_DrawColumnSprite (sprites, weapon, fuzz) samples half texels: kernel phase/step>>1,
C paths source[frac>>10]. World sizes, offsets and positions are unchanged.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


D = 'src/r_draw.c'
rep(D, 'static void R_DrawMaskedColumn(R_DrawColumn_f colfunc, draw_column_vars_t *dcvars, const column_t __far* column)\n{',
       'static uint8_t r109_postshift; /* 1 while drawing half-height sprite posts */\nstatic void R_DrawMaskedColumn(R_DrawColumn_f colfunc, draw_column_vars_t *dcvars, const column_t __far* column)\n{')
rep(D, 'const uint16_t r98_td = column->topdelta, r98_ln = column->length;',
       'const uint16_t r98_td = (uint16_t)(column->topdelta << r109_postshift), r98_ln = (uint16_t)(column->length << r109_postshift);')
rep(D, 'dcvars->texturemid = basetexturemid - (((int32_t)column->topdelta)<<FRACBITS);',
       'dcvars->texturemid = basetexturemid - (((int32_t)column->topdelta << r109_postshift)<<FRACBITS);')
rep(D, '        R_DrawMaskedColumn(colfunc, &dcvars, column);\n',
       '        r109_postshift = 1;\n        R_DrawMaskedColumn(colfunc, &dcvars, column);\n        r109_postshift = 0;\n')

V = 'src/r22_video.inc'; s = Path(V).read_text()
a = s.index('void R_DrawColumnSprite(const draw_column_vars_t *v) {')
b = s.index('static void R42_DrawPackedWall(const draw_column_vars_t *v)', a)
body = s[a:b]
n = body.count('source[frac>>9]'); assert n >= 8, n
call = 'R60_WallDraw(dst,source,r52map,frac,step,count,(uint16_t)(first&1u));'
assert body.count(call) == 1, body.count(call)
body = body.replace('source[frac>>9]', 'source[frac>>10]').replace(call,
    'R60_WallDraw(dst,source,r52map,(uint16_t)(frac>>1),(uint16_t)(step>>1),count,(uint16_t)(first&1u));')
s = s[:a] + body + s[b:]
Path(V).write_text(s)

# Host regression for the sprite column: the reference samples half texels too.
rep('scripts/lab/test_r22_pixel4.py', '   unsigned c=source[f>>9];if(d.colormap)c=map[c];c&=15;', '   unsigned c=source[f>>10];if(d.colormap)c=map[c];c&=15;')
F = 'scripts/lab/build_r35_linear.fish'
rep(F, '    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1\n    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1\n',
       '    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1\n    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1\n'
       '    python3 scripts/lab/r109_half_sprites.py scripts/doom64.wad --report "$dest/r109-$v.json"; or exit 1\n')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r107-'" in s and "('direct', 1)" in s
p.write_text(s.replace("'r107-'", "'r109-'").replace("('direct', 1)", "('halfsprite', 1)"))
print('R109 half-height sprites')
