# R20g — resultados do usuário no BlastEm, 17/10/2026

ROMs do run 39036770009, commit c58f7c716be57669f193a41e8e0ca65c5dda4f5c. Todas as concluídas: 2134 frames.

| Variante | Média FPS | Mínimo | Máximo | Tempo s |
|---|---:|---:|---:|---:|
| control | 11,54 | 4,7 | 19,4 | 184,90 |
| color | 11,54 | 5,0 | 19,0 | 184,90 |
| cache | 11,59 | 5,0 | 19,4 | 184,13 |
| r4b | 11,43 | 4,8 | 19,0 | 186,65 |
| r5 | 11,64 | 4,9 | 19,0 | 183,40 |
| r6 | 11,59 | 4,9 | 19,0 | 184,20 |
| m2 | 11,56 | 4,9 | 19,0 | 184,55 |
| p3 | 11,52 | 4,8 | 19,4 | 185,18 |
| m4 | 11,53 | 4,9 | 19,4 | 185,02 |
| v3 | 11,83 | 4,9 | 20,0 | 180,32 |
| render | 11,61 | 4,8 | 19,0 | 183,85 |

Diagnósticos: 11 concluídos, todos os visíveis com erro0/tic0 e pico2368/2560. color confirmou +512 B SGDK (3636 vs3124); cache confirmou +128 B (3252).

Falhas, reproduzidas nas ROMs sem diagnóstico: sprites, ram, ram-render com Z_Malloc falhando ao alocar904B; s5 congelou na imagem da demo (diag chegou ao T02134). Por eliminação com diag-color posteriormente fornecida, as três travas sem nome são ram-v2, ram-v2-v3 e full. Elas combinam V2 e SPRTEMP_DYNAMIC; não se isolou ainda a causa das travas.

R4b e P3 ficam desligadas por perda medida; M4 fica fora da rodada de desempenho por não apresentar ganho nesta execução. Não se inclui S5, V2 nem SPRTEMP_DYNAMIC na R20h. A reserva de pilha não aumenta com RAM livre do SGDK. Nenhum desses resultados constitui confirmação no hardware.
