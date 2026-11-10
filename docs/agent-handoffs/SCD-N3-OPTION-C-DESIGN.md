# N3 option C: game logic only on the Sega CD sub

## Why
BlastEm DEMO3 (E1M7, heavy combat), per frame: the sub spends ~270 ms re-running the logic the MD has
already run, while drawing takes ~45 ms plus ~60 ms of sprite waits. With the logic done once, on the
faster CPU (sub at 12.5 MHz without wait states, MD at 7.6 MHz), the MD is free to draw, read input and play sound.

## Measured size of the state (sub counters, DEMO3)
- mobjs alive: ~100 (max 109) in E1M7 combat; ~13 in E1M1.
- sectors whose floor/ceiling/light changed per exchange: ~9 typical (the 170/85 max is the first frame after load).
- Estimated packet: ~1.5 KB typical, under 3 KB worst case; this fits easily in a Word RAM swap.

## Packet (sub -> MD, once per MD frame, latest state)
1. Header (~48 B): gametic, gameaction, player view (x, y, z, viewz, angle, extralight, fixedcolormap),
   psprite states, HUD (health, armor, ammo, weapons, keys, face), damage/bonus counts (palette), message id.
2. Sector deltas: idx u8, floor i16, ceiling i16, light u8, plus floorpic/ceilingpic when they change.
   Wall/flat animation is a function of gametic, so the MD computes it itself.
3. Line/side events: switch textures, line specials cleared (for the automap).
4. Things: x, y, z as i16 map units, angle u8, sprite+frame u16, flags u8 (shadow/fullbright),
   sector u8. That is ~12 B per thing, sent as a full list.
5. Sound events: sfx id, plus an origin (x, y) or the player.

## MD side
- It still loads the level (geometry, textures) and keeps menus, intermission and automap.
- In-level it skips P_Ticker. It applies the packet to its sectors and to a puppet mobj pool,
  relinked into sector thinglists for R_AddSprites, and to the player/HUD; then it plays the sounds and draws.
- Ticcmds keep flowing MD -> sub as they do today; demos are read on the MD.

## Steps
- C1: the sub builds the packet and the MD still runs its logic but compares the packet against its
  own state. The lockstep acts as the oracle, so packet bugs show as diffs.
- C2: the MD stops in-level logic and runs from the packet; HUD and sound come from the packet.
- C3: the split render returns (the sub draws its columns from its own state); then rebalance.
