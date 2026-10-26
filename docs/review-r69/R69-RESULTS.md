# R69 — matriz de tamanho de janela (run 40333315226, branch exp-claudio-r69-window-matrix-20261026)

Diagnóstico. ROMs instrumentadas (R68), mesmos 342 tics do DEMO3 em todas as variantes. Use razões, não FPS absoluto.
Controle R66 reconstruído == original (cmp OK). BSS: R66 57.900 B; instrumentadas 57.904 B (teto 57.920).

| variante | janela (amostras 4x4) | pixels | vb/quadro | FPS eq. | vs 16/16 |
|---|---|---:|---:|---:|---:|
| w00 (sem crop) | 74x42 | 3108 | 14,41 | 4,16 | -13,7% |
| w08 | 70x38 | 2660 | 13,40 | 4,48 | -7,2% |
| w16 (= R66) | 66x34 | 2244 | 12,44 | 4,82 | 0 |
| w24 | 62x30 | 1860 | 11,50 | 5,22 | +8,2% |
| w32 | 58x26 | 1508 | 10,65 | 5,63 | +16,7% |
| h32 16/16 | 56x34 | 1904 | 11,20 | 5,35 | +11,0% |

Leitura:
- Cada passo de crop de 4 amostras por lado vale ~+7-8% de FPS. Aplicado ao baseline de 7,21 FPS: w24 ~7,8; h32 ~8,0; w32 ~8,4.
- O ganho é bem menor que a redução de área (w32 tem -33% de pixels vs w16 e só +16,7% de FPS): grande parte do tempo por quadro não escala com a janela (lógica ~7-10%, BSP/setup por segmento, vídeo/VBlank).
- Só cortar janela não chega a 10 FPS; precisa somar com redução de trabalho por coluna/quadro.
