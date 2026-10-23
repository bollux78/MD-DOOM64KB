#!/usr/bin/env python3
"""Source and numeric oracle for the isolated R54D 12.5Hz (25/2) pilot.

This tests scheduling maths only: not a claim of full physics normalization,
smoothness, or higher rendered FPS.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
system=(root/'src/i_genesis.c').read_text()
main=(root/'src/d_main.c').read_text()
hud=(root/'src/r22_video.inc').read_text()
build=(root/'scripts/lab/build_r35_linear.fish').read_text()
assert 'return ticcount * TICRATE / 60;' in system
assert 'return (ticcount * DOOM_R54_LOGIC_HZ) / (60 * DOOM_R54_LOGIC_DIV);' in system
assert 'r54d_fraction += 35 * DOOM_R54_LOGIC_DIV;' in main
assert "DOOM_R54_LOGIC_DIV=2" in build
assert '"L12.5 TPS00"' in hud
n,d=25,2
frames=list(range(60*120+1))
scheduler=[(v*n)//(60*d) for v in frames]
assert scheduler[0]==0
assert scheduler[60]==12 and scheduler[120]==25
assert all(b-a in (0,1) for a,b in zip(scheduler,scheduler[1:]))
assert [scheduler[k*120] for k in range(0,61)]==[k*25 for k in range(0,61)]
assert scheduler[7200]==1500
# 35/12.5 -> 2.8 simulated tic units, distributing 2 and 3 per step.
fraction=0
steps=[]
for i in range(500):
    fraction+=35*d
    step=fraction//n
    fraction%=n
    assert step in (2,3)
    steps.append(step)
assert sum(steps)==1400 and steps.count(3)==400 and steps.count(2)==100
print('R54 12.5Hz PASS: 25/2 exact VBlank cadence; 120 seconds => 1500 tics.')
print('Compensation maths: 500 calls => 1400 simulation units (partial only).')
