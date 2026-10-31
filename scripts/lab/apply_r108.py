#!/usr/bin/env python3
"""R108 walls at half height (after the R107 direct chain). Sprites, HUD, menus untouched.

Data: build step r108_half_walls.py halves every wall patch (P_START..P_END) of the converted WAD
and regenerates the R84 baked composites (64-byte half columns). Runs right after the episode
conversion, so the colour/palette generators keep reading the original patches.
Render: every wall sampler reads half texels:
  - R96 seg walls and R42 (R_DrawColumnWall: other colormaps, sky, masked mid textures):
    asm kernel R108_WallColumn = R60 with row mask 63, fed phase>>1 and step>>1;
    C single-pixel paths sample source[f>>10] (wraps at 64 like the full path wraps at 128);
  - composition: originy>>1 and (height+1)>>1;
  - masked mid textures: post topdelta/length are half units, scaled back by 2 for screen
    placement and texturemid (sprites keep shift 0).
World coordinates (texture heights, offsets, pegging) stay in full units, so size and alignment
on screen are unchanged.
"""
import shutil
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


# Kernel: private copy with mask 63.
k = Path('src/r60_pair_wall.s').read_text()
assert k.count('#127') == 2 and k.count('R60_WallColumn') >= 3
Path('src/r108_half_wall.s').write_text(k.replace('#127', '#63').replace('R60_WallColumn', 'R108_WallColumn'))
h = Path('src/r60_pair_wall.h').read_text()
Path('src/r108_half_wall.h').write_text(h.replace('R60_PAIR_WALL_H', 'R108_HALF_WALL_H').replace('R60_WallDraw', 'R108_WallDraw').replace('R60_WallColumn', 'R108_WallColumn'))

# R96 seg-loop wall path.
D = 'src/r_draw.c'
rep(D, '#include "r60_pair_wall.h"\nstatic uint8_t *r96_fb;', '#include "r60_pair_wall.h"\n#include "r108_half_wall.h"\nstatic uint8_t *r96_fb;')
rep(D, '    if (count >= 2) { R60_WallDraw(dst, v->source, lut, f, v->fracstep, count, (uint16_t)(yl & 1)); return; }\n    const uint8_t c = (uint8_t)(lut[v->source[f >> 9]] & 15u);',
       '    if (count >= 2) { R108_WallDraw(dst, v->source, lut, (uint16_t)(f >> 1), (uint16_t)(v->fracstep >> 1), count, (uint16_t)(yl & 1)); return; }\n    const uint8_t c = (uint8_t)(lut[v->source[f >> 10]] & 15u);')
# Composition at half height.
rep(D, 'R_DrawColumnInCache (patchcol, tmpCache, patch->originy, tex->height);',
       'R_DrawColumnInCache (patchcol, tmpCache, (int16_t)(patch->originy >> 1), (int16_t)((tex->height + 1) >> 1));')
# Masked mid textures: half-unit posts.
rep(D, 'static void R_DrawMaskedColumn(R_DrawColumn_f colfunc, draw_column_vars_t *dcvars, const column_t __far* column)\n{',
       'static uint8_t r108_postshift; /* 1 while drawing half-height wall posts */\nstatic void R_DrawMaskedColumn(R_DrawColumn_f colfunc, draw_column_vars_t *dcvars, const column_t __far* column)\n{')
rep(D, 'const uint16_t r98_td = column->topdelta, r98_ln = column->length;',
       'const uint16_t r98_td = (uint16_t)(column->topdelta << r108_postshift), r98_ln = (uint16_t)(column->length << r108_postshift);')
rep(D, 'dcvars->texturemid = basetexturemid - (((int32_t)column->topdelta)<<FRACBITS);',
       'dcvars->texturemid = basetexturemid - (((int32_t)column->topdelta << r108_postshift)<<FRACBITS);')
rep(D, '\t\t\tR_DrawMaskedColumn(R_DrawColumnWall, &dcvars, column);',
       '\t\t\tr108_postshift = 1;\n\t\t\tR_DrawMaskedColumn(R_DrawColumnWall, &dcvars, column);\n\t\t\tr108_postshift = 0;')

# R42 wall path (R_DrawColumnWall): only inside R42_DrawPackedWall.
V = 'src/r22_video.inc'; s = Path(V).read_text()
a = s.index('static void R42_DrawPackedWall(const draw_column_vars_t *v)')
b = s.index('void R_DrawColumnWall(const draw_column_vars_t *v){R42_DrawPackedWall(v);}', a)
body = s[a:b]
n9 = body.count('source[f>>9]'); assert n9 >= 4, n9
call = 'R60_WallDraw(dst,source,r52map,f,step,count,(uint16_t)(first&1));'
assert body.count(call) == 1
body = body.replace('source[f>>9]', 'source[f>>10]').replace(call, 'R108_WallDraw(dst,source,r52map,(uint16_t)(f>>1),(uint16_t)(step>>1),count,(uint16_t)(first&1));')
s = s[:a] + '#include "r108_half_wall.h"\n' + body + s[b:]
Path(V).write_text(s)

# Build step: halve the wall patches of the converted WAD and regenerate R84.
F = 'scripts/lab/build_r35_linear.fish'
rep(F, '    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1\n    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1\n',
       '    cp /tmp/r23-converted.wad scripts/doom64.wad; or exit 1\n    python3 scripts/lab/r89_align_maps.py scripts/doom64.wad; or exit 1\n'
       '    python3 scripts/lab/r108_half_walls.py scripts/doom64.wad --r84 src/r84_columns.h --report "$dest/r108-$v.json"; or exit 1\n')

p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r107-'" in s and "('direct', 1)" in s
p.write_text(s.replace("'r107-'", "'r108-'").replace("('direct', 1)", "('halfwall', 1)"))
print('R108 half-height walls')
