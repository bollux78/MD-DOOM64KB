# R50 — confirmed causes of menu ghosting and warm-reset state loss

## Reproduced user symptoms

- In R50 native static-art menus, old menu item labels and skull positions remain drawn when moving or changing a menu, despite the attempt to restore underlying title tilemap cells.
- In R50 after a soft reset during a benchmark, some runs display black only; others return to a title that no longer responds to Start. Previous attempts merely disabling SRAM and re-enabling VDP failed.
- Previously validated: Pair-V Fast ~5.30 FPS PLAY on DEMO3 and freeze-renderer-menu responsive; benchmark in PLAY completes and returns to menu/new game when **not** using reset.

## Cause 1: R40b occupancy state aliases the viewport buffer

**Proven code-path bug** in `src/r22_video.inc`:

- `r40b_native_prev` and `r40b_native_seen` are two bitsets overlaid onto `r22_fb.pixels` to conserve WRAM.
- `M_Drawer()` invokes `I_InitScreenPage()` whenever a menu is drawn.
- `I_InitScreenPage()` used to call `V_ClearViewWindow()` unconditionally.
- `V_ClearViewWindow()` calls `R47_ClearPairBuffer()`, wiping `r22_fb.pixels` including the two occupancy masks.
- `R40B_PruneNativeText()` sees no *previous* glyph occupancy; it cannot restore displaced native-art tiles. Ghost text accumulates after cursor movement/submenu transitions.

**Fix:** in `V_ClearViewWindow()`, return immediately if native art is active and `DOOM_R50_STATIC_MENU` is enabled. The static picture is entirely in VDP VRAM and needs no raster framebuffer clear. The two masks now survive until `R40B_PruneNativeText()` compares them with the freshly collected mask for this frame. Existing BG_A direct text + ROM tilemap restoration remains unchanged.

**Invariant:** while `r35_native_active>=0`, do not reuse, clear or overwrite the Pair-V framebuffer except deliberately resetting both masks upon first entry. Maintain 320x224 art, HUD/footer outside menu viewport and no added WRAM.

## Cause 2: SGDK soft reset does not clear all WRAM

**Confirmed from SGDK upstream code:**

- `src/boot/sega.s` transfers a soft reset to `_reset_entry`, not `_start_entry`.
- `src/sys.c`: `_reset_entry()` calls `internal_reset()` then `main(FALSE)`, but `_start_entry()` performs a complete 64 KiB RAM clear and copies initialized `.data` from ROM before calling `main(TRUE)`.
- `src/sys.c`: `internal_reset()` ALREADY calls `SRAM_disable()` and waits for VDP DMA BUSY to clear before initializing video.
- `src/sys_a.s`: `SYS_hardReset()` jumps to `_start_entry` after setting up the stack and halting the Z80.

Sources:
- https://github.com/Stephane-D/SGDK/blob/master/src/sys.c
- https://github.com/Stephane-D/SGDK/blob/master/src/sys_a.s
- https://github.com/Stephane-D/SGDK/blob/master/src/boot/sega.s

**Likely mechanism:** Doom and SGDK retain old global/static state across `main(FALSE)`: input last-state, game tics, framebuffer aliases, native-art active ID, event queues, menu state, etc. These state remnants can produce a title with nonfunctional menu and missing rendering.

**Experimental correction:** `DOOM_R50_HARD_REINIT` in the *first statements* of `main(bool hardReset)` calls `SYS_hardReset()` only when `!hardReset`. That enters `_start_entry()`, resets initialized state and returns via `main(TRUE)` once. It does not change hard-power-on behavior.

**Limits:** if `internal_reset()` hangs before `main(FALSE)`, the C-entry correction cannot run. Sega's Software Manual documents VDP DMA in-flight at CPU reset as a separate concern. If soft reset is **still** black, investigate boot-entry patch or DMA fault separately, only with a tightly scoped binary/assembly experiment.

## A/B batch: `r50-native-menu-mask-fix`

Five PLAY ROMs, all Pair-V Fast, with Benchmark and no-3D menu:

- `vf-prev-play`: previous native menu experiment + previous SRAM-only reset hack.
- `vf-mask-play`: guard occupancy-mask lifetime only.
- `vf-reinit-play`: full SGDK WRAM initialization on soft reset only; previous Window-based menu.
- `vf-both-play`: both confirmed menu fix + experimental complete soft reboot. **Main candidate.**
- `cm50l-both-play`: same with R49 50/50 ColorMix + composed LUT.

Do not promote until manual QA verifies native title menu without ghost labels, closing/reopening the menu, gameplay freeze responsiveness, returning from benchmark, and a real soft-reset during DEMO3.

## Historical decision

Pair-H remains only a single historical reference (no routine Pair-H ROM builds). R50 VF baseline must remain preserved independently.
