# R41 Q1 — Primer 4x4 profile manual (20/10/2026)

**Source:** screenshot of user BlastEm DEMO3 completed to 2134 frames. Compare against R41 clean control, the same branch and MOVEP mall.

| Variant | FPS avg | Total | Min/Max 1s | Free/block |
|---|---:|---:|---:|---:|
| `doom-md-r41-control-p4perf` | **3.01** | **709.67 s** | 1.8 / 3.9 | 862 / 862 |
| `doom-md-r41-profile-p4perf` | **2.90** | **735.85 s** | 1.8 / 3.6 | 826 / 826 |

Profiler overhead: (735.85/709.67-1)*100 = **3.69% extra elapsed time**. Never interpret instrumented FPS as gameplay performance.

### Profile samples by stage (%)

| Stage | Sample % |
|---|---:|
| 0 OTHER/LOGIC | 6.5 |
| 1 FRAME SETUP | 0.1 |
| 2 BSP OTHER | 1.7 |
| 3 COLUMN OTHER | 10.5 |
| 4 MASKED | 2.1 |
| 5 VDP WAIT | 0.1 |
| 6 WALL DRAW | **46.3** |
| 7 MULTIPATCH | 1.8 |
| 8 STORE RANGE | 3.2 |
| 9 ADD LINE | 2.9 |
| 10 CHECK BBOX | 1.3 |
| 11 FLAT DRAW | **8.8** |
| 12 SPRITE/FUZZ | 2.8 |
| 13 VRAM UPLOAD | **11.9** |

Grouped sampling shares: WALL+FLAT+SPRITE **57.9%**; VRAM upload **11.9%**; column other **10.5%**. Remaining stages **19.7%** (rounding to 100%).

**Important sampling bias:** Samples are triggered at 60Hz VBlank, NOT cycle-accurate. `R22_UploadBack` masks interrupts while writing tiles, so its 11.9% share may underrepresent actual wall-clock time. Because each sample increments the bucket active when VBlank fires, interruption-boundary aliasing can distort shares. Interpret directionally, and benchmark Q2/Q3 separately.

**Recommendation:** Prioritize **Q2 dedicated 4×4 walls kernel** (pixel4 does not reuse 8x8 asm; `src/r22_video.inc` refuses `DOOM_R20_REG_COLUMNS` and `FLAT_INLINE`). Preserve native 76x44 samples, 1672-byte packed framebuffer, 38-byte stride, nibble-preserving writes and overlaps with sprites/weapon; prove equality by framebuffer hash. Q3 DMA/upload optimization can follow or run parallel on a different branch if a trustworthy timing method is available.

**Q1 CI:** [run 39350173805](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39350173805) ([artifact 12233171284](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39350173805/artifacts/12233171284)); both ROMs booted in BlastEm.

**UI caveat:** The menu ghosting screenshot shows the *old* `r40-fast-pixel4-play` ROM and not `r40c-pixel4-play` or R41 (timedemos only). Validate the newly built R40c play before attributing any menu problem.
