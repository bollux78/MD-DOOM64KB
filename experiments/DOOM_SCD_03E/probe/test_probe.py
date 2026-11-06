"""Verify the expansion paths and compare E1M1 frame throughput."""
import os
from pathlib import Path
import sys

import test_r136_play as play
from r64a_rsp_capture import RSP


def bounded_rsp(exe, rom, _max_frames, timeout):
    return RSP(exe, rom, 3000, timeout)


play.RSP = bounded_rsp
FRAMES = 24


def set_byte(game, name, value):
    address = game.sym(name)
    assert game.g.req(f"M{address:x},1:{value:02x}") == "OK"


def enter_level(game):
    game.step(0, 24)
    game.menu(0)
    game.tap(play.USE)
    game.step(0, 24)
    game.check_map(1, 85)


def frame_window(game):
    """Measure identical views at the E1M1 spawn, excluding startup."""
    game.breakpoint(game.frame)

    def next_frame():
        while game.next(game.poll, game.frame) == game.poll:
            game.pad(0)

    try:
        next_frame()
        position = game.position()
        start = game.number("ticcount", 4)
        for _ in range(FRAMES):
            next_frame()
        end = game.number("ticcount", 4)
        assert end > start and game.position() == position, (start, end, position)
        return end - start
    finally:
        game.breakpoint(game.frame, False)
        game.next(game.poll)


def show_rate(label, vblanks):
    print(f"PERF {label}: {FRAMES} frames / {vblanks} VBlanks = "
          f"{FRAMES * 60 / vblanks:.2f} fps (E1M1 spawn, NTSC)", flush=True)


def measure_prior(blastem):
    root = Path.home() / "Projetos/Personal/scd-03e-probe/run-42272149436-1"
    stem = root / "doom-md-r128-scd-probe"
    if not stem.with_suffix(".bin").is_file() or not stem.with_suffix(".elf").is_file():
        print("PERF: prior ROM absent on runner", flush=True)
        return
    game = play.Play(blastem, stem.with_suffix(".bin"), stem.with_suffix(".elf"))
    try:
        game.boot()
        assert game.number("scd_available", 1) == 1
        enter_level(game)
        show_rate("prior Sega CD", frame_window(game))
        assert game.number("scd_render_fault") == 0
    finally:
        game.g.close()


def main():
    mode = sys.argv[1]
    blastem = os.environ["BLASTEM"]
    stem = Path(os.environ["SCD_OUT"]) / "doom-md-r128-scd-probe"
    game = play.Play(blastem, Path(sys.argv[2]), stem.with_suffix(".elf"))
    try:
        game.boot()
        available = game.number("scd_available", 1)
        assert available == (mode == "on"), (mode, available)

        enter_level(game)
        if available:
            # Speed runs exclude the software pixel verifier.
            before = game.number("scd_rendered_batches")
            show_rate("optimized Sega CD", frame_window(game))
            assert game.number("scd_rendered_batches") > before
            set_byte(game, "scd_available", 0)
            show_rate("native renderer, same ROM and emulator", frame_window(game))
            set_byte(game, "scd_available", 1)

            set_byte(game, "scd_verify", 2)
            before = game.number("scd_rendered_batches")
            frame_window(game)
            batches = game.number("scd_rendered_batches") - before
            assert batches >= FRAMES
            copy = game.number("scd_copy_ticks", 4)
            wait = game.number("scd_wait_ticks", 4)
            sub = game.number("scd_sub_ticks", 4)
            assert 0 < sub <= wait and copy > 0, (copy, wait, sub)
            print(f"PERF stopwatch: {batches} batches, {copy} framebuffer copy ticks, "
                  f"{wait} wait ticks including {sub} sub-CPU drawing ticks", flush=True)

        # Pixel comparison runs separately while playing the game.
        set_byte(game, "scd_verify", 1)
        start = game.position()
        game.step(play.UP, 20)
        assert game.position() != start
        assert game.number("scd_render_fault") == 0
        assert game.number("scd_available", 1) == available
        batches = game.number("scd_rendered_batches")
        columns = game.number("scd_textured_columns")
        if available:
            assert batches > before and columns > 0, (batches, columns)
        else:
            assert batches == columns == 0, (batches, columns)
        print(f"PASS {mode.upper()}: E1M1 load and movement, {batches} live batches, "
              f"{columns} textured columns", flush=True)
    finally:
        game.g.close()
    if mode == "on":
        measure_prior(blastem)


if __name__ == "__main__":
    main()
