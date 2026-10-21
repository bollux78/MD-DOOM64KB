# R48 Pair-V (columns): geometry proof and implementation contract

Status: **model only**. No Pair-V ROM has been compiled or validated yet.

## Retain reference
- Branch `r47-pair-bootfix` is the independent Pair-H baseline: 4.71 FPS / 453.22 s.
- Preserve the 210 B native-text framebuffer aliasing bootfix.
- The R48 Pair-V test is independent and must never silently change Pair-H.

## Proposed vertical geometry
- 76x44 logical pixels, 4x4 screen pixels per sample.
- Framebuffer is 3344 B, pitch 76 B = 38 VDP map words.
- Each big-endian word = `0x0100 | ((top_color << 4) | bottom_color)`.
- Even logical columns go in Plane A (even framebuffer rows).
- Odd logical columns go in Plane B (odd framebuffer rows).
- Logical y-pairs are stored in the same nibble byte, not adjacent bytes.
- Framebuffer word row: `2 * (y >> 1) + (x & 1)`.
- Word column: `x >> 1`; nibble chosen by **y parity**, not x parity.
- Pair fixed tile index = 256 + byte. Tile left 4 pixels opaque and right 4 transparent.
- Rows 0..3 of pattern = high nibble color, rows 4..7 = low nibble color.
- Plane B HScroll = +4 px relative to Plane A (SGDK positive means rightward).
- VScroll A/B = 0.
- 2 planes x 22 name-table rows x 38 words x 2 bytes = 3344 B if all rows uploaded; preserving the current skipped first row gives 3192 B/frame.

## Host proof
`python3 scripts/lab/test_r48_pair_v_geometry.py --frames 40`

The oracle checks all 256 tile patterns, 40 randomized/structured 76x44 frames, exact A/B compositing with +4 HScroll, and the unused 304..319 px right margin. Test addresses all 4x4 pixels, not only a single representative sample.

## Non-negotiable caveats
- The existing R47 wall/sprite/flat kernels choose a nibble from **x parity** and increment their pixel pointer by 76 B on each y step. Those kernels are NOT directly compatible with Pair-V. They need independently guarded vertical-pair loops, where the two y samples share one byte and move to the next byte-row after two logical pixels.
- Existing `R22_Put` also chooses nibble from x parity. A Pair-V implementation must change that with a compile-time flag.
- WINDOW text and native 320x224 art must restore HScroll(B) to zero during native art and +4 when returning, without breaking the framebuffer's 210 B scratch reuse.
- A valid geometry oracle does NOT validate VBlank DMA timing, effects of priority/transparency/palette bits, sprite interleaving or hardware revisions.
- Pair-V is initially about *equivalence*, not RGB blending. Only after PLAY/PERF and hardware confirmation should color mixing modes be added.
- Keep Pair-H as an artifact control and preserve equal audio/build flags in A/B tests.

## Research
The published SGDK `vdp_bg.h` contract states that positive horizontal scroll values move the plane to the right. Confirm this against the pinned SGDK revision used by the project and actual Mega Drive before final acceptance.

Reference:
https://stephane-d.github.io/SGDK/vdp__bg_8h.html
