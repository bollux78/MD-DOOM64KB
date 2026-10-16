#!/usr/bin/env python3
"""R18 source and VGM validator preflight. No copyrighted music required."""
from pathlib import Path
import importlib.util
import struct
import tempfile

root = Path(".")
build = (root / "scripts/lab/build_r18_playable.fish").read_text()
audio = (root / "src/i_genesis.c").read_text()
doom = (root / "src/d_main.c").read_text()
video = (root / "src/i_genesisv.c").read_text()
assert "set -gx DOOM_TIMEDEMO 0" in build
assert "set -gx DOOM_R17_PIXEL_DBRA 1" in build
assert "set -gx DOOM_R17_FRAC_MULU 0" in build
assert "set -gx DOOM_R16_HUD_UP2 1" in build
assert "set -gx DOOM_R16_WEAPON_LIFT 1" in build
assert "set -gx DOOM_R15_SETUPMUL 1" in build
assert "DOOM_R18_BGM_VGM" in build
assert "check_r18_vgm.py" in build
assert "rm -rf out" in build
assert "XGM_startPlay(bgm_e1m1)" in audio
assert "XGM_setLoopNumber(looping ? -1 : 0)" in audio
assert "const boolean nomusicparm = false" in doom
assert "#if defined(TIMEDEMO)" in video
assert "DOOM_R17_PIXEL_DBRA" in video

spec = importlib.util.spec_from_file_location(
    "check_r18_vgm", root / "scripts/lab/check_r18_vgm.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "test.vgm"
    raw = bytearray(512)
    raw[:4] = b"Vgm "
    struct.pack_into("<I", raw, 4, len(raw) - 4)
    struct.pack_into("<I", raw, 8, 0x150)
    struct.pack_into("<I", raw, 0x2c, 7670454)
    struct.pack_into("<I", raw, 0x18, 44100)
    struct.pack_into("<I", raw, 0x34, 0x0c)
    raw[0x40:0x46] = bytes((0x52, 0x28, 0x00, 0x62, 0x66, 0x66))
    p.write_bytes(raw)
    module.check(p)
    p.write_bytes(raw[:73])
    try:
        module.check(p)
    except ValueError:
        pass
    else:
        raise AssertionError("silent placeholder accepted as real E1M1 VGM")
print("PASS: R18 playable flags, R17 DBRA, audio path and VGM safety preflight")
