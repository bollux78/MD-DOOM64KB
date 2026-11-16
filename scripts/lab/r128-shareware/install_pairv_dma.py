"""Install the opt-in exact Pair-V DMA row reuse after the R128 overlays."""
from pathlib import Path


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise SystemExit(f"Pair-V DMA reuse anchor changed: {before!r}")
    return source.replace(before, after)


video = Path("src/r22_video.inc")
source = video.read_text()
source = replace_once(
    source,
    "static volatile uint16_t r22_ready;",
    "static volatile uint16_t r22_ready;\n"
    "enum { R128_BG_INVALID, R128_BG_SUBMITTED, R128_BG_PRESENTED };\n"
    "static volatile uint8_t r128_bg_history;\n"
    "static uint32_t r128_skip_a, r128_skip_b;",
)

# Clear the comparison history when code outside the normal DMA path changes
# the tilemaps, the saved buffer, or ownership of the R115 buffers.
invalidations = (
    "if(desired==r57_h32_active)return;",
    "static void R57_ClearBorder(void){",
    "static void R22_ClearOverlay(void){\n    R20_StopVideo();",
    "void I_R21_TextScreen(void)\n{",
    "static void R47_ClearPairBuffer(void)\n{",
    "r22_front=0;r22_ready=0;",
    "void R115_LevelEnd(void){\n    if(!r115_fb2 && !r115_db)return;\n    R20_StopVideo();",
)
for anchor in invalidations:
    source = replace_once(source, anchor, anchor + "\n    r128_bg_history = R128_BG_INVALID;")
source = replace_once(source, "r22_ready=0;r22_newpal=100;",
                      "r128_bg_history=R128_BG_INVALID;r22_ready=0;r22_newpal=100;")

source = replace_once(source, "void I_FinishUpdate(void){",
                      '#include "r128_bg_dma.inc"\nvoid I_FinishUpdate(void){\n'
                      '    if (_g_gamestate != GS_LEVEL || _g_menuactive)\n'
                      '        r128_bg_history = R128_BG_INVALID;')
source = replace_once(source, "    r115_show=r115_draw;\n    __asm__ volatile",
                      "    R128_PrepareBgDma();\n    r115_show=r115_draw;\n    __asm__ volatile")

start = "    for(uint16_t y=first_row;y<end_row;y++,srca+=76,srcb+=76,dsta+=128,dstb+=128){\n"
end = "\n#else\n    #if defined(DOOM_R22_SOLID_TILES)"
if source.count(start) != 1:
    raise SystemExit("Pair-V VBlank row loop changed")
prefix, tail = source.split(start)
loop, suffix = tail.split(end, 1)
plane_a, plane_b = loop.split("        if(!r22_overlay_dirty){\n")
plane_b = replace_once(plane_b, "            a=", "            uint32_t a=")
plane_b = replace_once(plane_b, "            command=", "            volatile uint32_t command=")
plane_b = replace_once(plane_b, "            words=", "            volatile uint16_t *words=")
loop = (
    "        if (!(skip_a & 1u)) {\n"
    + "".join("    " + line for line in plane_a.splitlines(keepends=True))
    + "        }\n"
    + "        if (!(skip_b & 1u) && !r22_overlay_dirty) {\n"
    + plane_b
)
start = start.rstrip("\n").removesuffix("){") + ",skip_a>>=1,skip_b>>=1){\n"
source = (prefix + "    const bool reuse = r128_bg_history == R128_BG_SUBMITTED;\n"
          + "    uint32_t skip_a = reuse ? r128_skip_a : 0;\n"
          + "    uint32_t skip_b = reuse ? r128_skip_b : 0;\n"
          + start + loop + end + suffix)
source = replace_once(
    source, '    __asm__ volatile("":::"memory");r22_ready=0;\n}',
    '    if (r128_bg_history == R128_BG_SUBMITTED)\n'
    '        r128_bg_history = R128_BG_PRESENTED;\n'
    '    __asm__ volatile("":::"memory");r22_ready=0;\n}',
)

shadow = Path("src/r92_shadow.inc")
shadow.write_text(replace_once(shadow.read_text(), "    R20_StopVideo();on=(on!=0);",
                               "    R20_StopVideo();on=(on!=0);\n"
                               "    r128_bg_history = R128_BG_INVALID;"))
video.write_text(source)
Path("src/r128_bg_dma.inc").write_text(
    Path("scripts/lab/r128-shareware/pairv-dma.inc").read_text()
)
