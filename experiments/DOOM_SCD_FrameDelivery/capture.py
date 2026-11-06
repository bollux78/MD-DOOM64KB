"""Capture the completed R128 two-plane frame at the E1M1 spawn."""
import os
from pathlib import Path
import sys

from test_r136_play import Play, USE

rom, elf, out = map(Path, sys.argv[1:])
game = Play(os.environ["BLASTEM"], rom, elf)
try:
    game.boot()
    game.step(0, 24)
    game.menu(0)
    game.tap(USE)
    game.step(0, 24)
    game.check_map(1, 85)
    game.picture(out)
    frame = out.read_bytes()
    assert len(frame) == 3344 and len(set(frame)) > 8
    print(f"Captured {len(frame)} bytes at E1M1 spawn")
finally:
    game.g.close()
