# NEXUS · teste de texturas nas paredes

E1M1 é a cena de referência. O renderizador trabalha com 80 × 60 amostras
nas duas ROMs. A versão 2x ocupa 160 × 120. A 3x ocupa 240 × 180 e usa
quatro linhas de padding para a tabela de tiles do VDP.

## Controles

- A seleciona paredes lisas.
- B alterna entre perspectiva por coluna e interpolação em blocos de quatro colunas.
- C mede 39 quadros por modo. Exibe mediana, P95 e máximo em milissegundos.
- Start alterna câmera livre e poses fixas. Esquerda/direita seleciona poses ou gira a câmera. Cima/baixo move a câmera livre.

As texturas são compostas dos patches do WAD e quantizadas para a
paleta do Mega Drive. A BSP projeta e recorta os segmentos de parede.
O rasterizador escreve o texel diretamente no pixel da parede. O modo
em blocos calcula a perspectiva nas extremidades e interpola dentro de
cada bloco. Pisos e tetos usam cores sólidas. Portais mascarados, sprites
e regras completas de iluminação ficam fora deste protótipo.

## Comparação em E1M1

Genesis Plus GX, as mesmas 13 poses repetidas três vezes em cada modo.
O tempo inclui render, empacotamento, espera pelo VBlank e DMA.

| Viewport | Liso mediana / P95 | Perspectiva mediana / P95 | Blocos mediana / P95 |
| --- | ---: | ---: | ---: |
| 160 × 120 | 99 / 215 ms | 233 / 432 ms | 219 / 399 ms |
| 240 × 180 | 214 / 315 ms | 367 / 549 ms | 349 / 515 ms |

Cada viewport e modo foi comparado à saída do renderer no PC nas 13
poses. Os tempos acima são do emulador. A confirmação no Mega Drive
físico está pendente.

## Compilar

Requer Python 3, Java, SGDK nativo e um WAD clássico local.

```sh
GDK=/caminho/para/sgdk DOOM1_WAD=/caminho/para/doom1.wad bash build.sh E1M1 3x
GDK=/caminho/para/sgdk DOOM1_WAD=/caminho/para/doom1.wad bash build.sh E1M1 2x
```

Os binários são gravados em `out/E1M1/`. O arquivo de textura gerado
localmente é ignorado no Git.
