# R20c natural — base validada no hardware

Commit: 52e2128a71274ccf43d683b8f9cacca93c877b61, branch r20c.
ROM: doom-md-r20c-natural.bin
SHA256: d126a432d9673ec8b6c5861e98aa1c78a056c1687014c2a486eb6851fa9fed44

Configuração: S2/visada iterativa + Flat DBRA R19 + P2/ADDX + M1/tangente MULS; inlining natural. Viewport 38x22, hand1, HUD levantado, cache 16, zona nominal 43 KiB, E1M1, sem espera explícita por VBlank.

| Ambiente / ROM | FPS | Tempo s | Situação |
|---|---:|---:|---|
| BlastEm / control (noinline) | 10,80 | 197,58 | 2134 frames |
| BlastEm / natural | 11,06 | 192,88 | 2134 frames |
| BlastEm / diag natural | overhead | 198,33 | 2134 frames; erro zero |
| Mega Drive / natural | ~10,92 calculados | 195,37 | Daniel confirmou conclusão e validou em 17/10/2026 |

O FPS calculado no hardware usa os 2134 frames esperados da DEMO3 e o tempo informado; a mensagem de validação trouxe o tempo, não a tela final. A orientação do teste foi 7,67 MHz; o usuário não repetiu a frequência nessa mensagem.

Diagnóstico no BlastEm: pico/reserva 2268/2560; erro/tic 0/0; SGDK mínimo livre/bloco 3336/3336; zona 912/528; SP mínimo E0FFF7B2. Watermark com margem de 292 bytes, incluindo custo das sondas. Validação refere-se à demo executada; não houve alteração desta base ao iniciar a R20d.

Artefato original: https://github.com/bollux78/MD-DOOM64KB/actions/runs/38998549865/artifacts/12087699678
