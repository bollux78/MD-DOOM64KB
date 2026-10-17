# Experimentos anteriores: não repetir sem uma hipótese nova

|Tentativa|Resultado|Consequência|
|S2 sight iterativo|resolveu estouro de pilha observado|manter; não reduzir reserva com base em heap livre|
|R3 flat unroll|196,23s vs191,43controle e prejudicou combinação|desligado|
|R4 hoist de parede1patch|193,38 vs191,43;combo191,87|desligado|
|R4b hoist composição|186,65 vs184,90|desligado|
|P3 unroll pixels|185,18 vs184,90|desligado|
|M4 higiene|185,02 vs184,90|sem ganho demonstrado;fora da matriz de desempenho|
|SPRTEMP_DYNAMIC|Z_Malloc falhou ao pedir904B|não transferir temporário638B para zona sem modelar pico de inicialização|
|S5 heap SGDK/DMA menor|imagem congelada;diag alcançouT02134|possível transição para resultados;causa não isolada|
|V2 VBlank/snapshot|três ROMs travaram BlastEm|todas também usavamSPRTEMP_DYNAMIC;causa confusa, não atribuir apenas aV2|

R20g `sprites`,`ram`,`ram-render`:erro alocação904B. `ram-v2`,`ram-v2-v3`,`full`:travas inferidas por eliminação após identificar todos os outros nomes. V2 jamais foi testada isoladamente nessa série; qualquer retomada exige alocação estável e controle sem o temporário dinâmico.

S5 congelou na imagem da demo; chegarT02134 sugere investigar parada/reinicialização de vídeo e tela de resultados, sem afirmar causa já provada.

P3 exigiu corrigir deslocamento PC indexado incompatível com68000: LEA do fim +JMP com índice deword. Não reintroduzir salto que só cabe em68020. Unroll pode perder por footprint, setup, registradores e pouco trabalho médio.

O antigo motor recursivo apresentou erro real de pilha; aumentar stack sem orçamento de memória não é solução estabelecida. R13/R14 e mulfast/mul4 históricos foram descartados por instabilidade; se revisitados, exigir implementação distinta e diagnóstico.

SFX silenciosos fazem parte do benchmark; vitória atual não valida SFX completos nem pico de memória em todos os mapas. A versão jogável anterior existe, mas não se deve presumir que a nova combinação já foi validada em campanha.
