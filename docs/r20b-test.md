# R20b — S2 como candidata de estabilidade; P2 e M1 isolados

Todas: DEMO3/2134 frames esperados, NTSC, zona nominal 43 KiB, viewport 38x22, HUD levantado, hand1, cache 16, E1M1, sem espera explícita de VBlank. Todas incluem visada iterativa S2 e o flat DBRA da R19. BSP do render permanece recursivo. Nenhuma R2/R3/R4 ou mudança de resolução/DMA foi habilitada.

| ROM | Finalidade |
|---|---|
| doom-md-r20b-control.bin | Controle S2+DBRA com colunas noinline |
| doom-md-r20b-p2.bin | Mesmo controle + ADD/ADDX |
| doom-md-r20b-m1.bin | Mesmo controle + tangente MULS.W |
| doom-md-r20b-combo.bin | Mesmo controle + P2 + M1 |
| doom-md-r20b-diag.bin | Combo com sondas de pilha/heaps; FPS tem overhead |
| doom-md-r20b-natural.bin | S2+DBRA com inlining natural; referência do executável completo |

## Ordem

1. diag: se terminar, fotografar pico/reserva, erro/tic e heaps. E=0 é desejável, mas não prova ausência de todo defeito.
2. control, p2, m1, combo: fotografar telas finais e observar paredes, céu, arma e sprites.
3. natural: comparar a melhor ROM experimental com esta referência e com R20a-dbra (10,69 FPS no teste recebido).

Para poucos testes: diag → control → combo. P2 e M1 separados ficam para identificar a contribuição individual. Clock/divisor idêntico em todas; no hardware, 7,67 MHz. Diagnóstico não serve para ranking de FPS.

noinline é igual nos quatro testes para limitar mudanças do grafo de chamadas; não fixa todo o layout do LTO. natural é propositalmente diferente e deve ser considerada uma comparação separada. O relatório registra símbolos e versões; não promete identidade de código.

Testes aritméticos M1/P2 são executados antes do build. Eles não executam o asm compilado nem substituem validação visual/estado do jogo. Todos os ELF correspondentes, flags e hashes estão no ZIP.

Se travar, fotografar a última tela e informar o nome exato da ROM. Não concluir estabilidade apenas por ter completado a demo.
