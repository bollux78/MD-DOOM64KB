#!/usr/bin/env python3
"""R104 (after apply_r100.py f1, optionally apply_r103.py): no interrupt inside an SRAM window.

Real hardware (old Everdrive clone): blockmap heads in cartridge SRAM become garbage at a fixed
demo point (R92+, Shadow On; BlastEm never shows it). Hypothesis: the VBlank ISR (VDP DMA from
WRAM, Z80 bus request, CRAM writes) runs while $A130F1=1 maps SRAM over $200000-$20FFFF.
R25_SRAM_BEGIN now masks interrupts (SR |= $0700) and R25_SRAM_END restores the saved SR after
unmapping. Windows are short (one MOVEP or a column copy), and level-load loops already run
outside gameplay. Windows never nest (checked by the BlastEm run: a nested pair would leave
interrupts masked and trip the VBlank timeout).
R104_NAME selects the build label (mask | maskdiag).
"""
import os
from pathlib import Path

name = os.environ.get('R104_NAME', 'mask'); assert name in ('mask', 'maskdiag')


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


H = 'src/r22_blocklinks.h'
rep(H, '''#define R25_SRAM_BEGIN() do { __asm__ volatile("" ::: "memory"); R22_SRAM_ENABLE(); __asm__ volatile("" ::: "memory"); } while(0)
#define R25_SRAM_END() do { __asm__ volatile("" ::: "memory"); R22_SRAM_DISABLE(); __asm__ volatile("" ::: "memory"); } while(0)''',
'''extern volatile uint16_t r104_sr;
#if defined(__m68k__)
#define R25_SRAM_BEGIN() do { uint16_t r104_s; __asm__ volatile("move.w %%sr,%0\\n\\tori.w #0x700,%%sr" : "=d"(r104_s) :: "cc", "memory"); \\
    r104_sr = r104_s; R22_SRAM_ENABLE(); __asm__ volatile("" ::: "memory"); } while(0)
#define R25_SRAM_END() do { __asm__ volatile("" ::: "memory"); R22_SRAM_DISABLE(); uint16_t r104_s = r104_sr; \\
    __asm__ volatile("move.w %0,%%sr" :: "d"(r104_s) : "cc", "memory"); } while(0)
#else
#define R25_SRAM_BEGIN() do { __asm__ volatile("" ::: "memory"); R22_SRAM_ENABLE(); __asm__ volatile("" ::: "memory"); } while(0)
#define R25_SRAM_END() do { __asm__ volatile("" ::: "memory"); R22_SRAM_DISABLE(); __asm__ volatile("" ::: "memory"); } while(0)
#endif''')
rep('src/r22_blocklinks.c', 'uint16_t r22_block_cells;', 'uint16_t r22_block_cells;\nvolatile uint16_t r104_sr;')
# Level-load probes opened the window with a bare enable and close it with R25_SRAM_END.
rep('src/r22_blocklinks.c', '    R22_SRAM_ENABLE();\n    for(uint16_t i=0;i<count;i++)saved', '    R25_SRAM_BEGIN();\n    for(uint16_t i=0;i<count;i++)saved')
rep('src/r23_mapmem.c', '    node_used=0;node_free=NULL;end=32768UL;\n    R22_SRAM_ENABLE();', '    node_used=0;node_free=NULL;end=32768UL;\n    R25_SRAM_BEGIN();')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
old_pre = "'r103-'" if "'r103-'" in s else "'r100-'"
old_set = "('diag', 1)" if "('diag', 1)" in s else "('f1', 1)"
assert s.count(old_pre) >= 1 and s.count(old_set) == 1, (old_pre, old_set)
p.write_text(s.replace(old_pre, "'r104-'").replace(old_set, repr((name, 1))))
print('R104', name, 'SRAM windows mask interrupts')
