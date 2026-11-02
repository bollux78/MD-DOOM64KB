# R114 — isolated exact-image experiments after R113

Authorized by the user 2026-11-02. Base e35345b / R113 hilut run 41464372009.
R113 remains the reference; no colour, menu, AI behaviour or Shadow decisions are reopened.

## Candidates (never combined in this first battery)

* `depth`: three exact sprite-projection tables, integer distance 4..1280. Values are precisely the original C divisions: xscale, yscale, reciprocal(xscale). Separate arrays, 15,372 ROM bytes; no new BSS. Full fixed-point tz remains in fracstep. Native compiled-C reference verifies all integer distances and fractional boundaries.
* `sprite`: R113 pre-shifted high-nibble kernel for R_DrawColumnSprite, ONLY when R52_LUT returns a composed LUT with the existing shifted twin. Arbitrary maps retain R60; fuzz unchanged. No new tables.
* `subos`: only R_Subsector gets GCC optimize("Os").
* `subiv`: only R_Subsector gets GCC optimize("no-ivopts").

## Runner sequence

First rebuild the unchanged R113 PLAY/PERF and require both published SHA256 hashes to match. Then capture the entire 2,134-frame DEMO3, including late E1M1, with one VBlank-PC sample per interrupt and actual benchmark-window counters. Run E1M1 Off/On A2/L3 and E1M7 On A2/L3. Then build and compare each candidate against those same-job controls. Every fixture must reach G_CheckDemoStatus at the end of the timedemo; a partial run cannot pass.

E1M7 PERF is an explicitly labelled test-only fixture (same DEMO3 input on E1M7 geometry). Its `map = 7` change is compile-time, isolated from delivery PLAY and from the E1M1 PERF. PLAY keeps the original benchmark-map menu.

The minimum in the existing benchmark is **1S (one second), not 15 frames**: a window closes at elapsed >= 60 VBlanks. Record actual frame/window counters and compare also the SAME frame intervals, because candidate speed shifts window boundaries. Profiler is biased immediately after IRQ unmasking; do not treat SRAM samples as unbiased. Emulated VBlank timing is triage, not console approval.

Capture is after R92_AfterPass for all modes, with byte-for-byte comparison of 3344 framebuffer bytes. Paint only the unused stack reserve using the established R82 method; measure through the complete demo, not tic 400. The first two tics are excluded from pixel comparisons while the GDB one-time colour selection takes effect. No ROM profiling code or new RAM counters are added.

BSS <= 57,920 and ROM <= 4 MiB. SRAM windows, original SR restoration, and the entire R104 protection remain unchanged. Control is bit-identical; each candidate differs in one named experiment. Candidates are copied to play/ only after all six fixtures pass. Read each candidate's SUMMARY for status and timing. No new combined/final base is declared automatically.

Final console validation: E1M1 AI Normal Shadow Off/On, E1M7 AI Normal Shadow On; check both colour modes visually. Low AI remains an optional gameplay setting, never a benchmark shortcut. Prefer >0.5% repeatable hardware benefit, especially in matched slow windows, over emulator noise.
