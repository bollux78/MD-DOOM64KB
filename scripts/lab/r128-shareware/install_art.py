#!/usr/bin/env python3
"""Install R128 native assets after the base R30/R78 generators."""
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

assets = Path("assets/r128-shareware")
if not assets.is_dir():
    raise SystemExit(0)

metadata = json.loads((assets / "manifest.json").read_text())
manifest = Path("src/r30_static_manifest.h")
source = manifest.read_text()
asm_path = Path("src/r30_static_data.s")
assembly = asm_path.read_text()
for kind, record in metadata.items():
    files = {part: assets / f"{kind}-{part}.bin" for part in ("map", "pal", "pack")}
    payload = {part: path.read_bytes() for part, path in files.items()}
    for part, data in payload.items():
        if sha256(data).hexdigest() != record["sha256"][part]:
            raise ValueError(f"{files[part]} hash mismatch")

    pack, attrs, palette = (payload[k] for k in ("pack", "map", "pal"))
    count = len(pack) // 32
    if len(pack) % 32 or not 0 < count < 1440 - 16:
        raise ValueError(f"{kind} tiles overlap other VRAM data")
    if len(attrs) != 40 * 28 * 2 or len(palette) != 4 * 16 * 2:
        raise ValueError(f"{kind} requires a 40x28 tilemap with four CRAM palettes")
    if any(word & 0x7FF >= count for word, in struct.iter_unpack(">H", attrs)):
        raise ValueError(f"{kind} tile index out of range")

    for part, data in payload.items():
        output = f"res/r30-{kind}-{part}.bin"
        Path(output).write_bytes(data)
        symbol = f"r30_{kind}_{part}"
        if f"\n{symbol}:\n" not in assembly:
            assembly += f'\n.balign 4\n.global {symbol}\n{symbol}:\n  .incbin "{output}"\n'
    if kind == "title":
        Path("res/r30-title-mapb.bin").write_bytes(attrs)

    constant = f"R30_{kind.upper()}_TILES"
    source, replaced = re.subn(rf"(#define {constant} )\d+u", rf"\g<1>{count}u", source)
    if not replaced:
        source = source.replace("#endif", f"#define {constant} {count}u\n#endif")

manifest.write_text(source)
asm_path.write_text(assembly)
