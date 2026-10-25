# R67 · precisão agressivamente reduzida nas texturas — handoff Cláudio / Werk

**25/10/2026. Experimento independente, NÃO promover antes de teste visual real.**

## Decisão de produto

O objetivo do DOOM-MD é preservar a experiência, o código e o comportamento do DOOM original sempre que couberem no orçamento real do Mega Drive, priorizando reconhecimento visual e jogabilidade sobre precisão matemática do rasterizador. Distorção controlada de texturas como o 'wobble' do PlayStation é aceitável. NÃO comprometer geometria da sala, clipping, colisões, movimento, efeitos de portas ou gameplay.

**Benchmark R66 comprovado pelo usuário**, DEMO3 completo NTSC 60Hz, 2134 quadros em H40 crop H/V16 no clock original:

| Métrica | R64A | R66 |
|---|---:|---:|
| FPS médio | 6,91 | **7,21** (+4,34%) |
| Tempo | 308,98 s | **295,88 s** (−13,10 s) |
| Mínimo FPS 1s | 2,7 | 2,9 |
| Máximo FPS 1s | 12,0 | 13,0 |
| SGDK FREE / BLOCK | 750 / 750 | 750 / 750 |

O usuário relatou **imagens visualmente iguais**. Os resultados automatizados de 3× prefixo da R66 foram +2,65% / +2,55% / +3,13% contra R64A nos tics 64/128/256. A equivalência visual do usuário é observação qualitativa válida e o critério de qualidade atual; não é uma prova de igualdade de pixels.

## Novos experimentos R67 implementados

Branch [exp-r67-aggressive-texture-groups](https://github.com/bollux78/MD-DOOM64KB/tree/exp-r67-aggressive-texture-groups), derivada da R66 validada, mantendo R60, R64A e R66 originais sem alterações.

Macro build `DOOM_R67_TEXGROUP` = `4`, `8` ou `16`, ativa **apenas** se `DOOM_R66_COLPAIR=1`. A R66 calcula textura/recíproca em colunas pares e compartilha com a ímpar seguinte; na R67 recalculamos somente a primeira coluna de cada grupo horizontal absoluto de 4/8/16 (ou a primeira coluna do segmento BSP, se iniciar no meio do grupo). Reutilizamos:

- `texturecolumn` / tangente / produto com distância;
- `dcvars.fracstep` / recíproca;
- `dcvars.source` em `midtexture` de parede de um lado só, zerado no início de um grupo para impedir reutilização entre grupos.

Tudo isso é **por segmento e com estado local**. Os limites de desenho `yl/yh`, clipping `floorclip/ceilingclip`, `rw_scale`, geometria/topfrac/bottomfrac, abertura de portas, BSP e rasterização de céu/chão/teto **continuam por coluna**. Testar se sprites/mascaradas visíveis herdaram resultados de textura porque `maskedtexturecol[rw_x]` também compartilha a coordenada dentro dos grupos. Não afirmar que o desenho é pixel-identical — divergências são pretendidas.

Como cada amostra Pixel4 representa 4 pixels físicos horizontais, grupos de 4/8/16 podem produzir coordenadas constantes em até aproximadamente 16/32/64 pixels físicos (dependendo de limites dos segmentos, janela ativa e o tipo de parede).

**7 ROMs no script** `scripts/lab/build_r67.py`:
- `doom-md-r60-r66-perf.bin` (controle original; SHA deve reproduzir artifact run 40231459814);
- `doom-md-r60-r67-g4-perf.bin` e `doom-md-r60-r67-g4-play.bin`;
- `doom-md-r60-r67-g8-perf.bin` e `doom-md-r60-r67-g8-play.bin`;
- `doom-md-r60-r67-g16-perf.bin` e `doom-md-r60-r67-g16-play.bin`.

Todas com ROM 2.883.584 B, tabelas de cores idênticas, kernel ASM R60, alvo stock 7,67 MHz, e BSS alvo <= 57.920 B, sem aumento na PERF em relação à R66.

## Métricas para não confundir

Workflow de build `r67-groups-build.yml` utiliza 800 e 10.000 quadros por **invocação**, sem usar tempo de execução do host como FPS. Workflow de análise `r67-groups-validate.yml` mede os valores reais via contadores de VBlank na WRAM com ROMs sem profiler, 3× prefixo em tics 64/128/256 para R66/G4/G8/G16, e compara cinco snapshots Pixel4 de 3344 bytes, incluindo mudanças por fase horizontal e pixels que saem da janela.

Amostras não provam o desempenho do DEMO3 completo. O usuário deve medir **2.134 quadros completos** em mesma resolução, clock e crop; reportar média, min/max 1 segundo, SGDK FREE/BLOCK, e comparar movimento visual.

## Critérios de seleção

1. Sem falha, corrupção de memória, travamento, tela instável ou alteração visível na geometria/clipping.
2. Movimentação frente/trás e rotação próximas a paredes, alinhamento de texturas, portas e grades, céu, transparências e compositing; a distorção pode ser notável, mas não deve impedir o entendimento dos ambientes nem incomodar em jogo.
3. Preferir a variante mais agressiva cuja aparência ainda seja agradável **e** cujo ganho repetido no DEMO3 completo compense; não eleger exclusivamente pelo FPS.
4. Manter controle R66 7,21 FPS e referência de precisão R64A 6,91 FPS. Se houver regressão, preservar R66 e rejeitar a variante.
5. Qualquer próxima redução numérica de projeção (distância/escala/ângulo) exige experimento separado, já que altera geometria e o risco é maior que ampliar grupos de textura.

**Status da publicação:** código e oráculos preparados; resultados da execução de CI e do teste visual serão acrescentados quando disponíveis. Este documento não presume ganho de G4/G8/G16.
