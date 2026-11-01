# R105 Cell8 PLAY

Experimental playable derivative of R105 twoface, pinned to
`9b5996d6a439dac7e1683f3a4d3d4d87efe88ac1`.

The scene renderer uses the existing 38-column / 22-row projection. Each
scene sample covers an 8x8 screen tile. This is direct lower-resolution
rendering, not a 76x44 render followed by a reduction pass.

The current Pair-V presentation is retained: each scene colour feeds the
even and odd palette maps, with the same value in both vertical nibbles.
Consequently, palette mixing/dither may still be visible *inside* an 8x8
sample. This is not a restoration of the historical single-palette renderer.

Unchanged production components: HUD, high-quality static pictures, menu,
fonts, music, sound, AI Normal/Low selector, save/load, A2/L3 selector,
cropped SH1 Shadow On/Off, and R104 SRAM interrupt masking. AI defaults to
Normal; Shadow defaults to Off. Geometry and sprite sizes use the old
38x22 projection, including its rounding differences from the 76x44 mode.

R95 per-seg flat lookup, R96 per-seg composed wall lookup, R98 sprite
multiplication and R105 twoface specialisation are retained/adapted. The
4px R60 wall kernel is replaced by full-cell writes. R66 approximate
neighbour reuse is disabled in the scene: 8px columns are sampled independently.

Only the PLAY ROM is intended for delivery. The PERF twin is used internally
to exercise actual drawing in BlastEm. The automated capture is a partial
smoke test, not proof of full-map stability or a hardware performance result.

On hardware, test E1M1 and E1M7 with Shadow Off/On, A2/L3, view sizes,
weapons/sprites, automap, save/load and return from menus/static screens.
Use AI Normal for comparative benchmarks. Keep backups of cartridge saves.

No FPS gain is claimed until measured. The R104 workaround is retained,
but the new derivative still requires testing on the affected cartridge.
