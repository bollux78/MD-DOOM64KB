# R20f — combinação sem R3

Mesmo código da R20e; apenas nova matriz de flags. Base R20d R2 validada no hardware em 193,87 s. R3/FLAT_UNROLL e R4 desligadas em todas as ROMs; Flat DBRA original mantido.

| ROM | Opções novas |
|---|---|
| control | Nenhuma; referência R2 |
| hud | HUD sob demanda |
| all | HUD + FPS sob demanda + M3 escala + S3 BSP render iterativo |
| diag | Mesma combinação de all + diagnóstico de pilha/heaps |

Ordem: diag → control → hud → all. Usar mesmo clock/divisor; todas devem completar 2134 frames. Guardar tela de diagnóstico e resultados de tempo/FPS mínimo, médio e máximo. diag tem overhead; seu tempo não compara com os demais. A combinação ainda depende da validação completa no emulador e no hardware.

## Resultados R20e no BlastEm (imagem do usuário)

| ROM | FPS médio | Mín. | Máx. | Tempo (s) |
|---|---:|---:|---:|---:|
| control | 11,15 | 4,8 | 18,7 | 191,43 |
| hud | 11,33 | 4,8 | 19,0 | 188,32 |
| fps | 11,18 | 4,9 | 18,7 | 190,88 |
| m3 | 11,25 | 4,7 | 18,7 | 189,63 |
| s3 | 11,22 | 4,8 | 18,7 | 190,23 |
| r3 | 10,87 | 4,7 | 18,4 | 196,23 |
| all | 11,24 | 4,9 | 19,4 | 189,93 |

Todas: 2134 frames. Diagnóstico R20e/all: 193,25 s, pilha 2368/2560, erro 0/tic 0, SGDK 3124/3124, zona 912/528, SP E0FFF872. HUD foi a melhor isolada. R3 piorou isoladamente; o novo pacote testa a combinação sem ela. Ganhos das demais opções não são necessariamente aditivos.

Observar HUD ao mudar saúde/armadura/munição e ao alternar telas/automapa; FPS após mensagens; paredes/perspectiva e oclusão/sprites. Evidências nativas e probe MC68000 são os mesmos da R20e, pois o código de produção não mudou. math-probe.raw é teste de CPU, não ROM de jogo, e não substitui teste do jogo completo.
