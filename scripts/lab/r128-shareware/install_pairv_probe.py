"""Install the opt-in Pair-V row diagnostic after the R128 overlays."""
from pathlib import Path

video = Path("src/r22_video.inc")
source = video.read_text()
edits = (
    ("static volatile uint16_t r22_ready;",
     "static volatile uint16_t r22_ready;\nstatic volatile bool r128_bg_presented, r128_bg_sampled;"),
    ('    __asm__ volatile("":::"memory");r22_ready=0;\n}',
     '    r128_bg_presented = r128_bg_sampled;\n'
     '    __asm__ volatile("":::"memory");r22_ready=0;\n}'),
    ('void I_FinishUpdate(void){',
     '#include "r128_bg_probe.inc"\nvoid I_FinishUpdate(void){\n'
     '    if (_g_gamestate != GS_LEVEL) R128_BGProbe();'),
    ('    r115_show=r115_draw;\n    __asm__ volatile("":::"memory");r22_ready=1;',
     '    r115_show=r115_draw;\n    if (_g_gamestate == GS_LEVEL) R128_BGProbe();\n'
     '    __asm__ volatile("":::"memory");r22_ready=1;'),
    ('    r22_front=0;r22_ready=0;',
     '    r22_front=0;r22_ready=0;r128_bg_presented=false;'),
)
for before, after in edits:
    if source.count(before) != 1:
        raise SystemExit(f"Pair-V row probe anchor changed: {before!r}")
    source = source.replace(before, after)
video.write_text(source)
Path("src/r128_bg_probe.inc").write_text(
    Path("scripts/lab/r128-shareware/pairv-probe.inc").read_text()
)
