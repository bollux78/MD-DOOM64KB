#!/usr/bin/env python3
"""Apply R73 experiment in a disposable runner checkout, never to stable R71.
Three ROMs: solid R53 color, R53 M25 microtiles, R53 M25+flat 2D.
Requires sibling apply_r72_flat2d.py from the experimental branch.
"""
from pathlib import Path
import subprocess,re
subprocess.run(["python3","scripts/lab/apply_r72_flat2d.py"],check=True)
p=Path("src/r22_video.inc")
s=p.read_text()
# Preserve the existing R59 runtime LUT/cache machinery but lock it to mode 0.
# Pair-V tiles gain the R53 M25 4x4 rotating physical-pixel pattern.
old="static inline uint32_t R56_PairRow(uint8_t code,const uint8_t pairs[16][2])"
assert s.count(old)==1
s=s.replace(old,"static inline uint32_t R56_PairRow(uint8_t code,const uint8_t pairs[16][2],uint16_t row)")
old="    return (a<<28)|(b<<24)|(a<<20)|(b<<16);"
assert s.count(old)==1
s=s.replace(old,"""#if defined(DOOM_R73_R53_FIXED)
    uint32_t result=0;
    for(uint16_t x=0;x<4u;x++){
        uint8_t nib=(((x+row)&3u)==0u)?(uint8_t)b:(uint8_t)a;
        result|=(uint32_t)nib<<(28u-4u*x);
    }
    return result;
#else
    (void)row;
    return (a<<28)|(b<<24)|(a<<20)|(b<<16);
#endif""")
for marker in ("R59_CURRENT.pairs_even","R59_CURRENT.pairs_odd","r56_pairs_even","r56_pairs_odd"):
    needle="R56_PairRow((y<4u)?hi:lo,"+marker+");"
    assert s.count(needle)==1,needle
    s=s.replace(needle,"R56_PairRow((y<4u)?hi:lo,"+marker+",y);")
p.write_text(s)
# Disable only the experimental ROM's palette selector; keep view-size menus.
p=Path("src/m_text.c")
s=p.read_text()
needle="#if defined(DOOM_R59_COLOR_VIEW)"
assert s.count(needle)>=3
s=s.replace(needle,"#if defined(DOOM_R59_COLOR_VIEW) && !defined(DOOM_R73_R53_FIXED)")
p.write_text(s)
# R52 palette is generated before R58/R59. Generate R53 M25 companions there,
# then replace only mode 0 after the original R59 six-profile validation passes.
p=Path("scripts/lab/build_r35_linear.fish")
s=p.read_text()
needle="            python3 scripts/lab/test_r59_colorview.py; or exit 1"
assert s.count(needle)==1
s=s.replace(needle,needle+"""
            if set -q DOOM_R73_STYLE
                python3 scripts/lab/gen_r53_micro.py --repo . --out src --profile "$DOOM_R52_AB_PROFILE" --ratio 25; or exit 1
                python3 scripts/lab/gen_r73_r53_fixed.py "$DOOM_R73_STYLE"; or exit 1
            end""")
needle="        set defs $defs '-DDOOM_R71_MUL_ASM'"
assert s.count(needle)==1
s=s.replace(needle,needle+"""
        if set -q DOOM_R73_STYLE
            set defs $defs '-DDOOM_R73_R53_FIXED'
        end""")
p.write_text(s)
# The existing isolated six independent build trees prevent shared generated assets.
p=Path("scripts/lab/build_r71a12mul_hud.py")
s=p.read_text()
i=s.index("VARIANTS = (")
j=s.index("\nLABEL =",i)
replacement="""VARIANTS = (
    ('r73-s-pf', 'perf', {'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'solid','DOOM_R72_FLAT_2D':'0'}, []),
    ('r73-m-pf', 'perf', {'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25','DOOM_R72_FLAT_2D':'0'}, []),
    ('r73-f-pf', 'perf', {'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25flat2d','DOOM_R72_FLAT_2D':'1'}, []),
    ('r73-s-pl', 'play', {'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'solid','DOOM_R72_FLAT_2D':'0'}, []),
    ('r73-m-pl', 'play', {'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25','DOOM_R72_FLAT_2D':'0'}, []),
    ('r73-f-pl', 'play', {'DOOM_HUD_WAD':'1','DOOM_R73_STYLE':'micro25flat2d','DOOM_R72_FLAT_2D':'1'}, []),
)"""
s=s[:i]+replacement+s[j:]
s=s.replace("'DOOM_R52_AB_PROFILE': 'luma32'", "'DOOM_R52_AB_PROFILE': 'near25'")
s=s.replace("assert len(records) == 2","assert len(records) == 6")
start=s.index("    for name in ('r72flat2d-hud-perf',")
end=s.index(":\n        contents=flags[name]",start)
s=s[:start]+"""    for name in ('r73-s-pf','r73-m-pf','r73-f-pf','r73-s-pl','r73-m-pl','r73-f-pl')"""+s[end:]
s=s.replace("'DOOM_R71_MUL_ASM', 'DOOM_HUD_WAD', 'DOOM_R72_FLAT_2D'","'DOOM_R71_MUL_ASM', 'DOOM_HUD_WAD', 'DOOM_R73_R53_FIXED'")
s=s.replace("print('PASS R71A12MUL HUD only: A12 + MUL + Claudio stone-margin HUD', flush=True)","print('PASS R73 R53 fixed palette triplet: R71A12MUL + HUD',flush=True)")
p.write_text(s)
print("PASS R73 source patch, fixed palette menu disabled, six build variants")
