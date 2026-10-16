# R18 — Playable Doom with E1M1 VGM music

**Baseline:** R17 DBRA (BlastEm NTSC divider 7: 10.55 FPS, 202.23 s for 2134 frames), confirmed running on original Mega Drive hardware. Do not enable R17 FRACMUL: it was slower.

**R18 changes:** Disable TIMEDEMO and automatic PLAYTEST, retain R16 Hand1 38x22 CRT geometry/HUD, R15 SETUPMUL, R17 DBRA, no explicit VSync, and all previous stable renderer flags. Use normal Doom title/menu, joystick controls and gameplay. SGDK rescomp converts the supplied Mega Drive VGM to XGM, and the existing XGM driver plays it on the title screen and in E1M1. SFX remain silent for this first music-only build because the external doom1.wad samples have not been supplied.

## Supply music locally (do not commit VGM to the public repository)

On the **self-hosted runner machine** (same Linux PC):

```fish
mkdir -p ~/Projetos/doom-assets
cp /caminho/para/seu/e1m1.vgm ~/Projetos/doom-assets/e1m1.vgm
```

Then open GitHub Actions > **HUD R18 Playable E1M1 music** > **Run workflow** (branch `fullscreen`). The job checks out `hud` and embeds the VGM. Artifact: `doom-md-r18-playable-e1m1`.

Or build from the source checkout directly:

```fish
cd ~/Projetos/MD-DOOM64KB
git pull origin hud
set -lx DOOM_R18_BGM_VGM ~/Projetos/doom-assets/e1m1.vgm
fish scripts/lab/build_r18_playable.fish
```

ROM: `dist/r18-playable/doom-md-r18-playable-e1m1.bin`.

## Important notes

- The original VGM is **not** stored in GitHub source; the runner must read it from the external path. This avoids accidental replacement by the old silent placeholder.
- The build validates the VGM header, rejects a tiny silent placeholder, forces a fresh rescomp conversion and records the input SHA256.
- The existing audio code already calls `XGM_startPlay(bgm_e1m1)` and sets infinite looping when Doom requests it. Confirm actual looping on hardware; the source VGM may lack loop markers.
- Controls: directional pad moves/turns, B fires, A uses/accepts, C+left/right strafes, Start opens the menu.
- Music timing and video smoothness must be verified on real hardware: the R17 FPS numbers came from a **timedemo with a silent VGM**, not from this new audio workload.
- PCM SFX can be added in a later round using an external `doom1.wad`; they are not part of this initial build.
