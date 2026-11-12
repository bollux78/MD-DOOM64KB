# NEXUS · perfil das paredes em E1M1

Daniel confirmou que o teste de texturas funciona no Mega Drive. O perfil abaixo usa o Genesis Plus GX e o código do experimento de texturas em `fca57373a31f7e2474f1524307cb4664b0b6dffb`. São três repetições por pose, nas 13 poses do benchmark. Os tempos são estimativas instrumentadas no emulador.

## Renderização interna de 80 × 60

| Medição | Mediana entre poses | Pose inicial |
| --- | ---: | ---: |
| BSP, projeção e oclusão com escrita de pixels desativada | 54 ms | 161 ms |
| Render liso completo | 72 ms | 183 ms |
| Render texturizado com escrita de pixels desativada | 140 ms | 298 ms |
| Render texturizado completo, perspectiva por coluna | 207 ms | 408 ms |
| Empacotamento texturizado em tiles, 2x | 18 ms | 17 ms |
| Empacotamento texturizado em tiles, 3x | 128 ms | 126 ms |

A ROM diagnóstica preserva a travessia e os cálculos de textura e desativa a escrita dentro das rotinas de spans. Os deltas pareados, calculados por pose antes de tirar a mediana, dão aproximadamente +86 ms de preparação das texturas e +49 ms de rasterização adicional, em relação às paredes lisas. A preparação inclui cálculo de U e escala vertical, seleção de material e chamadas de spans. As medições de empacotamento excluem espera e DMA.

## Direção

A geometria da pose inicial é lenta mesmo com paredes lisas e nenhuma escrita de pixels. Em textura, a NEXUS ainda calcula duas divisões de 32 bits, produtos largos e normalização em `sample_wall` para cada coluna amostrada. `material_span` calcula o início e o passo vertical antes de entrar no loop em C. O viewport 3x tem ainda o custo independente de ampliar e reempacotar a imagem em tiles.

O código do DOOM64KB-MD já dispõe de recíprocos tabelados, preparação seletiva de colunas e rasterizadores 68000 especializados. Vale testar na NEXUS um caminho com U/Z e 1/Z incrementais, recíproco de ponto fixo e loop de coluna em 68000. Medir esse caminho no viewport 2x primeiro. A comparação quantitativa entre motores ainda requer uma cena e uma carga de renderização equivalentes.
