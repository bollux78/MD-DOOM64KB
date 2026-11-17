"""Keep R128 gameplay and UI, with the original R22 packed pixel kernels."""
from pathlib import Path
import re

video = Path("src/r22_video.inc")
s = video.read_text()

def edit(a, b):
    global s
    if s.count(a) != 1:
        raise SystemExit(f"Pixel4 anchor changed: {a!r}")
    s = s.replace(a, b)

# These four loops and the safety border reproduce the original R22 C backend.
start = s.index('static inline void R22_Plot(')
end = s.index('void I_ReloadPalette(', start)
s = s[:start] + Path('scripts/lab/r128-shareware/pixel4-raster.inc').read_text() + '\n' + s[end:]
edit('    PAL_setColors(0,R79_PAL0[(uint8_t)p],16,DMA);',
     '    PAL_setColors(0,r22_cram[(uint8_t)p],16,DMA);')
edit('PAL_setColors(0,R79_PAL0[r77_last_palette],16,CPU);',
     'PAL_setColors(0,r22_cram[r77_last_palette],16,CPU);')
edit('    if(_g_gamestate==GS_LEVEL && !R76_InGameMenu() && R92_ShadowOn()){',
     '    if(_g_gamestate!=GS_LEVEL && R92_ShadowOn()){')
edit('#include "r92_shadow.inc"\n', '#include "r92_shadow.inc"\n#include "r128_pixel4_present.inc"\n')
edit('    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;\n#if defined(DOOM_R47_PLANE_PAIR)\n',
     '    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;\n'
     '    if (pixel4_active) { if (pixel4_pending) Pixel4_Present(ctrl); }\n'
     '    else {\n#if defined(DOOM_R47_PLANE_PAIR)\n')
edit('    if(!bus)Z80_releaseBus();\n', '    }\n    if(!bus)Z80_releaseBus();\n')
edit('r22_ready=0;r22_newpal=100;', 'r22_ready=0;pixel4_pending=0;r22_newpal=100;')
edit('    const uint8_t r115_want=(uint8_t)(r115_fb2 && _g_gamestate==GS_LEVEL',
     '    Pixel4_Begin();\n    const uint8_t r115_want=(uint8_t)(!pixel4_active && r115_fb2 && _g_gamestate==GS_LEVEL')
edit('    r115_show=r115_draw;\n    __asm__ volatile',
     '    if (pixel4_active && !_g_menuactive && !r22_overlay_dirty) Pixel4_Prepare();\n'
     '    r115_show=r115_draw;\n    __asm__ volatile')
edit('    r22_front=0;r22_ready=0;', '    r22_front=0;r22_ready=0;pixel4_active=0;pixel4_pending=0;')
edit('    const uint32_t need=(uint32_t)R22_FB_BYTES+16u;\n'
     '    r115_fb2=0;\n    if(R115_ZoneLargest()>=need+64u && R115_ZoneTotal()>=need+5632u)\n'
     '        r115_fb2=(uint8_t*)Z_CallocLevel(R22_FB_BYTES);',
     '    r115_fb2=(uint8_t*)Z_CallocLevel(sizeof(Pixel4Cache));')
edit('static void R47_ClearPairBuffer(void)\n{',
     'static void R47_ClearPairBuffer(void)\n{\n'
     '    if (_g_gamestate == GS_LEVEL) { memset(r22_fb.pixels, 0, 38u * 44u); return; }')
s = '#define HUDW_VRAM_BASE 816u\n' + s
video.write_text(s)
Path('src/r128_pixel4_present.inc').write_text(
    Path('scripts/lab/r128-shareware/pixel4-present.inc').read_text())
native = Path("src/r35_native4.inc")
t = native.read_text()
if t.count('R79_PAL0[0]') != 1 or t.count('    R47_ClearPairBuffer();') != 1:
    raise SystemExit("Native-art Pixel4 restore anchors changed")
native.write_text(t.replace('R79_PAL0[0]', 'r22_cram[0]')
                   .replace('    R47_ClearPairBuffer();',
                            '    if (_g_gamestate != GS_LEVEL) R47_ClearPairBuffer();'))

# Keep the settings for gameplay, audio, and gamma. The original viewport
# and 16-color palette are fixed, with no Pair-V shadow or palette controls.
menu = Path("src/m_text.c")
disabled = re.compile(r'\b(?:shadow_mode|video_mode|h_crop|v_crop|color_mode)\b')
entry = re.compile(r'"(?:Shadow|Video mode|H crop|V crop|Color mode):"')
menu.write_text("".join(line for line in menu.read_text().splitlines(keepends=True)
                        if not disabled.search(line) and not entry.search(line)))
builder = Path("scripts/lab/build_r35_linear.fish")
t = builder.read_text()
anchor = 'python3 scripts/lab/test_r59_colorview.py; or exit 1'
if t.count(anchor) != 1:
    raise SystemExit("Pixel4 expected the Pair-V color source test")
builder.write_text(t.replace(anchor, '''
            if not set -q R128_PIXEL4_ORIGINAL
                python3 scripts/lab/test_r59_colorview.py; or exit 1
            end'''))

link_check = Path("scripts/lab/build_r71a12mul_hud.py")
t = link_check.read_text()
anchor = "        assert 'R60_WallColumn' in nm, ('R60 linked kernel mismatch', name)"
if t.count(anchor) != 1:
    raise SystemExit("Pixel4 linker check anchor changed")
link_check.write_text(t.replace(anchor, """        if os.environ.get("R128_PIXEL4_ORIGINAL") == "1":
            assert 'pixel4_overflows' in nm, ('original Pixel4 backend missing', name)
            assert 'R113_WallColumn' not in nm, ('Pair-V wall kernel linked', name)
        else:
""" + "    " + anchor))

segs = Path("src/r_draw.c")
t = segs.read_text()
a = t.index("static inline __attribute__((always_inline)) void R96_WallDraw(")
b = t.index("#define R20_WALL_DRAW(v) R96_WallDraw(v)", a)
segs.write_text(t[:a] + """static inline void R96_WallDraw(const draw_column_vars_t *v)
{
    R_DrawColumnWall(v);
}
""" + t[b:])
Path("src/r113_hilut_wall.s").unlink()
