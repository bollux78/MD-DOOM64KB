# R20a — resultados recebidos em 17/10/2026

Fonte: captura enviada por Daniel, BlastEm. Clock/divisor não reconfirmados nesta mensagem. Todos os resultados completos exibem 2134 frames.

| Variante | Tempo s | FPS mostrado | Pico / reserva | Máscara / primeiro tic |
|---|---:|---:|---:|---|
| control | 202,20 | 10,55 | — | — |
| dbra | 199,62 | 10,69 | — | — |
| stack | travou, illegal instruction | — | — | — |
| render | 204,92 | diagnóstico | 2560 / 2560 | 15 / 7 |
| sight | 207,13 | diagnóstico | 2268 / 2560 | 0 / 0 |
| both | 203,85 | diagnóstico | 2368 / 2560 | 0 / 0 |
| counters | 203,93 | 10,46 (overhead) | — | — |

render: SP mínimo E0FFF4F2, 270 bytes abaixo de MEMORY_HIGH E0FFF600. Há evidência de estouro no build instrumentado e inconsistência SGDK, mesmo terminando. S2 elimina os erros detectados nessa execução. A instrumentação tem seu próprio custo de pilha/layout; não prova a causa de toda trava antiga.

Contadores por frame: TEX_CALLS 59,3; TEX_CELLS 648,0; FLAT_CALLS 39,1; FLAT_CELLS 162,6; WALL_1PATCH 7,2; WALL_MULTI 33,1; WALL_COMPOSED 9,4; TAN16 40,6; TAN32 12,1; SEGS 8,1; SIGHT_CHECKS 0,9. Máximo de filhos pendentes de visada: 10.

Média texturizada 10,93 células/chamada favorece P2. Média flat 4,16 e número menor de flats reduzem a expectativa de R3. O ganho DBRA de 1,29% é do executável completo, incluindo efeitos do LTO. GCC 15.2: R_Subsector control 0x27A0, DBRA 0x2C40, diferença +1184 bytes.
