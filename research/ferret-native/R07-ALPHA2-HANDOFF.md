# R07: comparação com a Alpha2 na mesma pose (para o Werk rodar no x360)

## Como rodar
Abrir um PR de `research-ferret-r07-perf-claudio-20261126` para `research-ferret-r06-perf-20261126`
(ou `workflow_dispatch` do `ferret-r07-alpha2.yml`). Nada privado sai do x360: imagens ficam em
`~/.local/share/ferret-research/r07/<run>`, só JSON/TXT numéricos vão para o artefato.

## O que o workflow faz
1. Builds: R06 BENCH (base `bbd5151`), R07 BENCH, R07 céu legado, R07 com as poses da Alpha2.
2. Tempo exato de render por pose (MAME, `mame_render_time.lua`), R06 x R07 -> `render-times.txt`.
3. Céu legado: mailbox das 12 poses -> `r07-legacy-mailbox.txt` (tem que ser idêntica à da R04).
4. Alpha2 autenticada no Genesis Plus GX instrumentado, nas poses de debug (spawn e zigzag 0/64/128/192),
   e R07 nas poses equivalentes; métricas em `alpha2-compare.json`.

## Contrato de coordenadas (medido na RAM da Alpha2)
- x Alpha2 = x WAD; y Alpha2 = y WAD + 3456; z Alpha2 = 1 - altura do olho.
- ângulo Alpha2 (0..255) = -ângulo Doom; o ângulo da FERRET-MD é o ângulo Doom em graus.
- Andar para a frente no spawn (Doom 90) aumenta y na Alpha2; virar à direita aumenta o ângulo dela.
Atenção: as 12 poses da R04 (ex.: "zigzag-walkway" 1504,-2938) **não** são as poses de debug da
Alpha2 (2980,170 = WAD 2980,-3286). Comparações anteriores entre essas poses não eram da mesma câmera.

## Critérios (medidos no MAME local, 26/11)
| Métrica | mesma pose | pose errada (base) |
|---|---|---|
| luma_corr | 0,36 a 0,62 | -0,29 a 0,08 |
| edge_corr | 0,08 a 0,61 | -0,03 a 0,08 |
| color_dist | 20 (spawn), 47 a 52 (zigzag) | 49 a 70 |
PASS geométrico por pose: luma_corr >= 0,30 e maior que a base. color_dist alto na zigzag é paleta, não geometria.
