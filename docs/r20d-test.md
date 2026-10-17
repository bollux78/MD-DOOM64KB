# R20d — reaproveitar trabalho por coluna/segmento

Base: R20c natural validada no hardware com tempo informado de 195,37 s. Todas as ROMs preservam S2+Flat DBRA+P2+M1, inlining natural, DEMO3, viewport 38x22, cache 16, zona nominal 43 KiB, hand1, HUD, E1M1 e ausência de espera explícita por VBlank.

| ROM | Mudança sobre a base |
|---|---|
| doom-md-r20d-control.bin | Nenhum bloco novo; configuração R20c natural |
| doom-md-r20d-r2.bin | Memo do colormap/cellmap |
| doom-md-r20d-r4.bin | Resolve patch de textura simples uma vez por segmento |
| doom-md-r20d-combo.bin | R2 + R4 |
| doom-md-r20d-diag.bin | Combo + diagnóstico de pilha/heaps |

R4 não modifica o cache de texturas compostas nem a geometria. R2 pressupõe a base fullcolormap inicializada e constante, como no código atual. Há RAM extra pequena: ponteiros do memo e três registros de origem de textura. O relatório de símbolos registra a ocupação real.

Testar: diag → control → r2 → r4 → combo. Para rodada curta: diag → control → combo. Mandar telas finais; conferir paredes, céu, sprites e arma. Sem erros detectados é desejável; se houver erro/trava, mandar a última tela e o nome exato.

Referências: BlastEm R20c natural 11,06 FPS / 192,88 s; hardware R20c natural 195,37 s. Comparar primeiro contra control da própria R20d, com clock/divisor idênticos. Não comparar FPS de diag. No hardware usar 7,67 MHz.

Não há promessa de ganho: há custo de memo miss e de preparação por segmento. Os contadores da R20a mostraram apenas 7,2 colunas de parede de uma patch por frame; R4 pode render pouco ou perder. Alterações de LTO fazem parte do resultado do executável completo e estão documentadas pelo relatório.

Testes offline cobrem seleção/fallback do memo e endereços de origem das texturas simples no WAD real; não executam o código compilado nem substituem inspeção visual do jogo. Esperados 2134 frames por execução completa.
