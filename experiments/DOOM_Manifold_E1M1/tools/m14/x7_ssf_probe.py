#!/usr/bin/env python3
"""Hardware-only EverDrive X7 SSF2 in-game menu bisection.

Uses the EXACT previously hardware-verified 128 KiB static ROM from Tile Palette
Studio (synthetic tiled graphics only); no Doom copyrighted assets, WAD, or music.

These variants are probes, NOT Manifold release builds. Every variant keeps
the same validated VBlank IRQ handler and two-phase pad polling. The header,
file length and SSF/SRAM register activity are varied independently.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import struct
import sys

MIB = 1024 * 1024
# Git object SHA of diagnostics/x7/x7_static_test.bin from known working tree.
BASE_GIT_BLOB = "756e378beb7bcff36f156ccd797f2de2a0c253e2"
BOOTSTRAP = 0x20000  # beyond the entire canonical 128 KiB base; fixed mapper slot zero
BANK_PORTS = tuple(0xA130F3 + 2 * i for i in range(7))
SRAM_PORT = 0xA130F1


def be32(value: int) -> bytes:
    return struct.pack(">I", value)


def move_b_imm(addr: int, value: int) -> bytes:
    # MOVE.B #imm, absolute-long (68000)
    return struct.pack(">HHI", 0x13FC, value & 0xFF, addr)


def check_baseline(b: bytes) -> None:
    blob = hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
    if blob != BASE_GIT_BLOB:
        raise ValueError("Expected the tested X7 static ROM (git blob SHA mismatch): " + blob)
    if len(b) != 128 * 1024:
        raise ValueError("Baseline must be exactly 128 KiB")
    if b[0x100:0x110] != b"SEGA MEGA DRIVE ":
        raise ValueError("Baseline header mismatch")
    pc = int.from_bytes(b[4:8], "big")
    irq = int.from_bytes(b[0x78:0x7c], "big")
    if pc != 0x200 or not (0x200 <= irq < len(b)):
        raise ValueError("Baseline reset/VBlank vectors invalid")
    if b"\x00\xa1\x00\x03" not in b[irq:irq+128]:
        raise ValueError("Baseline does not poll control port at VBlank")


def set_checksum(b: bytearray) -> None:
    words = array("H")
    words.frombytes(b[0x200:])
    if sys.byteorder == "little":
        words.byteswap()
    b[0x18e:0x190] = struct.pack(">H", sum(words) & 0xFFFF)


def build(baseline: bytes, megabytes: int, ssf: bool, banks: bool = False,
          sram: str = "none") -> bytes:
    if megabytes == 0:
        return baseline
    if megabytes not in (4, 8, 12):
        raise ValueError("Unsupported size")
    if banks and not ssf:
        raise ValueError("Bank writes need SSF mode")
    out = bytearray(b"\xFF") * (megabytes * MIB)
    out[:len(baseline)] = baseline
    out[0x100:0x110] = b"SEGA SSF        " if ssf else b"SEGA MEGA DRIVE "
    out[0x1a4:0x1a8] = be32(len(out) - 1)
    if banks or sram != "none":
        # The base ROM remains otherwise identical. This is a bootstrap
        # executed from slot 0; it tail-jumps to the original reset entry.
        stub = bytearray()
        if banks:
            for i, addr in enumerate(BANK_PORTS):
                stub.extend(move_b_imm(addr, i + 1))
        if sram == "toggle":
            stub.extend(move_b_imm(SRAM_PORT, 1))
            stub.extend(move_b_imm(SRAM_PORT, 0))
        elif sram == "on":
            stub.extend(move_b_imm(SRAM_PORT, 1))
        elif sram != "none":
            raise ValueError("Invalid SRAM mode")
        stub += b"\x4e\xf9" + be32(0x200)  # JMP 68000 fixed program entry
        out[BOOTSTRAP:BOOTSTRAP+len(stub)] = stub
        out[4:8] = be32(BOOTSTRAP)
    set_checksum(out)
    return bytes(out)


VARIANTS = (
    ("x7-a-original-128k", 0, False, False, "none",
     "Exact hardware-proven control. Menu + save/load should work."),
    ("x7-b-md-4m", 4, False, False, "none",
     "Normal MD header, 4 MiB padded with FF."),
    ("x7-c-ssf-4m", 4, True, False, "none",
     "SSF header only, identical 4 MiB ROM length."),
    ("x7-d-ssf-8m", 8, True, False, "none",
     "SSF header, 8 MiB; no mapper register accesses."),
    ("x7-e-ssf-12m", 12, True, False, "none",
     "SSF header, 12 MiB; no mapper register accesses."),
    ("x7-f-md-12m", 12, False, False, "none",
     "Normal MD header but 12 MiB; compares length vs SSF mode."),
    ("x7-g-ssf-12m-banks", 12, True, True, "none",
     "SSF 12 MiB, explicit identity writes to all seven bank registers."),
    ("x7-h-ssf-12m-sram-toggle", 12, True, False, "toggle",
     "SSF 12 MiB, enable then disable SRAM via A130F1."),
    ("x7-i-ssf-12m-sram-on", 12, True, False, "on",
     "SSF 12 MiB, leave SRAM enabled via A130F1."),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.baseline.read_bytes()
    check_baseline(source)
    args.out.mkdir(parents=True, exist_ok=True)
    reports = []
    for name, size, ssf, banks, sram, explanation in VARIANTS:
        payload = build(source, size, ssf, banks, sram)
        target = args.out / (name + ".bin")
        target.write_bytes(payload)
        end = int.from_bytes(payload[0x1a4:0x1a8], "big")
        reset = int.from_bytes(payload[4:8], "big")
        irq = int.from_bytes(payload[0x78:0x7c], "big")
        assert end == len(payload)-1 or size == 0
        assert irq == int.from_bytes(source[0x78:0x7c], "big")
        assert reset == (BOOTSTRAP if banks or sram != "none" else 0x200)
        assert payload[0x100:0x110] == (
            b"SEGA SSF        " if ssf else b"SEGA MEGA DRIVE ")
        report = {
            "file": target.name, "bytes": len(payload), "ssf": ssf,
            "banks": banks, "sram": sram, "sha256": hashlib.sha256(payload).hexdigest(),
            "purpose": explanation,
        }
        reports.append(report)
        print(report["file"], report["bytes"], report["sha256"])
    (args.out/"manifest.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=False) + "\n")
    readme = [
        "MEGA EVERDRIVE X7 — DIAGNÓSTICOS SSF / 12 MiB",
        "",
        "Estas ROMs têm apenas gráficos geométricos sintéticos e NÃO contêm DOOM.",
        "Todas derivam da mesma ROM de 128 KiB cujo menu X7 e Save/Load",
        "foram confirmados no hardware do usuário (controle x7-a).",
        "",
        "TESTE no Mega Drive + X7 real, sem 32X:",
        "1. Execute x7-a e confira Baixo+Start e Save/Load.",
        "2. Para cada variante: confirme imagem geométrica colorida,",
        "   pressione Baixo+Start, anote se LED acendeu, se o menu abriu",
        "   e se Save/Load funcionaram (se existir o menu).",
        "3. Uma variável de cada vez; reporte a PRIMEIRA variante que falhou.",
        "",
        "NÃO é correção definitiva do Manifold. Emuladores não testam o",
        "menu interno do cartucho X7. As variantes SRAM ON podem alterar",
        "temporariamente o mapeamento, sem gravar dados pessoais.",
        "",
    ]
    for r in reports:
        readme.append(f"{r['file']}: {r['purpose']}")
    (args.out/"LEIA-ME.txt").write_text("\n".join(readme)+"\n")


if __name__ == "__main__":
    main()
