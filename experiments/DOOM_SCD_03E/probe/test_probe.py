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
ROUTES = {
    0: "all",
    1: "route1",
    2: "route2",
    3: "reject-all",
    5: "route1+early",
    6: "route2+early",
    8: "all+resident-luts",
    16: "all+shared-source",
    24: "all+resident-luts+shared-source",
    29: "route1+all-optimizations",
}
METRICS = (
    ("scd_rendered_batches", 2),
    ("scd_textured_columns", 2),
    ("scd_copy_ticks", 4),
    ("scd_wait_ticks", 4),
    ("scd_sub_ticks", 4),
    ("scd_pack_ticks", 4),
)


def set_byte(game, name, value):
    address = game.sym(name)
    assert game.g.req(f"M{address:x},1:{value:02x}") == "OK"


def enter_level(game):
    game.step(0, 24)
    game.menu(0)
    game.tap(play.USE)
    game.step(0, 24)
    game.check_map(1, 85)


def frame_window(game, frames=FRAMES, metrics=()):
    """Measure identical views at the E1M1 spawn, excluding startup."""
    game.breakpoint(game.frame)

    def next_frame():
        while game.next(game.poll, game.frame) == game.poll:
            game.pad(0)

    try:
        next_frame()
        position = game.position()
        start = game.number("ticcount", 4)
        initial = [game.number(name, size) for name, size in metrics]
        for _ in range(frames):
            next_frame()
        end = game.number("ticcount", 4)
        assert end > start and game.position() == position, (start, end, position)
        if metrics:
            deltas = tuple((game.number(name, size) - before) % (1 << (size * 8))
                           for (name, size), before in zip(metrics, initial))
            return end - start, deltas
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
            for route, label in ROUTES.items():
                set_byte(game, "scd_route", route)
                vblanks, (batches, columns) = frame_window(game, metrics=METRICS[:2])
                show_rate(label, vblanks)
                print(f"PERF {label}: {batches} batches, {columns} columns in spawn window",
                      flush=True)
                if route == 3:
                    assert batches == columns == 0
            assert game.number("scd_rendered_batches") > before
            set_byte(game, "scd_route", 0)
            set_byte(game, "scd_available", 0)
            sampler = profile_native.Sampler(Path(sys.argv[2]), stem.with_suffix(".elf"))
            profile_native.spawn(game, sampler, FRAMES)
            set_byte(game, "scd_available", 1)

            set_byte(game, "scd_verify", 2)
            profile_frames = 8
            for route in (0, 1, 2, 3, 5, 6, 8, 16, 24, 29):
                set_byte(game, "scd_route", route)
                vblanks, (batches, columns, copy, wait, sub, pack) = frame_window(
                    game, profile_frames, METRICS)
                if route in (0, 8, 16, 24):
                    assert batches >= profile_frames and min(copy, sub, pack) > 0
                print(f"PERF stopwatch {ROUTES[route]}: {profile_frames} frames / {vblanks} VBlanks, "
                      f"{batches} batches, {columns} columns, "
                      f"compose={copy}, wait={wait}, sub={sub}, pack={pack} ticks", flush=True)
            set_byte(game, "scd_route", 24)

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
        for route in (None, *ROUTES):
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
        game = play.Play(blastem, Path(sys.argv[2]), stem.with_suffix(".elf"))
        try:
            captured = profile_native.demo(game, sampler, route=24, force_timeout=True)
            assert captured == reference, [tic for tic, frame in captured.items() if frame != reference[tic]]
            print("PASS timeout: same-frame native redraw at tic 211 and matching subsequent checkpoints",
                  flush=True)
        finally:
            game.g.close()


if __name__ == "__main__":
    main()
