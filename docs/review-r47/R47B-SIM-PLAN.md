# R47B-SIM: plane-pair and MiSTer / Nuked-MD preflight

Base branch: r47a-flat-hoist-plane-pair-oracle, commit 0f212f01ee8e150a8c5cd369e20eb09df4adb8cc.
This stage does NOT build any ROM, switch the renderer, change SGDK, or claim RTL DMA accuracy.
The R47A optimization passed CI, but its runtime FPS, visual equivalence and hardware approval are still pending.

## Purpose and evidence tiers

1. Source-level and host simulation: verify 76x44 pixels, VRAM ownership, two-plane VScroll mapping, WINDOW menu difference, DMA byte counts.
2. Provenance / tool readiness: fetch pinned Nuked-MD YM7101 RTL source, check its Git blob SHA and elaborate with Icarus/Verilator if available. This is NOT physical VDP simulation.
3. Future RTL testbench: drive register and cart / RAM buses of an actual RTL board, measure DMA completion relative to VBlank, generate VCD and JSON traces.
4. Later opt-in ROM: only after adequate confidence, build R47B-PAIR with a distinct flag and retain SHA-locked 8x8 Primary / 4x4 R45 ASM controls.

## Exact external reference

MiSTer project: https://github.com/MiSTer-devel/MegaDrive_MiSTer
Pinned commit: becbdee78c48e6eb536871cd03c869f43d7afa4d
Source: rtl/nuked-md/ym7101.v
Git blob SHA-1: 0862948114ddb7abec87e46fdbb16d4fa2172804

Nuked-MD hardware source: https://github.com/nukeykt/Nuked-MD-FPGA
Nuked-MD C software emulator: https://github.com/nukeykt/Nuked-MD

The YM7101 Verilog has roughly 215 KB of implementation logic and explicit DMA/FIFO circuit sections. The hardware modelling is valuable, but the project's own Progress.md still notes incomplete testing and fixes for CPU, VDP and arbiter. The CI must not misrepresent RTL source inspection/elaboration as a timing result.

## Discovered fault risk in the external standalone prototype

The existing R22 standalone setup has A=E000, B=E000, Window=F000, HScroll/SAT=FC00. Its minimum map start E000 places the dynamically positioned SGDK font in D400..DFFF.

The proposed prototype changes B to D000 but keeps Window=F000 and HScroll/SAT=FC00. The minimum map address becomes D000; the SGDK font moves from D400..DFFF to C400..CFFF. This is a FONT RELOCATION, with SGDK font decompression and heap pressure, not a direct overlapping of B with the font.

The prototype uses Window=F000. Window rows 24..31 alias FC00 and beyond (HScroll/SAT). Do not write or DMA-clear those rows. Any resulting red/black screen or corrupted font triggers code/documentation investigation, not another blind remap.

For a future dual 8x8 and plane-pair mode, the non-moving map proposal is A=E000, B=C000, Window=D000, HScroll=F000, SAT=F400, minimum map base C000, font B400..BFFF (tiles 1440..1535). Existing static 8x8 art can reside at tiles 16..241; 256 pair patterns at tiles 256..511, with no overlap. Actual coexistence and SGDK initialization still need integration tests.

## Plane-pair semantics, precisely bounded

The proposed 256 immutable patterns each encode an 8-bit palette pair in their top 4 scanlines; the bottom 4 scanlines are transparent. BG_A uses pixel-row 2r at VScroll=0; BG_B uses pixel-row 2r+1 at VScroll=-4. Transparent A pixels reveal B, reconstructing the legacy pixel4 image in 21 graphical map rows (38 columns each). Row 0 and unused bottom rows use the original glyph/HUD semantics.

Python tests compare all 304x224 pixels of 48 randomized framebuffers (including transparent palette index zero, top text and color pairs) with an independent representation of legacy R22 dynamic tiles.

The difference with the Window is deliberate: when a menu overlays gameplay, its transparent glyph pixels reveal odd rows only in plane B. Blacking out B beneath the Window may be aesthetically acceptable but is NOT pixel-identical to the original. This must be a visible explicit choice, not silently labelled as exact.

## Transfer model — 42 separate DMA commands

Legacy 4x4 dynamic patterns require up to 798*32 = 25536 B per frame.
Plane-pair requires 256*32 = 8192 B patterns once on init/after native artwork.
Every frame sends two planes x 21 rows x 38 words = 3192 B using 42 DMA commands (76 B each).

The nominal 7200 B/NTSC VBlank bulk capacity DOES NOT prove these 42 commands finish before VBlank exit. Register command costs, FIFO, Z80 bus arbitration, CRAM and other VDP consumers remain unmodelled until a real RTL/bus bench measures them.

RAM: legacy framebuffer 1672 + map 1596 = 3268 B.
Standalone plane-pair framebuffer 3344 B (+76).
A dual renderer can potentially split 22 rows (1672 B each) into existing 8x8 screen and R20 heap snapshot, each 2128 B, but this is a design hypothesis and must be validated for ISR/DMA lifetime.

## Deliverables and acceptance

Workflow: .github/workflows/r47b-sim.yml
- R47B-VRAM-PIXEL-DMA.json: exhaustive host pixel equivalence and layout, explicit menu discrepancy and DMA envelope.
- R47B-MISTER-RTL.json: pinned source integrity, optional tool availability and RTL elaboration result.
- No ROM ZIP; this stage does not consume user time on manual BlastEm tests.
- The CI must fail on layout or pixel mismatch and on upstream source integrity mismatch.
- If RTL compilers are missing, the report must plainly say RTL NOT RUN; never claim actual bus/DMA cycles validated.

Next proposed work is R47B-RTL for a small, real VDP bus/DMA testbench; then R47B-PAIR for standalone opt-in Mega Drive ROM benchmarking, preserving the approved baselines. R47C/D font and runtime toggle only after hardware and menu ownership are understood.

Every severe black/red screen, heap header error, font corruption or unstable DMA calls for investigation of installed SGDK, source-level RTL and hardware literature BEFORE another correction.
