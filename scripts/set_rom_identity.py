#!/usr/bin/env python3
"""Generate matched Genesis ROM header and on-screen identity.

SGDK's makefile.gen uses src/rom_header.c to generate out/rom_header.bin.
Keep this entirely inside the Doom source checkout (never edit SGDK).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
ID_PATTERN = re.compile(r"doom-md-[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="e.g. doom-md-r4-cache8-perf")
    args = ap.parse_args()
    identity = args.id.strip()
    if len(identity) > 30 or not ID_PATTERN.fullmatch(identity):
        ap.error("expected a short lowercase doom-md-... name (max 30 chars)")

    def field(value: str, length: int) -> str:
        if len(value) > length or not value.isascii():
            raise ValueError(f"Invalid ROM field {value!r}")
        return '"' + value.ljust(length) + '"'

    display = identity
    # Normal linear 4 MiB Mega Drive mapping, no SSF / bank switching.
    rom_end = '0x003FFFFF' if identity.startswith(('doom-md-r35-', 'doom-md-r35d-', 'doom-md-r37-', 'doom-md-r38-', 'doom-md-r39b-')) else '0x001FFFFF'
    title = identity  # Keep case identical to the ROM filename and demo screen
    note = "DOOM MD 68000 RENDERER BENCHMARK"

    # Keep layout and memory map the same as SGDK's stock ROMHeader.
    rom_header = f"""/* Auto-generated; edit scripts/set_rom_identity.py instead.
 * SGDK makefile.gen copies this header into ROM at $100..$1FF. */
#include <genesis.h>
__attribute__((externally_visible))
const ROMHeader rom_header = {{
#if (MODULE_MEGAWIFI && (MEGAWIFI_IMPLEMENTATION == MEGAWIFI_IMPLEMENTATION_MW_CART))
    "SEGA MEGAWIFI   ",
#elif (ENABLE_BANK_SWITCH != 0)
    "SEGA SSF        ",
#else
    "SEGA MEGA DRIVE ",
#endif
    "(C)SGDK 2026    ",
    {field(title, 48)},
    {field(title, 48)},
    "GM 00000000-00",
    0x000,
    "JD              ",
    0x00000000,
#if (ENABLE_BANK_SWITCH != 0)
    0x003FFFFF,
#else
    {rom_end},
#endif
    0xE0FF0000,
    0xE0FFFFFF,
    "RA",
    0xF820,
    0x00200000,
    0x0020FFFF,
    "            ",
    {field(note, 40)},
    "JUE             "
}};
"""
    identity_header = (
        "/* Auto-generated; same variant as the Genesis ROM header. */\n"
        "#ifndef DOOM_BUILD_IDENTITY_H\n"
        "#define DOOM_BUILD_IDENTITY_H\n"
        f'#define DOOM_BUILD_TITLE "{display}"\n'
        "#endif\n"
    )
    (ROOT / "src" / "rom_header.c").write_text(rom_header, encoding="ascii")
    (ROOT / "src" / "doom_build_identity.h").write_text(identity_header, encoding="ascii")
    print(f"Build identity: {identity}")
    print("Genesis ROM domestic/international title: " + title)


if __name__ == "__main__":
    main()
