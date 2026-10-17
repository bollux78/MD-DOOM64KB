# R20b — resultados recebidos em 17/10/2026

Fonte: duas capturas de Daniel, BlastEm. Clock/divisor não reconfirmados nas mensagens. Todas as telas completas exibem 2134 frames.

| Variante | FPS | Tempo s | Ganho sobre controle pelos tempos |
|---|---:|---:|---:|
| control (S2+DBRA, noinline) | 10,51 | 202,97 | — |
| p2 | 10,70 | 199,48 | +1,75% |
| m1 | 10,62 | 201,02 | +0,97% |
| combo | 10,80 | 197,58 | +2,73% |
| natural (S2+DBRA, sem P2/M1) | 10,72 | 199,03 | +1,98% |
| diag (combo + sondas) | não comparar | 202,93 | overhead |

combo: mínimo 4,5 FPS, máximo 18,7 FPS. Contra natural, ganho +0,73%. Somatório das economias isoladas 5,44 s; economia combinada 5,39 s.

Diagnóstico: pico/reserva 2268/2560, erro/tic 0/0, SGDK mínimo livre/bloco 3336/3336, zona mínimo livre/bloco 912/528, SP mínimo E0FFF82E. Não detectou erro nessa execução; inclui custo/layout da instrumentação e não constitui prova geral de ausência de corrupção.

Próxima pergunta: P2+M1 com inlining natural supera a combo de 10,80 FPS e continua sem erros detectados? R20c testa apenas isso.
