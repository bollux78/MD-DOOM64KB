#!/usr/bin/env python3
"""Drive the Sega CD visual demo through the SGDK joypad read in BlastEm."""
import os
from pathlib import Path
import re
import subprocess
import sys

from r64a_rsp_capture import RSP, symbols

UP, DOWN, LEFT, RIGHT, A = 1, 2, 4, 8, 64
out = Path(os.environ["SCD_OUT"])
elf = out / "visual.elf"
syms = symbols(elf)


def at(name):
    matches = [v for k, v in syms.items() if k.split(".")[0] == name]
    address, = matches
    return address & 0xFFFFFF


main, = (name for name in syms if name.split(".")[0] == "main")
asm = subprocess.check_output(
    [str(Path(os.environ["GDK"]) / "bin/m68k-elf-objdump"),
     "-d", f"--disassemble={main}", elf],
    text=True,
)
# LTO can emit a direct load or load the joyState address into a register first.
reads = re.findall(
    r"^\s*([0-9a-f]+):.*\b(?:movew|lea)\s+[0-9a-f]+ <joyState[^>]*>,%[ad][0-7]$",
    asm, re.MULTILINE,
)
assert len(reads) == 1, (main, [line for line in asm.splitlines() if "joyState" in line])
poll = int(reads[0], 16)
fail, joy = at("scd_gate_fail"), at("joyState")
g = RSP(os.environ["BLASTEM"], out / "doom-scd-visual-3d.bin", 8000, 90)
phase = "boot"
largest_interval = 0
previous_tick = None


def read(addr, size):
    return int.from_bytes(g.readmem(addr & 0xFFFFFF, size), "big")


def position():
    return tuple(read(at(name), 2) for name in ("camera_x", "camera_y", "heading"))


def next_poll():
    global largest_interval, previous_tick
    g.cont()
    regs = g.req("g")
    pc = int(regs[17 * 8:18 * 8], 16) & 0xFFFFFF
    if pc == fail:
        sp = int(regs[15 * 8:16 * 8], 16) & 0xFFFFFF
        reason = g.readmem(read(sp + 4, 4) & 0xFFFFFF, 40).split(b"\0", 1)[0].decode()
        raise RuntimeError(f"{reason} after {read(at('scd_frames'), 4)} frames "
                           f"during {phase}; pose Q8={position()}")
    assert pc == poll, (hex(pc), hex(poll), phase)
    tick = read(at("vtimer"), 4)
    if previous_tick is not None:
        largest_interval = max(largest_interval, tick - previous_tick)
    previous_tick = tick


def hold(mask, count):
    for _ in range(count):
        assert g.req(f"M{joy:x},2:{mask:04x}") == "OK"
        next_poll()


try:
    g.req("qSupported")
    for address in (fail, poll):
        assert g.req(f"Z0,{address:x},2") == "OK"
    next_poll()

    phase = "south wall"
    hold(A, 1)
    hold(RIGHT, 16)
    assert position() == (640, 2176, 16), position()
    hold(UP, 76)
    assert position() == (640, 3784, 16), position()
    print(f"{phase}: {position()}", flush=True)
    hold(RIGHT, 64)
    assert position() == (640, 3784, 16), position()

    phase = "north-side obstruction"
    hold(DOWN, 144)
    assert position() == (640, 808, 16), position()
    hold(LEFT, 64)
    assert position() == (640, 808, 16), position()
    print(f"{phase}: {position()}", flush=True)

    phase = "west wall"
    hold(LEFT, 16)
    hold(DOWN, 24)
    assert position() == (304, 808, 0), position()
    hold(LEFT, 64)
    assert position() == (304, 808, 0), position()
    print(f"{phase}: {position()}", flush=True)

    phase = "autoplay restart"
    hold(A, 1)
    assert position() == (656, 2176, 0), position()
    hold(0, 8)
    assert position() == (784, 2176, 0), position()
    assert largest_interval <= 6, f"manual frame took {largest_interval} VBlanks"
    print(f"blastem manual: PASS ({read(at('scd_frames'), 4)} frames, "
          f"largest frame interval {largest_interval} VBlanks)")
except RuntimeError as error:
    print(f"blastem manual: {error}", file=sys.stderr)
    raise
finally:
    g.close()
