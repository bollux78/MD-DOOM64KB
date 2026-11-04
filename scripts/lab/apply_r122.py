#!/usr/bin/env python3
"""R122 layout (after apply_r119.py both): keep every byte the Z80 reads below $200000 (audio stuck notes).

Finding (ELF symbol maps of the delivered ROMs):
  bgm_episode (XGM2 multi-track music, streamed from ROM by the Z80 driver) ends right where doom_iwad
  (.rodata_binf) starts; the part above $200000 grew from 3-11 KB (R100-R112) to 62-63 KB (R113, R115:
  0x1DA200-0x20FA00 -> 64,000 bytes above 2 MB).
  An SRAM window ($A130F1 = 1, R25_SRAM_BEGIN/END) maps cartridge SRAM over $200000+. IRQs are masked for the
  68000 (R104) but the Z80 keeps running: if the XGM2 driver fetches music bytes from >= $200000 inside a window,
  it reads SRAM instead of the song -> wrong commands, e.g. a lost key-off = a note that stays on until a later
  event on that channel. Rate scales with the number of SRAM windows (AI Normal >> AI Low: logic SRAM accesses),
  hardware only (BlastEm does not reproduce it), and depends on which track (a map change can avoid it).
Fix: r91_joint (512 KiB Shadow table, read only by the 68000 in I_FinishUpdate, never inside an SRAM window)
moves to .rodata_binf (after the music, beside doom_iwad). The music then sits 512 KiB lower, wholly below 2 MB.
No code or RAM change. The workflow asserts the layout from the ELF (music, PCM, XGM stop stream < $200000).
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


# gen_r91_shadow.py writes src/r79_shadow_tables.h during the build: emit r91_joint into the far section.
rep('scripts/lab/gen_r91_shadow.py',
    "p.write_text(emit('r79_pal',pal,'uint16_t')+emit('r79_map',maps,'uint16_t')+emit('r79_cost',cost,'uint16_t')+emit('r91_joint',fast,'uint32_t'))",
    "p.write_text(emit('r79_pal',pal,'uint16_t')+emit('r79_map',maps,'uint16_t')+emit('r79_cost',cost,'uint16_t')"
    "+emit('r91_joint',fast,'uint32_t').replace('static const uint32_t r91_joint','static const uint32_t __attribute__((section(\".rodata_binf\"),aligned(4))) r91_joint',1))")
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert s.count("'r119-'") == 1 and s.count("('both', 1)") == 1
p.write_text(s.replace("'r119-'", "'r122-'").replace("('both', 1)", "('layout', 1)"))
print('R122 layout')
