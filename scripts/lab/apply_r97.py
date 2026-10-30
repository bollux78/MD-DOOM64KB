#!/usr/bin/env python3
"""R97 (Claudio) after apply_r96.py: the p=0 Shadow pass (R92_ShadowPass) in hand-written asm.
Same table, same rectangle (r92_rect snapshot shared with the DMA), same words written.
p>0 (damage/pickup palettes) keeps the C R79 fallback."""
from pathlib import Path
import os, shutil
name = os.environ.get('R97_NAME', 'shasm')

def patch(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:90], c); p.write_text(s.replace(a, b))

shutil.copyfile('scripts/lab/r97/r97_shadow.s', 'src/r97_shadow.s')
patch('src/r92_shadow.inc', '''    const uint16_t maps[2][2][256],const uint16_t costs[2][2][256],uint8_t palette)
{
''', '''    const uint16_t maps[2][2][256],const uint16_t costs[2][2][256],uint8_t palette)
{
#if defined(__m68k__)
    /* Host regression tests compile this file natively: they keep the C path below. */
    if(!palette){
        if(r92_rect.y1>r92_rect.y0 && r92_rect.x1>r92_rect.x0){
            register uint16_t *a0 __asm__("a0")=pixels+(uint16_t)r92_rect.y0*76u+r92_rect.x0;
            register const uint32_t *a1 __asm__("a1")=table;
            register uint32_t d6 __asm__("d6")=(uint16_t)(r92_rect.y1-r92_rect.y0);
            register uint32_t d5 __asm__("d5")=(uint16_t)(r92_rect.x1-r92_rect.x0);
            __asm__ volatile("jsr R97_ShadowJoint":"+a"(a0),"+d"(d6),"+d"(d5):"a"(a1):"d0","d1","d7","a2","cc","memory");
        }
        return;
    }
#endif
''')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r96-'" in s
p.write_text(s.replace("'r96-'", "'r97-'").replace("('wall', 1)", repr((name, 1))))
print('R97 shadow pass asm; ROM name r97-%s' % name)
