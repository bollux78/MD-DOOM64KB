"""Read the actual ASIC pixel check and bank transition from the cartridge."""
import os
from pathlib import Path
import subprocess
import sys

from r64a_rsp_capture import RSP

rom, elf = map(Path, sys.argv[1:])
nm = Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"
symbols = {}
for line in subprocess.check_output([nm, elf], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3:
        symbols[fields[2]] = int(fields[0], 16) & 0xffffff
g = RSP(os.environ["BLASTEM"], rom, 1800, 60)
try:
    g.req("qSupported")
    stop = symbols["scene_complete"]
    assert g.req(f"Z0,{stop:x},2") == "OK"
    g.cont()
    assert int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff == stop
    state = int.from_bytes(g.readmem(symbols["scene_state"], 2), "big")
    raw = g.readmem(symbols["scene_metrics"], 64)
    for i, label in enumerate(("native", "scd")):
        values = [int.from_bytes(raw[j:j + 4], "big") for j in range(i * 32, i * 32 + 32, 4)]
        print("SCENE", label, dict(zip(("frames", "render_ticks", "request_ticks", "swap_ticks",
                                      "vblank_wait_ticks", "dma_ticks", "total_ticks", "bad"), values)))
        assert values[0] == 16 and not values[-1], (state, values)
    assert state == 1
finally:
    g.close()
