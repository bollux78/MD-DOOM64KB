"""Collect native monster-to-player visibility queries at fixed demo tics."""
import json
import os
from pathlib import Path
import struct
import sys

import test_r136_play as play
from r64a_rsp_capture import RSP


def bounded_rsp(exe, rom, _max_frames, timeout):
    return RSP(exe, rom, 9800, timeout)


play.RSP = bounded_rsp
rom, elf, output = map(Path, sys.argv[1:])
game = play.Play(os.environ["BLASTEM"], rom, elf)
queries = []
try:
    game.boot()
    game.step(0, 24)
    game.menu(3)
    game.tap(play.DOWN)
    game.tap(play.USE)
    assert game.number("r116_sel", 1) == 1
    game.breakpoint(game.poll, False)
    game.breakpoint(game.sound, False)
    hook = game.sym("SCD_RayCapture")
    ticker, end = game.sym("G_Ticker"), game.sym("R116_End")
    for address in (hook, ticker, end):
        game.breakpoint(address)
    no_render = game.sym("r116_norender")
    assert game.g.req(f"M{no_render:x},1:01") == "OK"
    while True:
        pc = game.next(hook, ticker, end)
        if pc == ticker:
            if game.number("_g_gametic", 4) > 440:
                break
            continue
        if pc == end:
            break
        sp = int(game.g.req("g")[15 * 8:16 * 8], 16)
        tic, x1, y1, x2, y2, visible = struct.unpack(">IiiiiI", game.read(sp + 4, 24))
        assert 200 <= tic <= 440 and visible in (0, 1), (tic, visible)
        queries.append([tic, x1, y1, x2, y2, visible])
finally:
    game.g.close()
assert len(queries) >= 256, ("fewer than 256 monster-to-player calls", len(queries))
output.write_text(json.dumps(queries, indent=1) + "\n")
print(f"Captured {len(queries)} calls, {sum(q[0] <= 300 for q in queries)} in tics 200–300. "
      f"First 256 span tics {queries[0][0]}–{queries[255][0]}.")
