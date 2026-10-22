#!/usr/bin/env python3
"""R54 source-level safety gate for isolated PLAY cadence experiments."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
sys=(ROOT/'src/i_genesis.c').read_text()
main=(ROOT/'src/d_main.c').read_text()
hud=(ROOT/'src/r22_video.inc').read_text()
identity=(ROOT/'scripts/set_rom_identity.py').read_text()
assert 'return ticcount * TICRATE / 60;' in sys, 'real time clock changed'
assert re.search(r'int32_t I_GetGameTime\(void\).*?return \(ticcount \* DOOM_R54_LOGIC_HZ\) / 60;',sys,re.S)
assert main.count('R54_LOGIC_TIME()') >= 5
assert '#define R54_LOGIC_TIME() I_GetTime()' in main
assert '#define R54_LOGIC_TIME() I_GetGameTime()' in main
assert main.count('r54_game_tics++;')==2
assert "R22_DrawText(VDP_BG_A,label,1,0)" in hud
assert "'doom-md-r54-'" in identity
rates=(35,28,24,21,18,15,12)
# Rational 60Hz VBlank clock generates exactly hz logical tics per second.
for hz in rates:
    seq=[v*hz//60 for v in range(0,601)]
    assert all(y>=x for x,y in zip(seq,seq[1:]))
    assert all(seq[(k+1)*60]-seq[k*60]==hz for k in range(10))
# Drift-free nominal comparison; do not confuse this with measured TPS.
print("R54 PASS: 35Hz system clock intact, 7 logical rates, separated G_Ticker counts, HUD display.")
