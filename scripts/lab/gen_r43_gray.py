#!/usr/bin/env python3
"""R43: recover neutral PLAYPAL greys lost by the 14-color pixel4 palette.

The 8x8 dither palette is NOT changed. Only pixel4's 3D 16-color palette
and 256-entry Doom-index lookup change. Assets TITLEPIC/WIMAP0/Bayer8,
VDP HUD and sprite source pixels are left intact.

The baseline R22 quantizer had no dark/mid grey steps: PLAYPAL neutral
RGB pixels were frequently quantized onto brown/olive representatives.
We repurpose the duplicate black slot #1 and dark warm slot #4 into
grays and re-quantize source PLAYPAL indices. Chromatic source colors
are matched against the remaining representative colors. 14 screen-flash
subpalettes use the same representative source Doom indices so flashes
remain coherent (including neutral colors).
"""
import re
import runpy
from pathlib import Path

root=Path(__file__).resolve().parents[2]
g=runpy.run_path(str(root/'scripts/genpal.py'))
src=(root/'src/r22_palette.h').read_text()
m1=re.search(r"static const uint8_t r22_color\[256\]=\{(.*?)\};",src,re.S)
m2=re.search(r"static const uint16_t r22_cram\[14\]\[16\]=\{(.*?)\};",src,re.S)
assert m1 and m2, 'R22 baseline palette format unexpectedly changed'
oldlut=[int(x) for x in re.findall(r'\d+',m1.group(1))]
rows=re.findall(r'\{([^{}]+)\}',m2.group(1))
baseline=[[int(x) for x in re.findall(r'\d+',row)] for row in rows]
assert len(oldlut)==256 and len(baseline)==14 and all(len(r)==16 for r in baseline)
pp=g['load_playpal']()
allrgb=[g['decode_subpal'](pp,k) for k in range(14)]
rgb=allrgb[0]

def chroma(c):return max(c)-min(c)
def dist2(a,b):return sum((int(a[k])-int(b[k]))**2 for k in range(3))

# Choose actual Doom source greys, allowing small noise from the original
# palette, rather than inventing static RGB while red-flash subpalettes run.
greys=[i for i,c in enumerate(rgb) if chroma(c)<=20]
assert len(greys)>=8, 'Original PLAYPAL has too few neutral source greys'
targets={1:(36,36,36),4:(72,72,72)}
representative={slot:min(greys,key=lambda i:dist2(rgb[i],target)) for slot,target in targets.items()}
assert len(set(representative.values()))==2
for c in allrgb:
    assert len(c)==256

cram=[list(row) for row in baseline]
for sub in range(14):
    for slot,source in representative.items():
        cram[sub][slot]=g['gen_color'](allrgb[sub][source])
assert cram[0][1]!=cram[0][4]
# The new palette provides a neutral luminosity ramp: black, dark & mid
# gray plus the three original grey reps and bright white.
neutral_slots=(0,1,4,8,11,14,15)
all_disp=[g['gen_to_rgb'](w) for w in cram[0]]
for slot in neutral_slots:
    assert chroma(all_disp[slot])<=40, ('non-neutral gray slot',slot,all_disp[slot])

lookup=[]
old_neutral_as_chroma=0
mapped_neutral=0
for i,c in enumerate(rgb):
    neutral=chroma(c)<=24
    if neutral:
        # Keep dark/medium gray details, e.g. strips and flat sectors,
        # out of the brown/olive palette bins.
        choices=neutral_slots
        if oldlut[i] not in neutral_slots:old_neutral_as_chroma+=1
        mapped_neutral+=1
    else:
        choices=range(16)
    lookup.append(min(choices,key=lambda j:dist2(c,all_disp[j])))
assert all(lookup[i] in neutral_slots for i,c in enumerate(rgb) if chroma(c)<=24)
assert all(0<=idx<16 for idx in lookup)

out=root/'src/r43_gray_palette.h'
out.write_text(
    '/* Generated via scripts/lab/gen_r43_gray.py from PLAYPAL + R22 color. */\n'
    '/* Native pixel4 only; R42 wall ASM & Bayer8 native art unchanged. */\n'
    'static const uint8_t r22_color[256]={' + ','.join(map(str,lookup))+'};\n'
    'static const uint16_t r22_cram[14][16]={\n'
    + ',\n'.join('{'+','.join(map(str,row))+'}' for row in cram)
    + '};\n',
    encoding='utf-8'
)
# Human-readable checks for comparative brightness/footprint and history.
report=(root/'src/r43_gray_palette_report.txt')
report.write_text(
    'R43 4x4 gray palette experiment. Do not edit generated files.\n'
    +f'neutral input PLAYPAL indices: {mapped_neutral}/256\n'
    +f'neutral input indices that formerly used color slots: {old_neutral_as_chroma}\n'
    +f'gray slots (original 0/8/11/14/15 plus new 1/4): {neutral_slots}\n'
    +f'new source Doom index for dark gray: {representative[1]}; '
      f'for medium gray: {representative[4]}\n'
    +f'neutral gray CRAM0: '+','.join(hex(cram[0][x]) for x in neutral_slots)+'\n'
    +f'remapped lookup entries: {sum(a!=b for a,b in zip(oldlut,lookup))}/256\n',
    encoding='utf-8'
)
print(report.read_text())
