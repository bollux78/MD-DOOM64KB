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
    stop = symbols["asic_probe_complete"]
    assert g.req(f"Z0,{stop:x},2") == "OK"
    g.cont()
    assert int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff == stop
    raw = g.readmem(symbols["asic_probe_result"], 14)
    result = [int.from_bytes(raw[i:i + 2], "big") for i in range(0, 14, 2)]
    print("ASIC result: state=%d, 1M=%d (%d ticks), 2M=%d (%d ticks, first=%04x), "
          "1M swap restored=%d" % tuple(result), flush=True)
    assert result[0] == 2 and result[3] == 1 and result[6] == 1, result
finally:
    g.close()
