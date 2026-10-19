# R39e — Independent Music and SFX toggles (R39d dither retained)

Base: `r39d-dither-toggle` (8x8 R35d checkerboard, R39c **mall** MOVEP: cache + SRAM map).
Reference: `r39d-toggle-cell-perf` 11.80 FPS / 180.82 s, DEMO3 2134 frames, NTSC 60 Hz, original 7.67 MHz CPU.

## User controls in PLAY
- Start > Options > **Dithering: On/Off**, unchanged from R39d.
- Start > Options > **Music: On/Off** (new): A switches music only. OFF sends `XGM2_pause`; ON sends `XGM2_resume`. Music is paused instead of reloaded from the beginning. The state is respected across track/level transitions.
- Start > Options > **SFX: On/Off** (new): A toggles all Doom PCM SFX. OFF immediately stops PCM channels 2 and 3, and subsequent `DMX_Play` calls are skipped. PCM channel 1 (reserved for soundtrack) is not touched.
- The three toggles are independent and default to ON after boot. Their state persists across levels in the current session but not after console power-off.
- Existing gameplay controls A=use, B=fire, C=strafe, Start=menu unchanged. Do not consume controls when menu closed.

## Source integration
- `src/r39e_audio.h`: public toggles (compiled with `DOOM_R39E_AUDIO_TOGGLES`).
- `src/i_genesis.c`: XGM2 pause/resume and direct PCM SFX gate. Existing song tracking `mus_playing` remains unchanged; new `r39e_song_active` tracks whether to send resume/pause.
- `src/m_text.c`: new entries in existing Options menu.
- Static art (R30 Bayer8) is independent and never affected by 3D dithering toggle.

## Clean A/B
- `doom-md-r39e-control-cell-perf.bin`: R39d-style 8x8 runtime dithering, MOVEP mall, audio toggles **not compiled**.
- `doom-md-r39e-audio-cell-perf.bin`: Same baseline, plus Music/SFX option code, both ON. The DEMO3 cannot access the menu; input and image should match control.
- `doom-md-r39e-audio-cell-play.bin`: The playable variant with all three switches.

## Important qualifications
- Song pause/resume preserves position but FM envelopes may lose notes until the next key-on; that is a known XGM2 behavior.
- A currently playing soundtrack PCM hit may end naturally shortly after pausing music; new music PCM events stop with the sequencer.
- Turning OFF Music or SFX is a functional audio test, **not** a guarantee of improved 68000 FPS (XGM2 mixing runs primarily on Z80).
- Initial ROM smoke is not a full playtest. Check menu appearance (seven Options rows), independent combinations of three toggles, switching E1M1/E1M2, SFX while Music OFF and music while SFX OFF, and returning to game.
- Before EverDrive testing, back up SRAM. MOVEP SRAM code remains experimental until hardware-tested.

## About 4x4
The actual `DOOM_R22_PIXEL4` renderer (76x44 independent samples, 1672-byte packed framebuffer, two VDP banks and distinct palette/VRAM upload) is **compile-time mutually exclusive** with the 38x22 tilemap/column writer: see `src/i_genesisv.c` and `src/r22_video.inc`. Merely adding a menu boolean would not switch the renderer. Runtime 8x8 ↔ 4x4 requires a significant dual-backend refactor: allocate both render buffers within limited work RAM; unify or dispatch all public video entry points and dependent `R_Draw*` functions; reinitialize VDP layouts, CRAM/tile banks, view geometry/scaling, weapons, text HUD and DMA; handle mapper and SRAM; and make switches between frames, with in-flight VBlank DMA fully drained. Do not claim a true 4x4 toggle exists in R39e.
