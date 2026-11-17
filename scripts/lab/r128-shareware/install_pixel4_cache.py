"""Use the original R22 palette in the playable R128 cached tile renderer."""
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from convert_r24_episode import read_wad

video = Path("src/r22_video.inc")
source = video.read_text()

def edit(before, after):
    global source
    if source.count(before) != 1:
        raise SystemExit(f"Pixel4 cache anchor changed: {before!r}")
    source = source.replace(before, after)

palette = Path("src/r22_palette.h")
quantize = list(map(int, re.search(r"r22_color\[256\]=\{(.*?)\}", palette.read_text()).group(1).split(",")))
wad = dict(read_wad(Path("scripts/doom64.wad").read_bytes(), True))
colormap = wad["COLORMAP"]
if len(quantize) != 256 or len(colormap) != 8704:
    raise SystemExit("Invalid Pixel4 palette or R113 colormap size")
composed = [quantize[c] for c in colormap]
# R113's assembly reads the shifted twin exactly 8,704 bytes after the
# normal table. Both parity lookups point to the same Pixel4 pair of tables.
packed = composed + [c << 4 for c in composed]
with Path("src/r128_pixel4_comp.h").open("w") as out:
    out.write(f"\nstatic const uint8_t r128_pixel4_comp[{len(packed)}] = {{\n")
    for i in range(0, len(packed), 32):
        out.write(",".join(str(c) for c in packed[i:i + 32]) + ",\n")
    out.write("};\n")

edit('#include "r22_maps.h"', '#include "r22_maps.h"\n#include "r128_pixel4_comp.h"')

# Keep the existing optimized sampling and geometry, but quantize from
# original Doom palette indices, before the tile assembly stage.
source = re.sub(r'R59_CURRENT\.(?:wall|flat)_(?:even|odd)', 'r22_color', source)
source = re.sub(r'R59_CURRENT\.comp_(?:even|odd)\[0\]', 'r128_pixel4_comp', source)
source = source.replace('PAL_setColors(0,R79_PAL0[(uint8_t)p],16,DMA);',
                        'PAL_setColors(0,r22_cram[(uint8_t)p],16,DMA);')
source = source.replace('PAL_setColors(0,R79_PAL0[r77_last_palette],16,CPU);',
                        'PAL_setColors(0,r22_cram[r77_last_palette],16,CPU);')
edit('    if(_g_gamestate==GS_LEVEL && !R76_InGameMenu() && R92_ShadowOn()){',
     '    if(_g_gamestate!=GS_LEVEL && R92_ShadowOn()){')
edit('#include "r92_shadow.inc"\n', '#include "r92_shadow.inc"\n#include "r128_pixel4_play.inc"\n')
edit('    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;\n#if defined(DOOM_R47_PLANE_PAIR)\n',
     '    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;\n'
     '    if (raw_active) { if (raw_pending) R128_RawPresent(ctrl); }\n'
     '    else {\n#if defined(DOOM_R47_PLANE_PAIR)\n')
edit('    if(!bus)Z80_releaseBus();\n', '    }\n    if(!bus)Z80_releaseBus();\n')
edit('r22_ready=0;r22_newpal=100;', 'r22_ready=0;raw_pending=0;r22_newpal=100;')
edit('    const uint8_t r115_want=(uint8_t)(r115_fb2 && _g_gamestate==GS_LEVEL',
     '    R128_RawBegin();\n    const uint8_t r115_want=(uint8_t)(!raw_active && r115_fb2 && _g_gamestate==GS_LEVEL')
edit('    r115_show=r115_draw;\n    __asm__ volatile',
     '    if (raw_active && !_g_menuactive && !r22_overlay_dirty) R128_RawPrepare();\n'
     '    r115_show=r115_draw;\n    __asm__ volatile')
edit('    r22_front=0;r22_ready=0;', '    r22_front=0;r22_ready=0;raw_active=0;raw_pending=0;')
edit('    const uint32_t need=(uint32_t)R22_FB_BYTES+16u;\n'
     '    r115_fb2=0;\n    if(R115_ZoneLargest()>=need+64u && R115_ZoneTotal()>=need+5632u)\n'
     '        r115_fb2=(uint8_t*)Z_CallocLevel(R22_FB_BYTES);',
     '    r115_fb2=(uint8_t*)Z_CallocLevel(sizeof(R128RawWork));')
video.write_text(source)

# This legacy renderer has a fixed viewport and no Pair-V-specific options.
menu = Path("src/m_text.c")
lines = menu.read_text().splitlines(keepends=True)
disabled = re.compile(r'\b(?:shadow_mode|video_mode|h_crop|v_crop|color_mode)\b')
entry = re.compile(r'"(?:Shadow|Video mode|H crop|V crop|Color mode):"')
menu.write_text("".join(line for line in lines if not disabled.search(line) and not entry.search(line)))

# The stock test asserts the presence of the Pair-V color tables in the
# renderer. It stays active for stock builds; this one uses R22 tables.
builder = Path("scripts/lab/build_r35_linear.fish")
s = builder.read_text()
anchor = 'python3 scripts/lab/test_r59_colorview.py; or exit 1'
if s.count(anchor) != 1:
    raise SystemExit("Pixel4 expected the original Pair-V color test")
builder.write_text(s.replace(anchor, '''
            if not set -q R128_PIXEL4_PLAY
                python3 scripts/lab/test_r59_colorview.py; or exit 1
            end'''))
