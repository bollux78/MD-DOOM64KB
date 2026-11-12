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

## Comparação isolada de otimizações

A matriz A/B usa E1M1 a 80 × 60 internos e viewport 2x. Rode
`bash build.sh E1M1 2x <variante>` com `base`, `uv`, `lut`, `asm` ou
`all`. A sigla aparece no cabeçalho da tela e no nome da ROM.

- UV avança a escala de perspectiva e o peso horizontal em ponto fixo por coluna.
- LUT usa uma tabela de mantissa interpolada para o recíproco vertical.
- ASM usa DBRA e um acumulador de 16 bits no loop de texels quando o período cabe.
- ALL habilita as três mudanças.

Genesis Plus GX, perspectiva por coluna, mesmas 13 poses e três repetições.
A medição do render isolado exclui empacotamento, espera e DMA.

| Variante | Mediana do render isolado | Quadro mediana / P95 |
| --- | ---: | ---: |
| BASE | 204,6 ms | 233 / 432 ms |
| UV | 176,8 ms | 216 / 416 ms |
| LUT | 205,5 ms | 233 / 432 ms |
| ASM | 202,9 ms | 232 / 432 ms |
| ALL | 175,6 ms | 200 / 416 ms |

O modo em blocos ficou em 199 / 399 ms de quadro em todas as variantes.
As cinco ROMs coincidiram com a saída correspondente do renderer no PC
nas 13 poses e nos três modos. UV e ASM foram idênticos à BASE. LUT e
ALL mudaram nove pixels lógicos no total no modo perspectiva e sete no
modo em blocos. As paredes lisas foram idênticas em todas as variantes.
O teste em console da matriz está pendente.

## Contornos e wireframe

Duas ROMs de E1M1 usam 80 × 60 internos e viewport de 160 × 120.

- `bash build.sh E1M1 2x uv lines` gera a comparação com contornos.
  A alterna liso/contorno, B alterna as texturas e C executa o benchmark.
  Fora da câmera livre, cima alterna as poses normais, a parede no mapa e
  o mesmo segmento isolado. C nessas duas últimas poses mede as duas cenas
  automaticamente em modo liso.
- `bash build.sh E1M1 2x base wire` gera o wireframe puro, em branco sobre
  preto. As linhas vêm de linedefs de paredes e desníveis. A importação
  deduplica as arestas. O renderer recorta e rasteriza linhas, inclusive
  arestas atrás das paredes. C mede o wireframe, esquerda/direita navegam
  nas poses e Start alterna a câmera livre.

No Genesis Plus GX, 39 amostras por modo nas 13 poses de E1M1:

| Modo | Mediana / P95 do quadro |
| --- | ---: |
| Parede lisa | 99 / 216 ms |
| Contorno visível com oclusão | 82 / 183 ms |
| Wireframe com arestas ocultas visíveis | 116 / 300 ms |

Na pose de frente para a parede lisa, a imagem da BSP inteira foi
idêntica à de uma folha contendo só o segmento correspondente. A
mediana do render foi 33 ms com a BSP do mapa e 31 ms com a folha
isolada. O quadro completo mediu 50 ms de mediana e P95 nos dois casos
(39 amostras por cenário). O teste no Mega Drive físico está pendente.
