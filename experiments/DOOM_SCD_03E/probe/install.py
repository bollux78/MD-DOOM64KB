"""Install the optional Sega CD world rasterizer into a disposable R128 build checkout."""
from pathlib import Path
import shutil
import subprocess

here = Path(__file__).resolve().parent
tools = Path.home() / "mars/m68k-elf/bin"
transport = here.parents[1] / "DOOM_SCD_Bench03D_Transport" / "tools"
subprocess.run([tools / "m68k-elf-as", "-m68000", here / "sub.s", "-o", "scd-sub.o"], check=True)
subprocess.run([tools / "m68k-elf-gcc", "-m68000", "-O2", "-fomit-frame-pointer",
                "-ffreestanding", "-fno-builtin", "-Isrc", "-c",
                here / "sub_render.c", "-o", "scd-render.o"], check=True)
subprocess.run([tools / "m68k-elf-as", "-m68000", "src/r60_pair_wall.s",
                "-o", "scd-column.o"], check=True)
subprocess.run([tools / "m68k-elf-ld", "-Ttext=0", "-e", "0", "-o", "scd-sub.elf",
                "scd-sub.o", "scd-render.o", "scd-column.o"], check=True)
subprocess.run([tools / "m68k-elf-objcopy", "-O", "binary", "scd-sub.elf", "scd-sub.bin"], check=True)
subprocess.run(["python3", transport / "make_sub_header.py", "scd-sub.bin", "src/scd_probe_sub.h"], check=True)
for name in ("scd_probe.c", "scd_probe.h", "packet.h"):
    shutil.copyfile(here / name, Path("src") / name)


def replace(path, old, new):
    path = Path(path)
    content = path.read_text()
    assert content.count(old) == 1, (path, old)
    path.write_text(content.replace(old, new))


replace("src/i_genesis.c", "\tD_DoomMain(argc, argv);",
        "\tSCD_Probe();\n\tD_DoomMain(argc, argv);")
replace("src/i_genesis.c", '#include "d_main.h"',
        '#include "d_main.h"\n#include "scd_probe.h"')
replace("src/d_main.c", '#include "d_main.h"',
        '#include "d_main.h"\n#include "scd_probe.h"\n#include "i_vtext.h"')
replace("src/d_main.c", "\tV_DrawRawFullScreen(titlepicnum);",
        '\tV_DrawRawFullScreen(titlepicnum);\n'
        '\tV_DrawString(1, 1, 12, scd_available ? "SEGA CD: ON" : "SEGA CD: OFF");')

draw = "src/r_draw.c"
video = "src/r22_video.inc"
replace(draw, 'static inline __attribute__((always_inline)) void R95_Fill',
        '#include "scd_probe.h"\n'
        'static inline __attribute__((always_inline)) void R95_Fill')
replace(draw, '    if (count >= 2) { R113_WallDraw',
        '    if (scd_available && SCD_Column(fb, dst, v->source, lut, f, v->fracstep, count, yl & 1)) return;\n'
        '    if (count >= 2) { R113_WallDraw')
start = '    R_SetupFrame (player);'
end = '    R_RenderBSPNode (numnodes-1);'
path = Path(draw)
s = path.read_text()
assert s.count(start) == s.count(end) == 1
a, b = s.index(start), s.index(end) + len(end)
world = s[a:b]
# Keep preprocessor directives at the left margin.
world = '\n'.join('    ' + line if line and not line.startswith('#') else line
                  for line in world.splitlines())
path.write_text(s[:a] + '    do\n    {\n        SCD_BeginWorld();\n' + world +
                '\n    } while (!SCD_EndWorld());' + s[b:])

replace(video, 'void R_DrawColumnSprite(const draw_column_vars_t *v) {',
        '#include "scd_probe.h"\n'
        'uint8_t *SCD_DrawBuffer(void) { return r115_draw; }\n'
        'void SCD_LutBases(const uint8_t **base) {\n'
        '    _Static_assert(R52_COLORMAP_BYTES == 34u * 256u, "Sega CD LUT layout");\n'
        '    base[0] = R59_CURRENT.comp_even[0];\n'
        '    base[1] = R59_CURRENT.comp_odd[0];\n'
        '}\n'
        'void R_DrawColumnSprite(const draw_column_vars_t *v) {')
