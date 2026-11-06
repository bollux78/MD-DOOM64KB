#!/usr/bin/env python3
"""R135/R135b (after apply_r133/r134 sources): map-state "SRAM" on the extended SSF mapper ("SEGA SSF" header).

Cause of R134 "SRAM MAP STATE UNAVAILABLE": with "SEGA SSF" in the header, BlastEm (and Mega EverDrive
X3/X5/X7/Pro) use the *extended* SSF mapper (BlastEm MAPPER_SEGA_MED_V2). There, $A130F1 is NOT an SRAM
switch: a write to $A130F0/F1 without bit 15 (0x8000) is ignored, so $200000 stays ROM page 4
(read-only) and R23's write/read probe fails. The 4 MiB builds used the classic mapper, where $A130F1=1
overlays SRAM.

Extended SSF has no separate SRAM overlay: cartridge memory itself becomes writable when $A130F0 bit 13
(0x2000, write-enable) is set together with bit 15. So the map state window becomes:
  BEGIN: $A130F9 (slot 4, $200000-$27FFFF) = R135_PAGE (an unused 512 KiB page), then $A130F0.w = 0xA000
  END:   $A130F0.w = 0x8000 (write-protect, slot 0 = page 0), then $A130F9 = 4
R22_SRAM_BASE ($200000) and the odd-lane layout are unchanged. Page R135_PAGE=10 ($500000-$57FFFF in the
image) is just past the 5 MiB data; it needs >= 5.5 MiB of cart RAM (BlastEm gives 16 MiB). Map state is
rebuilt on every level load, so it never needs to persist.
Order matters: page first, then write-enable; write-protect first, then page back - ROM page 4 is never
writable. Active only with DOOM_R133_SSF_BOOT (the 5 MiB SSF builds); 4 MiB builds unchanged.
Slot 0 stays page 0 (low 5 bits of $A130F0 = 0). No RAM added.
"""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--classic-sram", action="store_true")
classic_sram = parser.parse_args().classic_sram

PAGE = 10


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


H = 'src/r22_blocklinks.h'
if not classic_sram:
    rep(H, '#ifndef R22_SRAM_ENABLE\n', '''#if defined(DOOM_R133_SSF_BOOT)
/* R135: extended SSF mapper (header "SEGA SSF"): page %d in slot 4, cartridge write-enable. */
#define R22_SRAM_ENABLE() do { *(volatile uint8_t*)0x00A130F9UL=%d; *(volatile uint16_t*)0x00A130F0UL=0xA000u; } while(0)
#define R22_SRAM_DISABLE() do { *(volatile uint16_t*)0x00A130F0UL=0x8000u; *(volatile uint8_t*)0x00A130F9UL=4; } while(0)
#endif
#ifndef R22_SRAM_ENABLE
''' % (PAGE, PAGE))

    G = 'src/i_genesis.c'
    rep(G, '    *(volatile uint8_t*)0x00A130F1UL=0;\n', '''#if defined(DOOM_R133_SSF_BOOT)
    *(volatile uint16_t*)0x00A130F0UL=0x8000u; *(volatile uint8_t*)0x00A130F9UL=4; /* R135 */
#else
    *(volatile uint8_t*)0x00A130F1UL=0;
#endif
''')

# R135b: every other place that opens/closes the window must use the R135 macros. A raw $A130F1 write is
# ignored by the extended mapper, so a raw "disable" left page 10 + write-enable in slot 4 for good: ROM
# $200000-$27FFFF (WAD lumps such as TEXTURE1) then read as map-state RAM -> "SKY1 not found".
C = 'src/r81_save_codec.inc'          # save/load codec: enable via macro, disable raw (2x) -> the SKY1 bug
rep(C, """#if !defined(DOOM_R27_SRAM_FIXED)
    *(volatile uint8_t*)0x00A130F1UL=0;
#endif""", """#if defined(DOOM_R133_SSF_BOOT)
    R22_SRAM_DISABLE(); /* R135b */
#elif !defined(DOOM_R27_SRAM_FIXED)
    *(volatile uint8_t*)0x00A130F1UL=0;
#endif""", 2)
D = 'src/r_draw.c'                    # SRAM column cache init: raw enable (ignored) -> probe failed silently
rep(D, "    *control = 1; /* enable SRAM; writable, do not disable during demo */\n",
    """#if defined(DOOM_R133_SSF_BOOT)
    (void)control; R22_SRAM_ENABLE(); /* R135b */
#else
    *control = 1; /* enable SRAM; writable, do not disable during demo */
#endif
""")
# Fail closed for configurations that keep the window open or write $A130F1 raw.
rep(H, '#ifndef R22_SRAM_ENABLE\n', """#if defined(DOOM_R133_SSF_BOOT) && (defined(DOOM_R27_SRAM_FIXED) || !defined(DOOM_R25_MUSIC))
#error R135: extended SSF needs SRAM windows (page 10 would hide ROM $200000-$27FFFF permanently)
#endif
#ifndef R22_SRAM_ENABLE
""")
rep('src/r21_prof.c', '    *(volatile uint8_t *)0xA130F1 = 1;     /* SRAM_enable(): read/write */\n',
    """#if defined(DOOM_R133_SSF_BOOT)
#error R135: R21 profiler writes $A130F1 directly; not valid on the extended SSF mapper
#endif
    *(volatile uint8_t *)0xA130F1 = 1;     /* SRAM_enable(): read/write */
""")
# Audit: every raw A130F1 write left must sit in a non-SSF branch (whitelist by file and count).
import re
seen = {}
for f in Path('src').rglob('*'):
    if f.suffix in ('.c', '.h', '.inc', '.s'):
        n = len(re.findall(r'0x(?:00)?A130F1', f.read_text(errors='replace'), re.I))
        if n: seen[str(f)] = n
allowed = {'src/r22_blocklinks.h': 2, 'src/i_genesis.c': 1, 'src/r81_save_codec.inc': 2, 'src/r_draw.c': 1, 'src/r21_prof.c': 1}
assert seen == allowed, ('R135 audit: unexpected raw $A130F1 users', seen)
if classic_sram:
    # Report which part of the unchanged map-memory probe failed on hardware.
    M = 'src/r23_mapmem.c'
    rep(M, '#if defined(DOOM_R39C_MOVEP_MAP)\n    /* Verify MOVEP lane order',
        '    const int byte_ok = ok;\n    ok = 1;\n#if defined(DOOM_R39C_MOVEP_MAP)\n    /* Verify MOVEP lane order')
    rep(M, '    if(!ok)I_Error("SRAM MAP STATE UNAVAILABLE");',
        '    if(!byte_ok)I_Error("SRAM CLASSIC BYTE TEST FAILED");\n'
        '    if(!ok)I_Error("SRAM CLASSIC MOVEP TEST FAILED");')
    print('R135b classic SRAM audit ok')
else:
    print('R135b MED SRAM page', PAGE, 'audit ok')
