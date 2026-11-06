"""Compare private PLAY ROMs in fixed demo windows, one BlastEm process per ROM."""
import hashlib
import json
import os
from pathlib import Path
import sys

import test_r136_play as play
from r64a_rsp_capture import RSP


def bounded_rsp(exe, rom, _max_frames, timeout):
    return RSP(exe, rom, 10000, timeout)


play.RSP = bounded_rsp
MODES = ("native", "sight", "sound", "rays", "all")


def demo(root, mode, mapnum, first, last, off=False):
    filename = root / f"doom-md-scd-logic-{mode}.bin"
    if off:
        # A cartridge header without the CD device flag tells BlastEm to boot without the add-on.
        rom = bytearray(filename.read_bytes())
        rom[0x190:0x1A0] = rom[0x190:0x1A0].replace(b"C", b" ")
        filename = Path(os.environ["XDG_DATA_HOME"]) / "no-cd.bin"
        filename.write_bytes(rom)
    game = play.Play(os.environ["BLASTEM"], filename, root / "logic.elf")
    counters = ("scd_sight_calls", "scd_sound_calls", "scd_ray_calls")
    try:
        game.boot()
        assert game.number("scd_available", 1) == int(not off)
        game.step(0, 24)
        game.menu(3)
        for _ in range(mapnum):
            game.tap(play.DOWN)
        game.tap(play.USE)
        assert game.number("r116_sel", 1) == mapnum
        game.breakpoint(game.poll, False)
        game.breakpoint(game.sound, False)
        ticker, end = game.sym("G_Ticker"), game.sym("R116_End")
        game.breakpoint(ticker)
        game.breakpoint(game.frame)
        game.breakpoint(end)
        addr = game.sym("r116_norender")
        assert game.g.req(f"M{addr:x},1:01") == "OK"
        samples, images = {}, {}
        while True:
            pc = game.next(ticker, game.frame, end)
            tic = game.number("_g_gametic", 4)
            if pc == ticker:
                if tic >= first - 8:
                    assert game.g.req(f"M{addr:x},1:00") == "OK"
                    game.breakpoint(ticker, False)
                continue
            assert pc == game.frame, (mode, mapnum, tic)
            if tic < first:
                continue
            assert tic <= last and game.number("_g_gamemap") == mapnum, (mode, mapnum, tic)
            assert tic not in samples, (mode, mapnum, tic)
            samples[tic] = game.number("ticcount", 4)
            if (tic - first) % 8 == 0 or tic == last:
                draw = game.number("r115_draw", 4)
                frame = game.read(draw, 3344)
                images[tic] = hashlib.sha256(frame).hexdigest()
            if tic == last:
                break
        assert samples.keys() == set(range(first, last + 1))
        assert game.number("scd_available", 1) == int(not off), (mode, mapnum, "CD failure")
        vblanks = samples[last] - samples[first]
        calls = [game.number(counter) for counter in counters]
        times = [samples[t] - samples[t - 1] for t in range(first + 1, last + 1)]
        print(json.dumps({"mode": mode, "off": off, "map": mapnum, "tics": [first, last],
                          "vblanks": vblanks, "fps_ntsc": round(60 * (last - first) / vblanks, 3),
                          "worst_vblanks": max(times), "calls": dict(zip(counters, calls))}), flush=True)
        return images, calls
    finally:
        game.g.close()


def main():
    root = Path(sys.argv[1])
    if len(sys.argv) > 2:
        mode = sys.argv[2]
        assert mode in MODES
        for window in ((1, 200, 260), (7, 280, 440)):
            demo(root, mode, *window)
        return
    used = [0, 0, 0]
    for window in ((1, 200, 260), (7, 280, 440)):
        reference, _ = demo(root, "native", *window)
        for mode in MODES[1:]:
            images, calls = demo(root, mode, *window)
            assert images == reference, (mode, window, [tic for tic in images if images[tic] != reference[tic]])
            if mode == "all":
                used = [a + b for a, b in zip(used, calls)]
        if window[0] == 1:
            images, calls = demo(root, "all", *window, off=True)
            assert images == reference and not any(calls)
    assert all(used), ("at least one coprocessor kernel went untested", used)
    print("PASS same-tic image checkpoints, active kernels and no-expansion fallback")


if __name__ == "__main__":
    main()
