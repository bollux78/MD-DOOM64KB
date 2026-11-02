#!/usr/bin/env python3
"""R112 onemul (after the R107 direct chain): one multiply instead of two in the column prologues.

R_DrawColumnSprite and R42_DrawPackedWall computed the start phase as
  f = (texturemid>>7) + (y0-CENTERY)*fracstep;  f += (first-y0)*fracstep;
which equals (texturemid>>7) + (first-CENTERY)*fracstep modulo 2^16 (exact integer identity,
|first-CENTERY| <= 44). One MULS per sprite / R42 wall column instead of two. Identical pixels.
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


V = 'src/r22_video.inc'
rep(V, '''    uint16_t frac=(uint16_t)((v->texturemid>>7)+(y0-CENTERY)*v->fracstep);
    frac=(uint16_t)(frac+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)v->fracstep));''',
    '''    uint16_t frac=(uint16_t)((v->texturemid>>7)+(int16_t)(first-CENTERY)*v->fracstep);''')
rep(V, '''    uint16_t f=(uint16_t)((v->texturemid>>7)+(y0-CENTERY)*v->fracstep);
    f=(uint16_t)(f+(uint16_t)((uint32_t)(uint16_t)(first-y0)*(uint32_t)v->fracstep));''',
    '''    uint16_t f=(uint16_t)((v->texturemid>>7)+(int16_t)(first-CENTERY)*v->fracstep);''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r107-'" in s and "('direct', 1)" in s
p.write_text(s.replace("'r107-'", "'r112-'").replace("('direct', 1)", "('onemul', 1)"))
print('R112 onemul')
