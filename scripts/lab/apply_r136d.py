#!/usr/bin/env python3
"""Use R136's reserved page 9 for extended-SSF map state and diagnose access."""
from pathlib import Path


def rep(file, old, new):
    path = Path(file)
    source = path.read_text()
    assert source.count(old) == 1, (file, old)
    path.write_text(source.replace(old, new))


rep('src/r22_blocklinks.h', '0x00A130F9UL=10;', '0x00A130F9UL=9;')
M = 'src/r23_mapmem.c'
# R136's packer reserves page 9 and stamps its signature at offset 0x7fff0.
from r133_pack import sig
signature = sig(9)
rep(M, '    uint16_t pos[18],n=0;uint8_t saved[18];', f'''    if (*(volatile const uint32_t *)0x0027FFF0UL != 0x{signature:08X}UL)
    {{
        R25_SRAM_END();
        I_Error("SRAM BANK 9 NOT MAPPED");
    }}
    const uint32_t probe = R22_SRAM_BASE + 1u;
    const uint8_t saved_byte = R22_SRAM_BYTE(probe);
    const uint8_t pattern = saved_byte ^ 0xffu;
    R22_SRAM_BYTE(probe) = pattern;
    const int byte_writable = R22_SRAM_BYTE(probe) == pattern;
    R22_SRAM_BYTE(probe) = saved_byte;
    if (!byte_writable)
    {{
        R25_SRAM_END();
        I_Error("SRAM BANK 9 NOT WRITABLE");
    }}
    uint16_t pos[18],n=0;uint8_t saved[18];''')
rep(M, 'SRAM MAP STATE UNAVAILABLE', 'SRAM BANK 9 RANGE OR MOVEP FAILED')
