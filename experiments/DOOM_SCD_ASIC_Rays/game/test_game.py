"""Compare identical E1M1 demo tic windows, with separate profiling runs."""
import json
import os
from pathlib import Path
import sys

import test_r136_play as play
from r64a_rsp_capture import RSP


def bounded_rsp(exe, rom, _max_frames, timeout):
    return RSP(exe, rom, 9800, timeout)


play.RSP = bounded_rsp
root = Path(sys.argv[1])
counters = {
    "scd_ray_sight_ticks": 4, "scd_ray_transition_ticks": 4,
    "scd_ray_batches": 2, "scd_ray_accepted": 2, "scd_ray_queued": 2,
}


def run(mode, profile):
    rom = root / f"doom-md-scd-sight-{mode}.bin"
    game = play.Play(os.environ["BLASTEM"], rom, root / "sight.elf")
    try:
        game.boot()
        assert game.number("scd_ray_available", 1) == 1, (mode, "boot")
        game.step(0, 24)
        game.menu(3)
        game.tap(play.DOWN)
        game.tap(play.USE)
        assert game.number("r116_sel", 1) == 1
        game.breakpoint(game.poll, False)
        game.breakpoint(game.sound, False)
        ticker = game.sym("G_Ticker")
        game.breakpoint(ticker)
        game.breakpoint(game.frame)
        addr = game.sym("r116_norender")
        assert game.g.req(f"M{addr:x},1:01") == "OK"
        frames = {}
        while True:
            pc = game.next(ticker, game.frame)
            tic = game.number("_g_gametic", 4)
            if pc == ticker:
                if tic >= 192:
                    assert game.g.req(f"M{addr:x},1:00") == "OK"
                    game.breakpoint(ticker, False)
                continue
            if tic < 200:
                continue
            frames[tic] = game.number("ticcount", 4)
            if tic == 200:
                initial = {k: game.number(k, n) for k, n in counters.items()}
                if profile:
                    addr = game.sym("scd_ray_profile")
                    assert game.g.req(f"M{addr:x},1:01") == "OK"
            if tic == 300:
                break
        assert frames.keys() == set(range(200, 301))
        assert game.number("scd_ray_available", 1) == 1, (mode, "transport failed")
        result = {k: (game.number(k, n) - initial[k]) % (1 << (8 * n))
                  for k, n in counters.items()}
        result.update(mode=mode, profile=profile, vblanks=frames[300] - frames[200],
                      worst_vblanks=max(frames[t] - frames[t - 1] for t in range(201, 301)))
        print("ASIC_GAME " + json.dumps(result, sort_keys=True), flush=True)
        if mode == "asic":
            assert result["scd_ray_batches"] and result["scd_ray_queued"], result
        if profile:
            assert result["scd_ray_sight_ticks"], result
    finally:
        game.g.close()


for profile in (False, True):
    for mode in ("native", "asic"):
        run(mode, profile)
