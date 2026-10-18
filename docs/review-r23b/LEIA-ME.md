# R23b: E1M2 em 4x4 e correção dos ângulos de parede

- doom-md-r23b-direct-p4.bin: começa diretamente em E1M2, renderizador 4x4 real (76x44 amostras), solid tiles e pair LUT.
- doom-md-r23b-play-p4.bin: jogável 4x4, E1M1 -> E1M2 -> E1M1.
- doom-md-r23b-direct-e1m2.bin: mesma E1M2 corrigida em 8x8, para comparar geometria rapidamente.
- doom-md-r23b-control.bin: controle timedemo 8x8 da base, WAD antigo.
- doom-md-r23b-play-control.bin: controle jogável 8x8 da base, WAD antigo e E1M1 -> E1M8.

Todos usam SRAM e a música E1M1 existente. Ainda não há música específica E1M2.
4x4 usa o renderizador anterior já testado, sem novas otimizações de desempenho.

A R23 gravava em SEGS o ângulo tangente original do Doom. Esta engine usa o ângulo normal,
perpendicular à parede, diretamente nos cálculos de distância e escala. Correção: somar
90 graus (16384 em angle16), com wrap de 16 bits. A discrepância foi confirmada contra
as geometrias dos mapas antigos funcionais e o consumidor rw_normalangle no renderer.
O erro podia produzir distâncias/escalas incorretas e paredes projetadas como colunas.
Teste independente verifica todos os 1463 segmentos de E1M2 contra sua geometria e os
quatro sentidos cardeais. Isso não substitui sua verificação visual no emulador/hardware.

Mantidas as alocações de SRAM/ROM e compactações da R23 que passaram pelos testes
MC68000 de carga nos níveis médio/difícil e dez objetos temporários simultâneos.
Não há conversão dos demais mapas do episódio nesta leva.
