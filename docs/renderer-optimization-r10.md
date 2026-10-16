# DOOM Mega Drive — R10 exact arithmetic matrix

## Baseline
User validated R9 Combined three times at **9.80 FPS**, same DEMO3 2134 frames, 217.72 emulated s, NTSC 60 Hz and BlastEm M68000 divider 7. Visuals confirmed unchanged. 38×24 3D + 4 text HUD rows, fast DIVU and Color LUT, Cache16 WRAM, status-only DMA. Both R9 SLOPE_DIVU and STEP_DIVS flags stay active for all four ROMs.

## Controlled R10 experiments
| ROM | Change relative to R9 Combined |
|---|---|
| doom-md-hud-r10-base.bin | none; reproducibility control |
| doom-md-hud-r10-dist.bin | guarded 68000 DIVU.W for positive 32-bit distance / positive divisor up to 65535, quotient <65536 |
| doom-md-hud-r10-recip.bin | split exact unsigned 32-bit reciprocal numerator 0xffffffff into two long-division 16-bit digits; two DIVU.W instead of generic division when divisor 1..65535 |
| doom-md-hud-r10-combined.bin | both R10 experiments |

The R_PointToDist hot path uses R_PointToDist's original FixedApproxDiv for the cosine index; only the final division changes under the guard. This leaves the same mathematical truncation and low-16-bit return result. Out-of-range values use the original signed division.

FixedApproxDiv uses FixedReciprocalSmall(b) = 0xffffffffu/(uint16_t)b when b<=65535, then FixedMul3232. The two-DIVU division recovers EXACTLY that original 32-bit reciprocal without any rounding change. First compute high quotient and remainder of 0xffff / b, then compute low quotient and remainder of ((rem << 16)|0xffff)/b. The outcome is (qhi<<16)|qlo. The original division-by-zero behavior is not modified.

Python mathematical preflight exhaustively validates all nonzero 16-bit reciprocals and randomly verifies 32/16 distance divisions; actual 68000 instruction encoding is checked by the cross compiler. The runner packages the ELF, disassembly (if available), build logs, flags, and ROMs.

These are hypotheses, NOT measured FPS gains; user checks the four ROMs, visual fidelity, stability, 2134 frames. Compare at BlastEm stock divider 7 (fast-forward 1000% is fine). Do not promote any candidate on a single timing anomaly.
