# R18 Playable — single music-enabled ROM

This branch is an **isolated one-off playable build** based on the hardware-tested R17 DBRA winner, not a replacement for the ongoing `hud` renderer experiments. R12–R17 scripts and ROMs remain intact.

## ROM
- `doom-md-r18-playable-e1m1.bin`
- 38×22 true viewport, R16 Hand1 CRT HUD, R15 SETUPMUL, R17 DBRA (not FRACMUL).
- **No timedemo, no benchmark screen, no automatic playtest**: standard title/menu and normal joypad gameplay.
- User-supplied `e1m1.vgm`, losslessly archived in `assets/r18-e1m1.vgm.xz`. Restored by GitHub Actions, SHA256-verified, converted to XGM by SGDK, then embedded in the ROM.
- Source VGM SHA256: `64a7a0748953a4bd35b75735b9f4b7c1c89c0f3f4aa43395485cadd7e88a8226`.
- First R18 release is **music-only**; sound effects are still disabled (`SFX_SILENT`).
- Music looping must be verified on original hardware. R17 timedemo FPS is **not** a benchmark of R18 with audio.

## Build
The workflow `R18 Playable — E1M1 Music (single ROM)` builds exactly one ROM on the existing self-hosted Mega Drive toolchain runner on push to `r18-playable`.

To rebuild locally on the same runner checkout:

```fish
git switch r18-playable
python3 -c 'import lzma,pathlib;pathlib.Path("res/e1m1.vgm").write_bytes(lzma.decompress(pathlib.Path("assets/r18-e1m1.vgm.xz").read_bytes()))'
set -lx DOOM_R18_BGM_VGM "$PWD/res/e1m1.vgm"
fish scripts/lab/build_r18_playable.fish
```

The other benchmark builds and ongoing optimization work stay in the `hud` branch.

**Music redistribution:** this branch includes the uploaded VGM as an XZ-compressed source asset. Verify any third-party redistribution rights before distributing the music-enabled ROM publicly.
