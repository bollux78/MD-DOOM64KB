#!/usr/bin/env python3
"""R135 (after apply_r133/r134 sources): map-state "SRAM" on the extended SSF mapper ("SEGA SSF" header).

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
from pathlib import Path

PAGE = 10


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


H = 'src/r22_blocklinks.h'
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
print('R135 MED SRAM page', PAGE)
