"""Read timed ray results from the cartridge."""
import json
import os
from pathlib import Path
import subprocess
import sys

from r64a_rsp_capture import RSP

rom, elf = map(Path, sys.argv[1:3])
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
    selected = json.loads(Path(sys.argv[3]).read_text())
    raw_hits = b"".join(g.readmem(0x630040 + offset, 128) for offset in range(0, 1024, 128))
    hits = [int.from_bytes(raw_hits[i:i + 4], "big") for i in range(0, 1024, 4)]
    pairs = [{"tic": q[0], "native_visible": bool(q[5]),
              "first_block_map_units": None if hit == 0xffffffff else hit / 256}
             for q, hit in zip(selected, hits)]
    assert len(pairs) == 256
    assert sum(q["native_visible"] and q["first_block_map_units"] is not None for q in pairs) == result["false_blocked"]
    rom.with_suffix(".hits.json").write_text(json.dumps(pairs, indent=1) + "\n")
    print("False-blocked distances:", [q for q in pairs if q["native_visible"] and q["first_block_map_units"] is not None])
finally:
    g.close()
