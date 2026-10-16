#!/usr/bin/env python3
"""Validate an external, genuine Mega Drive VGM before embedding in R18.

A silent 73-byte generated VGM must never be mistaken for the user's song.
The original VGM stays outside Git; SGDK rescomp converts it to XGM.
"""
from pathlib import Path
import struct
import sys

def check(path: Path) -> None:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raise ValueError("compressed VGZ detected: decompress to .vgm first")
    if len(raw) < 256:
        raise ValueError("VGM too short (<256 bytes): possible silent build placeholder")
    if raw[:4] != b"Vgm ":
        raise ValueError("missing Vgm header")
    u32 = lambda offset: struct.unpack_from("<I", raw, offset)[0]
    version = u32(0x08)
    if not (0x100 <= version <= 0x200):
        raise ValueError(f"unexpected VGM version: 0x{version:x}")
    data_start = 0x40 if version < 0x150 or u32(0x34) == 0 else 0x34 + u32(0x34)
    if not (0x40 <= data_start < len(raw)):
        raise ValueError("invalid VGM data offset")
    ym2612 = u32(0x2c) & 0x3fffffff
    sn76489 = u32(0x0c) & 0x3fffffff
    if not (ym2612 or sn76489):
        raise ValueError("VGM declares neither YM2612 nor SN76489 clock")
    eof = u32(0x04)
    if eof and eof + 4 > len(raw):
        raise ValueError("truncated VGM (EOF offset beyond file)")
    samples = u32(0x18)
    loop_offset = u32(0x1c)
    print(f"PASS: {path.name}: {len(raw)} bytes, VGM {version >> 8:x}.{version & 255:02x}, "
          f"YM2612={ym2612} Hz, SN76489={sn76489} Hz, "
          f"samples={samples}, loop={'yes' if loop_offset else 'not marked'}")
    if not ym2612:
        print("NOTE: PSG-only VGM: SGDK XGM conversion/playback must be checked.")
    if not loop_offset:
        print("NOTE: no VGM loop marker: verify continuous E1M1 playback in-game.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check_r18_vgm.py /path/to/e1m1.vgm")
    try:
        check(Path(sys.argv[1]))
    except (ValueError, OSError, struct.error) as exc:
        sys.exit(f"ERROR: invalid R18 BGM: {exc}")
