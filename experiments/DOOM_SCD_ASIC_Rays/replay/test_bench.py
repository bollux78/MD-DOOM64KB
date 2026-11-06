"""Read timed ray results from the cartridge."""
import json
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
    stop = symbols["ray_bench_complete"]
    assert g.req(f"Z0,{stop:x},2") == "OK"
    g.cont()
    assert int(g.req("g")[17 * 8:18 * 8], 16) & 0xffffff == stop
    raw = g.readmem(symbols["ray_bench_result"], 48)
    values = [int.from_bytes(raw[i:i + 4], "big") for i in range(0, 48, 4)]
    keys = ("state", "rays", "setup_ticks", "draw_ticks", "scan_ticks", "dda_ticks",
            "asic_dda_mismatches", "false_blocked", "false_clear",
            "native_visible", "native_blocked", "timeouts")
    result = dict(zip(keys, values))
    result["asic_total_ticks"] = sum(result[k] for k in ("setup_ticks", "draw_ticks", "scan_ticks"))
    print("RAY_BENCH " + json.dumps(result, sort_keys=True), flush=True)
    assert result["state"] == 2 and result["rays"] == 256 and not result["timeouts"], result
    assert not result["asic_dda_mismatches"], result
finally:
    g.close()
