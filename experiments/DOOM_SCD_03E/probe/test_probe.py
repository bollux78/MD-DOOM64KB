"""Verify the expansion paths and compare E1M1 frame throughput."""
import os
from pathlib import Path
import sys

import profile_native
import test_r136_play as play
from r64a_rsp_capture import RSP


def bounded_rsp(exe, rom, _max_frames, timeout):
    return RSP(exe, rom, 10000, timeout)


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


def frame_window(game, frames=FRAMES):
    """Measure identical views at the E1M1 spawn, excluding startup."""
    game.breakpoint(game.frame)

    def next_frame():
        while game.next(game.poll, game.frame) == game.poll:
            game.pad(0)

    try:
        next_frame()
        position = game.position()
        start = game.number("ticcount", 4)
        for _ in range(frames):
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
    root = Path.home() / "Projetos/Personal/scd-03e-probe/run-42274512230-1"
    stem = root / "doom-md-r128-scd-probe"
    if not stem.with_suffix(".bin").is_file() or not stem.with_suffix(".elf").is_file():
        print("PERF: prior ROM absent on runner", flush=True)
        return
    game = play.Play(blastem, stem.with_suffix(".bin"), stem.with_suffix(".elf"))
    try:
        game.boot()
        assert game.number("scd_available", 1) == 1
        enter_level(game)
        show_rate("serial Sega CD", frame_window(game))
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
            for route in range(3):
                set_byte(game, "scd_route", route)
                start_cols = game.number("scd_textured_columns")
                show_rate(f"SPLIT-ALT route={route}", frame_window(game))
                print(f"PERF route={route} spawn columns={game.number('scd_textured_columns') - start_cols}",
                      flush=True)
            assert game.number("scd_rendered_batches") > before
            set_byte(game, "scd_route", 0)
            set_byte(game, "scd_available", 0)
            sampler = profile_native.Sampler(Path(sys.argv[2]), stem.with_suffix(".elf"))
            profile_native.spawn(game, sampler, FRAMES)
            set_byte(game, "scd_available", 1)

            set_byte(game, "scd_verify", 2)
            before = game.number("scd_rendered_batches")
            profile_frames = 8
            frame_window(game, profile_frames)
            batches = game.number("scd_rendered_batches") - before
            assert batches >= profile_frames
            copy = game.number("scd_copy_ticks", 4)
            wait = game.number("scd_wait_ticks", 4)
            sub = game.number("scd_sub_ticks", 4)
            pack = game.number("scd_pack_ticks", 4)
            assert min(copy, wait, sub, pack) > 0, (copy, wait, sub, pack)
            print(f"PERF SPLIT-ALT stopwatch: {profile_frames} sampled frames, {batches} batches, "
                  f"compose={copy}, wait={wait}, sub={sub}, pack={pack} ticks", flush=True)

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
        reference = None
        for route in (None, 0, 1, 2):
            game = play.Play(blastem, Path(sys.argv[2]), stem.with_suffix(".elf"))
            try:
                captured = profile_native.demo(game, sampler, route)
                if route is None:
                    reference = captured
                else:
                    mismatches = [tic for tic, frame in captured.items() if frame != reference[tic]]
                    assert not mismatches, (route, mismatches)
                    print(f"PASS route={route}: all eight DEMO1 framebuffers match native", flush=True)
            finally:
                game.g.close()


if __name__ == "__main__":
    main()
