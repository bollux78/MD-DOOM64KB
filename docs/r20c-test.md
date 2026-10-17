# R20c — P2+M1 com inlining natural

Três ROMs, mesma geometria 38x22, DEMO3, NTSC, cache 16, zona nominal 43 KiB, hand1, HUD levantado, E1M1, sem espera explícita por VBlank. Todas: S2/visada iterativa + flat DBRA + P2/ADDX + M1/tangente MULS. BSP do render continua recursivo.

| ROM | Comparação |
|---|---|
| doom-md-r20c-control.bin | Configuração da R20b combo: colunas noinline. Referência anterior 10,80 FPS / 197,58 s |
| doom-md-r20c-natural.bin | Mesma matemática, sem o atributo noinline nas colunas |
| doom-md-r20c-diag.bin | Natural + diagnóstico de pilha/heaps; FPS tem overhead |

Ordem: diag → natural → control. Mandar foto do diagnóstico e das telas finais. Todas devem completar 2134 frames, sem mudanças visuais observáveis. Se travar, guardar a última tela e nome exato.

Manter clock/divisor idêntico; no hardware, 7,67 MHz. Não comparar FPS do diagnóstico com os benchmarks. O controle reproduz configuração, não identidade binária: nome e cabeçalho R20c diferem, e os ELFs acompanham o ZIP. noinline removido permite decisões normais do LTO; não força inlining e não garante ganho.

Dados do diagnóstico congelados antes da tela final; pico desde main, watermark satura na reserva. Erro zero é uma verificação útil e limitada. Os testes aritméticos executados no build continuam sendo modelos, não execução do asm compilado.
