# Doom SCD Live 3D

A cartridge Mode 1 experiment based on the 03D Word RAM transport. The Sega CD
68000 renders a textured first-person scene from a live camera. The Mega Drive
handles input and presentation. No disc, game WAD or captured frame is used.

The 80 × 56 raycaster writes 2 × 2 pixel blocks directly into 160 × 112 VDP
tiles. It uses one 128 KiB Word RAM bank for the render and one for presentation.
The main CPU publishes the next camera as soon as the banks swap. It waits for
VDP DMA completion before releasing the presentation bank. The first and sixty-fifth
frames are read back from VRAM and compared with the Sub CPU output.

The cartridge opens in autoplay. Press A to switch to manual control. Up and
Down move forward and backward. Left and Right turn. Press A again to restart
autoplay.

Build with `GDK=/path/to/mars/m68k-elf fish build.fish`. The ROM is
`build/doom-scd-visual-3d.bin`. Run it as a Mega Drive cartridge with Sega CD
expansion emulation and a configured BIOS. The CI test builds the ROM and checks
it separately in BlastEm.
