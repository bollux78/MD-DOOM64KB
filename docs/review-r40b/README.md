# R40b — Anti-flicker native title/intermission text

Based on R40a `r40a-pixel4-menu-overlay`, with R39c dual MOVEP, R39e independent Music/SFX, native R22 76x44 4x4 renderer, and R35 Bayer8 screens. R40a fixed ghosting but cleared the WINDOW each frame, causing noticeable text blink.

## Change
`src/r22_video.inc` now holds an 836-byte previous-glyph cache and 105-byte drawn-this-frame bitset in 68000 WRAM, **only for native static screen overlays**. Each text string writes to WINDOW VRAM only for characters whose ASCII glyph changed. When the frame is ready, obsolete glyph positions receive the transparent tile index 0, revealing the original artwork. Unchanged characters remain visible throughout the frame. The same lifecycle covers Options cursor, ON/OFF labels, and intermission/level transition count strings.

When an R35 native picture is first shown or replaced, `src/r35_native4.inc` invalidates the cache because WINDOW VRAM has been cleared; closing the menu still clears/hides the WINDOW once. No full WINDOW clear is performed between ordinary text frames. WINDOW writes stop before row 22 to protect 0xFC00's SAT/HScroll.

## Validation
- Open Start > Options over TITLEPIC; move cursor up/down 10 times, toggle Music/SFX repeatedly. **No flicker, stale arrows, or overprinted ON/OFF.**
- Close/reopen the menu, repeat; title Bayer8 background should remain undisturbed.
- Finish E1M1 to display WIMAP0 intermission; during the kills/items/secrets counting observe no overprint or blinking. E1M2 still loads normally.
- Compare pixel4-perf result against R40-fast-pixel4-perf, original 3.01 FPS / 708.37 s / 2134 DEMO3 frames.
- Audio controls must work on/off while in PLAY; original 4x4 resolution and geometry unchanged.

There is no automated pixel-exact menu input replay in this build. Headless BlastEm smoke does not prove that dynamic text flicker is fixed; check manually.
