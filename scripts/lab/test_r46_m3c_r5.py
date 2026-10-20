#!/usr/bin/env python3
"""R46 M3C R5: isolated heap allocation lifetime barrier.

The original R3 control code must compile exactly without R5 define.
Only M3C with the flag may postpone allocating R20's 2128-byte
immutable DMA snapshot until VDP/font restoration is completed.

This test checks source-level control flow; visual correctness, SGDK
heap headers and timing are assessed by ROM/BlastEm runtime tests.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
video=(root/'src/i_genesisv.c').read_text()
builder=(root/'scripts/lab/build_r35_linear.fish').read_text()
routine=video.split('void I_InitGraphicsHardwareSpecificCode(void)',1)[1].split('void I_ShutdownGraphics(void)',1)[0]
assert 'DOOM_R46_M3C_LATE_BUFFER' in routine
assert 'DOOM_R46_M3C_DIAG' in routine
assert 'DOOM_R21_V2_HEAPBUF' in routine
assert 'DOOM_R46_M3C_LATE_BUFFER) && (!defined(DOOM_R46_M3C_DIAG)' in routine
assert 'defined(DOOM_R21_V2_HEAPBUF) && !defined(DOOM_R46_M3C_LATE_BUFFER)' in routine
assert routine.count('I_R21_AllocVideoCopy();')==2
assert routine.count('R46_M3C_ShowVideoTest(')==1
assert routine.index('I_R21_AllocVideoCopy();') < routine.index('R46_M3C_ShowVideoTest(')
assert routine.index('R46_M3C_ShowVideoTest(') < routine.rindex('I_R21_AllocVideoCopy();')
assert routine.index('R46_M3C_ShowVideoTest(') < routine.index('R20_InvalidateVideo();', routine.index('R46_M3C_ShowVideoTest('))
# R20 submission must never dereference an unallocated snapshot before it
# is pending: VBlank publisher returns on !ready and no present occurs in
# I_InitGraphicsHardwareSpecificCode before deferred allocation.
assert 'if(!r20_video_ready) return;' in video
assert 'r20_video_copy = MEM_alloc(VIEWWINDOWWIDTH * VDP_DISPLAY_ROWS * sizeof(uint16_t));' in video
assert 'R20_Present(' not in routine
assert "set defs $defs '-DDOOM_R46_M3C_LATE_BUFFER'" in builder
assert 'doom-md-r46-r5-late-safe' in builder
assert 'doom-md-r46-r5-late-stress' in builder
assert 'DOOM_R46_M3C_FONT_RESTORE' in builder
assert len('doom-md-r46-r5-late-stress')<=30
print('R46 M3C R5 PASS: delayed allocation only after 4x4 diagnostic/font/VRAM restore; old R3 untouched')
