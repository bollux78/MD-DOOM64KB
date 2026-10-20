# R46 M2C/P2D — world-to-camera sprite transforms (staged)

Base: P2C accepted on three ROMs including real hardware validation in progress.
P2B previously measured 11.80 FPS control vs 11.78 FPS experimental.
Do not assume the subsequent P2C timings without an explicit report.

Added pure Q16.16 world-to-camera transform with fixed-point view sine/cosine and
overflow checks; chaining into 76x44 sprite rectangle projection. This is an
intermediate geometry contract, not patch selection, sorting, masked draw,
visplane render, native BSP traversal or live-resolution dispatcher.
64-bit intermediate arithmetic is currently used for correctness and may
be too expensive for the 68000 hot loop: optimize and benchmark BEFORE wiring it.

M2C/P2D gating: run host oracle, build primary+M2C performance+PLAY variants;
audit linked symbols, BSS, headers and ROM length; BlastEm 300 frames;
compare complete DEMO3 against last known reference and test hardware.

**Workflow deliberately manual-only**: wait for explicit user permission to
start the self-hosted runner; do not add a push trigger to the P2D workflow.
