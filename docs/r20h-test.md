# R20h — combinações completas sobre V3 + color

Código de produção igual à R20g. Só muda a matriz de flags e a identidade das ROMs. São 20 variantes com 20 diagnósticos correspondentes, em um único ZIP.

Base comum: R20f-all (S2/S3, P2, M1/M3, R2, HUD/FPS sob demanda, Flat DBRA, cache16, 38x22, hand1, E1M1, zona43KiB, sem espera explícita por VSync).

**Referências BlastEm:** control184,90s; color184,90s; V3 isolada180,32s. Esperados2134 frames em todas. Hardware ainda precisa ser validado.

## Nomes e opções

`vc` significa **V3 + color em ROM**. `vc-all` reúne R5 + cache + R6 + M2 sobre V3/color. `c` significa composição direta no cache; não confundir com color. Cada nome possui uma ROM diag-NOME com as mesmas opções mais diagnóstico.

| Sufixo após doom-md-r20h- | Opções adicionais à base comum |
|---|---|
| control | nenhuma; controle R20f-all |
| color | color |
| v3 | V3 |
| vc | V3 + color |
| vc-r5 | V3 + color + R5 |
| vc-c | V3 + color + cache |
| vc-r6 | V3 + color + R6 |
| vc-m2 | V3 + color + M2 |
| vc-r5-c | V3 + color + R5 + cache |
| vc-r5-r6 | V3 + color + R5 + R6 |
| vc-r5-m2 | V3 + color + R5 + M2 |
| vc-c-r6 | V3 + color + cache + R6 |
| vc-c-m2 | V3 + color + cache + M2 |
| vc-r6-m2 | V3 + color + R6 + M2 |
| vc-r5-c-r6 | V3 + color + R5 + cache + R6 |
| vc-r5-c-m2 | V3 + color + R5 + cache + M2 |
| vc-r5-r6-m2 | V3 + color + R5 + R6 + M2 |
| vc-c-r6-m2 | V3 + color + cache + R6 + M2 |
| vc-all | V3 + color + R5 + cache + R6 + M2 |
| no-v3 | color + R5 + cache + R6 + M2 |

As 16 ROMs vc cobrem todos os subconjuntos de R5/cache/R6/M2: nenhum, quatro isolados, seis pares, quatro trios e os quatro juntos. no-v3 contém color+R5+cache+R6+M2, para verificar a contribuição de V3 na combinação completa.

## Ordem de teste

1. diag-control → control, depois diag-v3 → v3; conferir as referências da sessão.
2. diag-vc → vc. Comparar vc com v3 verifica color na base com DMA em lote.
3. Os quatro isolados vc-r5, vc-c, vc-r6 e vc-m2; sempre diag-NOME antes de NOME.
4. Os seis pares, quatro trios e vc-all; a tabela acima lista todos em ordem.
5. no-v3 e color são controles adicionais. Usar seus diagnósticos correspondentes.

Guardar nome, máscara/tic, pico/reserva, heaps e SP do diagnóstico; tempo e FPS mínimo/médio/máximo da ROM de desempenho. Todas devem completar2134 frames. Diagnóstico tem overhead e não serve para classificar FPS. Passar uma demo não prova estabilidade em todos os mapas.

Comparar com o controle da mesma sessão/clock. No hardware, 7,67MHz, começar pelas aprovadas no emulador e observar música/PCM, HUD, paredes, chão/teto, sprites e arma. V3 modifica acesso ao VDP/Z80; desempenho no BlastEm ainda não comprova som e timing no console.

R3/R4/R4b/P3/M4/S5/V2/SPRTEMP_DYNAMIC permanecem desligadas em todas estas ROMs. color libera512B estáticos e cache128B; não há nova alocação temporária na zona nem snapshot VBlank.

## Verificações

Builds limpos por ROM, flags exatas, conjunto completo 2^4, headers, hashes, ELF e layout acompanham o pacote. Os testes de cobertura WAD, cache e probe MC68000 da R20g são reexecutados; o motor não foi modificado nesta rodada. evidence/*.raw é teste de CPU, não jogo. O guia R20g-resultados.md registra os resultados e as falhas que motivaram a seleção.
