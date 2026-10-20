# R45 controls — compilation and CI results

**Build successfully completed:** [GitHub Actions #39360378906](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39360378906); [artifact 12237107601](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39360378906/artifacts/12237107601). Source SHA at build: `700676f1a8ec7aa7b214748989ed8e84012ba160`.

## Checks passed
- All six ROMs compile and pass a 300-frame BlastEm boot smoke (return code 0).
- ROM header/size/flags/geometry checked, all ROMs **2,752,512 bytes** (real linear image, within 4 MiB).
- Randomized 4×4 packed framebuffer reference test **20,000 columns** passed.
- R44 intermission coordinates tested (38×22 glyphs, 76×44 gameplay); anti-flicker sources preserved.
- 8×8 R39f Dithering Off / Checker / Vertical tables and audio toggles preserved in compiled cell variants.
- R43 gray lookup generated from PLAYPAL; 64 neutral indices, 7 previously mapped to non-gray slots, 43/256 total remapped. Gray CRAM0 representative neutral ramp: `0x000,0x222,0x444,0x666,0x888,0xCCC,0xEEE`.

## ROMs for manual testing

| ROM | Renderer | Palette | Benchmark |
|---|---|---|---|
| `doom-md-r45-cell-perf.bin` | 8×8 R39f | original | DEMO3 2134 frames |
| `doom-md-r45-cell-play.bin` | 8×8 R39f | original | playable |
| `doom-md-r45-asm-p4perf.bin` | 4×4 R44 ASM | original | DEMO3 2134 frames |
| `doom-md-r45-asm-p4play.bin` | 4×4 R44 ASM | original | playable |
| `doom-md-r45-gray-p4perf.bin` | 4×4 R44 ASM | R43 grayscale | DEMO3 2134 frames |
| `doom-md-r45-gray-p4play.bin` | 4×4 R44 ASM | R43 grayscale | playable |

**User tests still pending:** gray vs original at identical E1M1 position and CRT, intermission after E1M1, all three DEMO3 average/min/max results. Do not claim measured R45 FPS or approval of gray until screenshots arrive.

**Important:** these six ROMs still select backends at compile time; the real runtime 8×8↔4×4 switch inside one ROM is a **future M1–M4 engineering task**. Do not describe this CI milestone as a dual renderer runtime implementation.
