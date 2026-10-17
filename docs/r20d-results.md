# R20d R2 — base validada no hardware

Commit 9afc0e46bb3229022cbedb0665dfbd77241e7caa, ROM doom-md-r20d-r2.bin.
SHA256 fa9de31cfc564b0d0bfafd7cb01d79c2868f79d4e11cc9e64d414377b6762a95

| Variante | BlastEm FPS | Tempo s |
|---|---:|---:|
| control (R20c natural) | 11,06 | 192,88 |
| R2 | 11,15 | 191,43 |
| R4 | 11,04 | 193,38 |
| R2+R4 | 11,12 | 191,87 |

Todas as telas completas exibem 2134 frames. R2 ganhou 0,76%; R4 perdeu 0,26% e fica desligada. Diagnóstico da combinação: pico/reserva 2268/2560, máscara/tic 0/0, SGDK mínimo 3312/3312, zona 912/528, SP mínimo E0FFF7F2.

Daniel confirmou sucesso da R2 no hardware em 193,87 s em 17/10/2026. Considerando 2134 frames: ~11,01 FPS calculados. Contra a R20c no mesmo hardware (195,37 s), ganho de 0,77%. A instrução foi testar a 7,67 MHz; a mensagem de confirmação trouxe apenas o tempo.

Base preservada: S2 + Flat DBRA + P2 + M1 + R2; inlining natural; 38x22, cache 16, hand1, HUD levantado, E1M1, zona nominal 43 KiB, sem espera explícita por VBlank.
