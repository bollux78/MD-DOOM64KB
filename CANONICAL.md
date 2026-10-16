# MD-DOOM64KB — FULLSCREEN

**Canonical Fullscreen line**, restored directly from R6 commit
`1a22afd71829769c3b9a4c2f940c76ed70f15989`.
This is the **sramasm-perf** variant of R6, *not* R6 SRAM C
(`sram16-perf`), not R7 and not later SRAM tests.

- Screen: 38x28 cells, **no HUD**.
- Cache: 16 columns stored in cartridge **odd-byte-lane SRAM**.
- Copy: 68000 assembly `DBRA` fast copy (`DOOM_SRAM_FASTCOPY=1`).
- Zone heap: 43 KiB. No hot RAM slots.
- `FAST_DIVU`, `CELL_LUT`, `NO_VSYNC`, DEMO3 benchmark.
- Recorded working ROM: `doom-md-r6-sramasm-perf` **~8.86 FPS**,
  2134 frames, BlastEm NTSC 60Hz at normal 68000 frequency.
- Recorded ROM is a benchmark reference, not a guarantee that every
  rebuild has identical binary/layout behaviour.

Rebuild only this variant:

```fish
fish scripts/lab/build_fullscreen.fish
~/Projetos/blastem64-1.0.0/blastem dist/fullscreen/doom-md-fullscreen-sramasm-perf.bin
```

The canonical build wrapper preserves the original internal ROM identity
(`doom-md-r6-sramasm-perf`) and reproduces
the verified R6 compiler options. Source renderer/cache logic is
unchanged from R6. Original physical hardware behaviour of cartridge
SRAM depends on your flashcart's odd-byte SRAM support, so verify
there before assuming compatibility.

Repository branch policy: retain only `fullscreen` and `hud`.
