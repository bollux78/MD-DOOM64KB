"""Check startup, live Sega CD rasterization and the unexpanded fallback."""
import os
from pathlib import Path
import sys

import test_r136_play as play
from r64a_rsp_capture import RSP


def bounded_rsp(exe, rom, _max_frames, timeout):
    return RSP(exe, rom, 3000, timeout)


play.RSP = bounded_rsp
mode = sys.argv[1]
stem = Path(os.environ["SCD_OUT"]) / "doom-md-r128-scd-probe"
game = play.Play(os.environ["BLASTEM"], Path(sys.argv[2]), stem.with_suffix(".elf"))
try:
    game.boot()
    available = game.number("scd_available", 1)
    assert available == (mode == "on"), (mode, available)
    verify = game.sym("scd_verify")
    assert game.g.req(f"M{verify:x},1:01") == "OK"
    game.step(0, 24)
    game.menu(0)
    game.tap(play.USE)
    game.step(0, 24)
    game.check_map(1, 85)
    start = game.position()
    game.step(play.UP, 20)
    assert game.position() != start
    assert game.number("scd_render_fault") == 0
    assert game.number("scd_available", 1) == available
    batches = game.number("scd_rendered_batches")
    columns = game.number("scd_textured_columns")
    if mode == "on":
        assert batches > 0 and columns > 0, (batches, columns)
        print(f"PASS: {batches} live batches match the reference pixels; {columns} textured columns")
    else:
        assert batches == columns == 0, (batches, columns)
    print(f"PASS {mode.upper()}: startup status, E1M1 load and movement", flush=True)
finally:
    game.g.close()
