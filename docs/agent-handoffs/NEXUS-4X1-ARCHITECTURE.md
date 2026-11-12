# NEXUS 4×1 · testes de arquitetura

Testes em E1M1 no Genesis Plus GX. Render 40 × 120, viewport 160 × 120,
mesmas 13 poses, modo texturizado por perspectiva e UV incremental.

## Escrever diretamente no formato de tiles

O protótipo escreve cada faixa de quatro pixels diretamente em um
buffer na ordem dos tiles da VRAM. A imagem coincide com a referência
em todos os três modos e 13 poses. O protótipo envia os 300 tiles
completos a cada quadro e usa um mapa de tiles fixo para cada banco.

| Medida | Buffer atual e compactação | Escrita direta |
| --- | ---: | ---: |
| Quadro texturizado, mediana | 149 ms | 182 ms |
| Quadro texturizado, P95 | 299 ms | 349 ms |
| Render na pose inicial, leitura individual | 269 ms | 305 ms |
| Preparação para DMA na pose inicial | 19 ms | 1 ms |

A escrita direta eliminou a compactação, mas aumentou o custo do loop
de render e dos uploads completos. Uma implementação de tiles nativos
com atualização parcial pode ter outro resultado. Esta variante ficou
em diagnóstico.

## Filtro de segmentos por pose

No PC, o renderer gravou, em cada pose, quais segmentos chegaram a uma
janela horizontal ainda aberta. Na ROM diagnóstica, a BSP original
pulou os segmentos ausentes dessa lista. A ordem de desenho foi
preservada. A imagem foi idêntica nas 13 poses no teste do PC.
Esse filtro conhece a pose com antecedência e não generaliza para
câmera livre. O tempo exclui empacotamento e DMA.

| Medida | Sem filtro | Com filtro por pose |
| --- | ---: | ---: |
| Mediana de render entre poses | 110,5 ms | 109,3 ms |
| Render na pose inicial | 269,8 ms | 254,6 ms |

O teste mede a economia de rejeitar esses segmentos cedo mantendo a
travessia BSP atual. Uma arquitetura por portais também mudaria a
travessia. A vista inicial processou 29 segmentos que alcançaram
colunas abertas. Nas outras poses, foram seis a oito.

## Próxima hipótese

Testar um rasterizador de faixas de parede que recebe os intervalos
visíveis e amostra texturas com uma representação pré-calculada para
o 68000. Quantizar a escala vertical, pré-calcular os passos da textura
e medir RAM e ROM, estabilidade visual em movimento e custo do quadro.
Manter o renderer 4×1 atual como referência. O alvo de 125 ms no P95
segue como marco inicial para paredes texturizadas.
