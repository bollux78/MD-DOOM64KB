# R115 — can R114 depth and subiv savings accumulate?

Base: exp-chatgpt-r114-exact-20261102, 2b14b55. Keep R113 image, colours, menus, Shadow toggle/crop, AI Normal benchmarks, and R104 SRAM/IRQ protection.

## Evidence

User screenshot, E1M1 AI Normal Shadow Off:

| ROM | seconds | mean FPS | minimum 1S FPS |
|---|---:|---:|---:|
| R113 hilut | 249.28 | 8.56 | 3.7 |
| R114 depth | 248.37 | 8.59 | 3.8 |
| R114 subiv | 248.32 | 8.59 | 3.8 |

Each individual saves about 0.9s. Independent time savings would predict 247.41s (8.625 FPS), approximately 0.75% less time than this user's control. This is a prediction, NOT a measured combined result. Minimum FPS values cannot be added.

Original run 41486845409: depth and subiv passed six complete DEMO3 post-pass comparisons, 2,132 compared frames each after startup, zero differing frames in E1M1 Off/On A2/L3 and E1M7 On A2/L3. ROM/BSS/stack guards passed. Emulator time savings were ~0.28%/0.44% respectively in E1M1 Off, ~0.47% each in E1M7 On. Hardware results above take precedence.

## Compatibility and experiment

Depth changes R_ProjectSprite's three bounded integer divisions into exact ROM lookups; subiv applies optimize("no-ivopts") to R_Subsector. Different functions, no semantic conflict. Layout, LTO and register allocation still require measuring the actual combination: code compatibility alone does not prove additive speed.

The combo applies both transformations once to the complete R113 chain, delivers r115-combo-pl, and adds no state/approximation. Rebuild control, depth, subiv, combo in the same job. Require published R113 and original R114-single hashes to match. Compare all six fixtures, full-demo stack, and matched slow-frame windows. Report measured combined savings beside predicted independent savings in combo-SUMMARY.json/interaction. Do not change the default AI, render resolution, palettes, or SRAM wrappers.

## Diagnostic observations (not gameplay changes)

Two other original experiments stopped in the comparison harness due to repeated debugger marker stops, NOT a proven pixel difference: sprite L3 On repeats tic 863, subos E1M7 L3 repeats tic 295. Repeated stops have identical framebuffer hash and benchmark frame counter; the second is one VBlank later. The R115 capture coalesces ONLY identical frame/state repeats and preserves the first stop's timing. Nonidentical repeats still fail. Sprite's measured gain was tiny and subos was slower; neither is in this combination.

The full E1M1 Off worst control window was frames 2046..2049: R_Subsector 25/64 VBlank-PC samples, map reads 6/64 (IRQ bias), sound propagation 4/64, scale 4/64. One small window is not a robust whole-function profile.

The worst E1M7 window includes G_DoLoadLevel and map writes around frames 1614..1616. The raw benchmark minimum therefore includes a level reload. Keep the existing benchmark intact and mark windows containing sampled reload work in the host report. A different raw minimum can result from shifting the 1-second boundaries; inspect the SAME frame intervals before claiming better gameplay minimum FPS.

Final acceptance remains console E1M1 Off/On and E1M7 On plus visual review, not emulator timing alone.
