"""Install the raw BG benchmark in the patched R128 source tree."""
from pathlib import Path
import sys


def edit(path, pairs):
    source = path.read_text()
    for before, after in pairs:
        if source.count(before) != 1:
            raise SystemExit(f"Raw BG anchor changed in {path}: {before!r}")
        source = source.replace(before, after)
    path.write_text(source)


mode = sys.argv[1]
if mode not in ("raw", "cache"):
    raise SystemExit(f"Unknown raw BG mode: {mode}")
path = Path("scripts/lab/r128-shareware/raw-bg.inc")
Path("src/r128_raw_bg.inc").write_text(
    f"#define R128_RAW_CACHE {int(mode == 'cache')}\n" + path.read_text()
)
edit(Path("src/r22_video.inc"), (
    ('#include "r92_shadow.inc"\n', '#include "r92_shadow.inc"\n#include "r128_raw_bg.inc"\n'),
    ('    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;\n#if defined(DOOM_R47_PLANE_PAIR)\n',
     '    volatile uint16_t *ctrl=(volatile uint16_t*)0xC00004;\n'
     '    if (raw_pending) R128_RawPresent(ctrl);\n    else {\n#if defined(DOOM_R47_PLANE_PAIR)\n'),
    ('    if(!bus)Z80_releaseBus();\n', '    }\n    if(!bus)Z80_releaseBus();\n'),
    ('r22_ready=0;r22_newpal=100;', 'r22_ready=0;raw_pending=0;r22_newpal=100;'),
    ('    const uint8_t r115_want=(uint8_t)(r115_fb2 && _g_gamestate==GS_LEVEL',
     '    R128_RawBegin();\n'
     '    const uint8_t r115_want=(uint8_t)(r115_fb2 && !raw_active && _g_gamestate==GS_LEVEL'),
    ('    r115_show=r115_draw;\n    __asm__ volatile',
     '    if (raw_active && _g_gamestate == GS_LEVEL) R128_RawPrepare();\n'
     '    r115_show=r115_draw;\n    __asm__ volatile'),
    ('    r22_front=0;r22_ready=0;', '    r22_front=0;r22_ready=0;raw_active=0;raw_pending=0;'),
))
edit(Path("src/r22_benchmark.inc"), (
    ('volatile uint32_t r128_ab_result[6]', 'volatile uint32_t r128_ab_result[8]'),
    ('    r128_ab_result[0] = 0x52414231u;',
     '    extern uint32_t R128_RawUploads(void), R128_RawFrames(void);\n'
     '    r128_ab_result[6] = R128_RawUploads();\n'
     '    r128_ab_result[7] = R128_RawFrames();\n'
     '    r128_ab_result[0] = 0x52414232u;'),
))
