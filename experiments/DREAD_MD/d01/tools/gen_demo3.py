#!/usr/bin/env python3
"""Extract original Doom DEMO3 ticcmds on the runner, without shipping the WAD.
Compress consecutive equal commands and blocks of unique commands; decoder runs
directly from ROM and requires no extra RAM buffer."""
import sys, struct, hashlib
from pathlib import Path

def main(wad_path, dst_path):
    wad = Path(wad_path).read_bytes()
    ident, count, directory = struct.unpack_from("<4sII", wad)
    if ident not in (b"IWAD", b"PWAD"):
        raise ValueError("Not a Doom WAD")
    demo = None
    for index in range(count):
        pos, length, name = struct.unpack_from("<II8s", wad, directory + index*16)
        if name.rstrip(b"\0").upper() == b"DEMO3":
            demo = wad[pos:pos+length]
            break
    if demo is None or len(demo) < 14:
        raise ValueError("The supplied WAD has no usable DEMO3")
    version, skill, episode, map_no = demo[:4]
    if episode != 1 or not 1 <= map_no <= 9:
        raise ValueError(f"DEMO3 map {episode}/{map_no} is not available in this E1 C7 build")
    pos = 13 # vanilla Doom header: version, 8 options, 4 player flags
    commands = []
    while pos < len(demo) and demo[pos] != 0x80:
        if pos + 4 > len(demo):
            raise ValueError("Truncated DEMO3 ticcmd")
        commands.append(demo[pos:pos+4])
        pos += 4
    if pos >= len(demo):
        raise ValueError("DEMO3 lacks vanilla Doom end marker")
    packets = bytearray()
    i = 0
    while i < len(commands):
        rep = 1
        while i+rep < len(commands) and commands[i+rep] == commands[i] and rep < 128:
            rep += 1
        if rep >= 3:
            packets.append(0x80 | (rep-1))
            packets.extend(commands[i])
            i += rep
            continue
        start = i
        i += 1
        while i-start < 128 and i < len(commands):
            rep = 1
            while i+rep < len(commands) and commands[i+rep] == commands[i] and rep < 3:
                rep += 1
            if rep >= 3:
                break
            i += 1
        packets.append(i-start-1)
        for cmd in commands[start:i]:
            packets.extend(cmd)
    # Roundtrip-check exactly the original per-tic commands.
    decoded = []
    at = 0
    while at < len(packets):
        op = packets[at]; at += 1
        n = (op & 127) + 1
        if op & 128:
            c = packets[at:at+4]; at += 4
            decoded.extend([bytes(c)]*n)
        else:
            decoded.extend(bytes(packets[at+4*k:at+4*k+4]) for k in range(n))
            at += n*4
    assert decoded == commands
    dst = Path(dst_path)
    fragments = []
    for k in range(0, len(packets), 24):
        fragments.append("    " + ",".join(f"0x{x:02x}" for x in packets[k:k+24]) + ",")
    dst.write_text(
        "/* Auto-generated from local WAD DEMO3: no original WAD is checked in. */\n"
        "#include <stdint.h>\n"
        f"static const uint8_t demo3_map = {map_no};\n"
        f"static const uint8_t demo3_skill = {skill};\n"
        f"static const uint32_t demo3_tics = {len(commands)}u;\n"
        f"static const uint32_t demo3_pack_bytes = {len(packets)}u;\n"
        "static const uint8_t demo3_packed[] = {\n"
        + "\n".join(fragments) + "\n};\n"
    )
    print(f"DEMO3: WAD version={version}, E{episode}M{map_no}, skill={skill}, "
          f"{len(commands)} tics, compressed={len(packets)} bytes, "
          f"SHA256={hashlib.sha256(demo).hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: gen_demo3.py WAD OUTPUT_HEADER")
    main(sys.argv[1], sys.argv[2])
