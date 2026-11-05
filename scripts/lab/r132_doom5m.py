#!/usr/bin/env python3
"""R132: repackage a PRIVATE R128 All ROM into a 5 MiB SSF2 compatibility probe.

This is a layout/boot test, NOT an in-game >4 MiB bank-read test.
No WAD/ROM bytes are checked into the public repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

SIZE = 5 * 1024 * 1024
BANK = 512 * 1024
HEADER_SYSTEM = slice(0x100, 0x110)
HEADER_END = 0x1A4
CHECKSUM = 0x18E


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    src = args.input.resolve(strict=True)
    dst = args.output.resolve()
    report = args.report.resolve()
    if src == dst or src == report or dst == report:
        ap.error("input, output and report must be distinct")
    if dst.is_relative_to(Path.cwd().resolve()) or report.is_relative_to(Path.cwd().resolve()):
        ap.error("output/report must be outside current public checkout")
    data = src.read_bytes()
    if not 0x400 <= len(data) <= 4 * 1024 * 1024:
        ap.error("input ROM must fit in original 4 MiB space")
    if data[0x100:0x104] != b"SEGA":
        ap.error("invalid Genesis ROM header")
    new = bytearray(SIZE)
    new[:len(data)] = data
    old_system = bytes(new[HEADER_SYSTEM])
    new[HEADER_SYSTEM] = b"SEGA SSF".ljust(16, b" ")
    struct.pack_into(">I", new, HEADER_END, SIZE - 1)
    # Stamp only extended 512 KiB pages 8, 9; leave 0..4 MiB untouched except header/checksum.
    for p in range(8, 10):
        pos = p * BANK
        pattern = sha256(b"R132-EXTRA-5M-DOOM" + bytes([p])).encode()
        for i in range(pos, pos + BANK, len(pattern)):
            new[i:min(i + len(pattern), pos + BANK)] = pattern[:min(len(pattern), pos + BANK - i)]
        new[pos:pos + 12] = b"R132-EXTRA-" + bytes([48 + p % 10])
    checksum = sum((new[i] << 8) | new[i + 1] for i in range(0x200, SIZE, 2)) & 0xFFFF
    struct.pack_into(">H", new, CHECKSUM, checksum)
    assert len(new) == SIZE
    # Verify absolutely no modifications to executable ROM except 0x100 system, 0x18E checksum and 0x1A4 end.
    allowed = set(range(0x100, 0x110)) | {0x18E, 0x18F, 0x1A4, 0x1A5, 0x1A6, 0x1A7}
    unexpected = [i for i in range(len(data)) if data[i] != new[i] and i not in allowed]
    if unexpected:
        raise RuntimeError(f"unexpected original-ROM mutation at 0x{unexpected[0]:X}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(new)
    r = {
        "name": dst.name,
        "variant": "r128-all-pl-ssf2-5m",
        "size_bytes": SIZE,
        "sha256": sha256(new),
        "input_sha256": sha256(data),
        "input_size_bytes": len(data),
        "system_original": old_system.decode("ascii", "replace"),
        "system_new": new[HEADER_SYSTEM].decode("ascii"),
        "rom_end": SIZE - 1,
        "checksum": checksum,
        "extra_banks": [8, 9],
        "verification": "first 4 MiB byte-identical outside ROM header fields",
        "limitation": "no bank switching during gameplay; boot compatibility only; emulator PASS does not validate X7 clone or 5 MiB content access",
    }
    report.write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
