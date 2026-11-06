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
    stop = symbols["delivery_complete"]
    assert g.req(f"Z0,{stop:x},2") == "OK"
    g.cont()
    assert int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff == stop
    state = int.from_bytes(g.readmem(symbols["delivery_state"], 2), "big")
    raw = g.readmem(symbols["delivery_result"], 80)
    labels = ("packed-native", "packed-scd", "rows-native", "rows-scd")
    for i, label in enumerate(labels):
        values = [int.from_bytes(raw[j:j + 4], "big") for j in range(i * 20, i * 20 + 20, 4)]
        print(label, dict(zip(("frames", "swap_ticks", "dma_ticks", "total_ticks", "bad"), values)))
        assert values[0] == 32 and not values[-1], (state, values)
    assert state == 2
finally:
    g.close()
