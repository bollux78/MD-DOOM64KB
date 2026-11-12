# NEXUS N02 no console

Daniel confirmou que a N02 funciona no Mega Drive e que a imagem está correta nas cenas que inspecionou. Relatou baixa fluidez. A revisão testada pertence à N02, cujo código está no commit `8081097a39d6d6303297bf8eac6980e2820833bc`.

## Perfil de E1M1

Uma ROM de diagnóstico derivada da N02 mediu as mesmas 13 poses no Genesis Plus GX, com três repetições por pose. Cada amostra começou após a espera pelo VBlank. Para medir geometria e oclusão, a função de desenho de spans retornou antes de escrever pixels. As janelas de oclusão e a travessia BSP continuaram a ser calculadas. Os incrementos de rasterização são diferenças pareadas por pose. A medição exclui a apresentação no VDP.

| Componente | Mediana aproximada entre poses |
| --- | ---: |
| Geometria e oclusão sem escrita de pixels | 100 ms |
| Incremento de rasterização linear | 106 ms |
| Empacotamento da imagem linear em tiles | 42 ms |
| Incremento de rasterização direta em tiles | 142 ms |

Na pose inicial, geometria e oclusão consumiram aproximadamente 319 ms. O perfil agrupa travessia BSP, clipping, projeção e cálculo das janelas. Os tempos são do emulador e incluem o custo da instrumentação.

A próxima rodada deve medir e reduzir a geometria na pose inicial e reduzir a escrita de pixels nas demais poses, usando a N02 como referência de imagem.
