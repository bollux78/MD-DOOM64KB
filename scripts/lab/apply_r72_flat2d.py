#!/usr/bin/env python3
"""R72 flat-only two-dimensional color parity experiment, applied to R71 sources.
Leaves walls, sprite rendering, HUD and all original R71 sources unchanged in Git."""
from pathlib import Path
p=Path("src/r22_video.inc")
s=p.read_text()
a='    uint8_t sample=(uint8_t)(r52map[c]&15u);'
assert s.count(a)==1
s=s.replace(a,a+"""
#if defined(DOOM_R72_FLAT_2D)
    const uint8_t *other_flat=
#if defined(DOOM_R64A_PROLOGUE)
        cx->flat[(x ^ 1u)&1u];
#else
        (x&1u)?R59_CURRENT.flat_even:R59_CURRENT.flat_odd;
#endif
    const uint8_t sample_odd=(uint8_t)(other_flat[c]&15u);
#endif
""")
start=s.index('void R_DrawColumnFlat(')
end=s.index('void I_ReloadPalette(',start)
flat=s[start:end]
old='        *dst=(uint8_t)((*dst&0xf0u)|sample);'
assert flat.count(old)==2
flat=flat.replace(old,"""        *dst=(uint8_t)((*dst&0xf0u)|
#if defined(DOOM_R72_FLAT_2D)
            sample_odd
#else
            sample
#endif
        );""",1)
old='    const uint8_t pair=(uint8_t)(sample*0x11u);'
assert flat.count(old)==1
flat=flat.replace(old,"""    const uint8_t pair=
#if defined(DOOM_R72_FLAT_2D)
        (uint8_t)((sample<<4)|sample_odd);
#else
        (uint8_t)(sample*0x11u);
#endif
""")
s=s[:start]+flat+s[end:]
p.write_text(s)
fish=Path("scripts/lab/build_r35_linear.fish")
t=fish.read_text()
anchor="        set defs $defs '-DDOOM_R71_MUL_ASM'"
assert t.count(anchor)==1
t=t.replace(anchor,anchor+"""
        if set -q DOOM_R72_FLAT_2D; and test "$DOOM_R72_FLAT_2D" = 1
            set defs $defs '-DDOOM_R72_FLAT_2D'
        end""")
fish.write_text(t)
builder=Path("scripts/lab/build_r71a12mul_hud.py")
b=builder.read_text()
assert b.count("'DOOM_HUD_WAD': '1'")==2
b=b.replace("'DOOM_HUD_WAD': '1'","'DOOM_HUD_WAD': '1', 'DOOM_R72_FLAT_2D': '1'")
b=b.replace("r71a12mul-hud-", "r72flat2d-hud-")
b=b.replace("DOOM_R71_MUL_ASM', 'DOOM_HUD_WAD'","DOOM_R71_MUL_ASM', 'DOOM_HUD_WAD', 'DOOM_R72_FLAT_2D'")
b=b.replace("'-DDOOM_HUD_WAD'):","'-DDOOM_HUD_WAD'):")
builder.write_text(b)
print("R72 flat 2D source/build patch applied")
