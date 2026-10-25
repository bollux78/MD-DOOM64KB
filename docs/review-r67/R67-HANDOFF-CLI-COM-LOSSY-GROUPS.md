# R67 · precisão agressivamente reduzida nas texturas — handoff Cláudio / Werk

**25/10/2026 — VEREDITO FINAL DO USUÁRIO: R67-G4 / G8 / G16 REJEITADAS POR DETERIORAÇÃO VISUAL PERCEPTÍVEL. R66 MANTIDA.** A perda visual aumenta com o tamanho do grupo e os ganhos reais de desempenho não justificam a troca. Não promover nem incorporar R67 à R66.

## Benchmark COMPLETO enviado pelo usuário e decisão

DEMO3 / NTSC 60 Hz; 2.134 quadros por ROM, configurações equivalentes; screenshot comparativo de quatro ROMs fornecido pelo usuário. Todos os valores abaixo são **medidos no benchmark completo** e distintos dos prefixos automatizados.

| Métrica | R66 controle | R67-G4 | R67-G8 | R67-G16 |
|---|---:|---:|---:|---:|
| FPS médio | 7,21 | 7,35 | 7,47 | 7,53 |
| Ganho sobre R66 | — | +1,94% | +3,61% | +4,44% |
| Tempo de DEMO3 | 295,88 s | 290,17 s | 285,68 s | 283,42 s |
| FPS mínimo 1s | 2,9 | 2,9 | 3,0 | 3,2 |
| FPS máximo 1s | 13,0 | 14,0 | 14,3 | 14,5 |
| SGDK FREE/BLOCK AT END | 750 / 750 | 750 / 750 | 750 / 750 | 750 / 750 |

**Avaliação visual explícita do usuário:** «perda visual perceptível e crescente com ganhos pequenos. não aceito». Vale mesmo para G4 (+0,14 FPS); G16 (+0,32 FPS) é insuficiente para justificar a imagem mais degradada. Não confundir aceitabilidade de aproximação da R66 (relatada visualmente indistinguível da R64A) com permissão irrestrita para texturas em blocos maiores.

**Nova orientação para Cláudio/Werk:** preservar R66 (grupo de 2 colunas) como melhor compromisso conhecido, alvo de performance de referência **7,21 FPS** no DEMO3 completo. Buscar economia em outros cálculos e estruturas (escala, distância, setup por segmento, reduções numéricas com erro controlado, cache seguro, chamada ao kernel ASM), evitando maior compartilhamento horizontal de textura. Aproximações novas são possíveis, mas devem passar pelo julgamento visual antes de promoção; não adotar ganhos de 1–4% à custa de faixas ou perda evidente de identidade visual. R60 e R64A continuam referências imutáveis.



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

## Resultados reais do primeiro A/B em DEMO3 (PREFIXOS)

Os workflows agora encerraram com sucesso, incluindo build [40233731174](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40233731174) e validação [40234412567](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40234412567). [Arquivo de evidências / snapshots / JSON](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40234412567/artifacts/12614122676).

Três execuções independentes por ROM em cada tic, VBlanks extraídos da ROM sem profiler e clock original, sem dispersão observada:

| Tic | R66 FPS | G4 FPS (ganho) | G8 FPS (ganho) | G16 FPS (ganho) |
|---:|---:|---:|---:|---:|
| 64 | 4,1722 | 4,2000 (+0,67%) | 4,2424 (+1,68%) | 4,2616 (+2,14%) |
| 128 | 4,0446 | 4,0727 (+0,69%) | 4,1145 (+1,73%) | 4,1391 (+2,34%) |
| 256 | 4,5590 | 4,6070 (+1,05%) | 4,6575 (+2,16%) | 4,6918 (+2,91%) |

**Não extrapolar estes percentuais para o DEMO3 completo de 2134 quadros; ainda não foi medido.** Todas as 7 ROMs têm BSS PERF 57900, PLAY 57908 (sem BSS adicional). O controle R66 foi byte-idêntico à ROM que registrou 7,21 FPS no DEMO3 completo. BlastEm smoke: 8 execuções PERF (800 e 10000 frames cada ROM), zero falhas.

### Divergência visual intencional comparada ao controle R66

O total é por **amostra de 4 bits** dentro da janela ativa de 66×34=2244 amostras; cinco instantâneos separados por tic. Zero pixels modificados fora da janela de jogo nas 15 comparações realizadas.

| Tic | G4 % alterada | G8 % alterada | G16 % alterada |
|---:|---:|---:|---:|
| 8 | 6,46% | 9,72% | 12,39% |
| 16 | 6,60% | 8,91% | 11,23% |
| 64 | 6,24% | 9,98% | 17,47% |
| 128 | 9,14% | 15,29% | 17,25% |
| 256 | 7,35% | 12,34% | 18,23% |

Em cada grupo, apenas fases 2..N-1 alteraram suas amostras; fases 0 e 1 permaneceram iguais ao R66, consistente com o algoritmo de compartilhamento. **Tendência de retornos decrescentes:** G16 ganha mais FPS mas muda muito mais pixels do que G8. Não avaliar a qualidade da imagem só por percentuais: é preciso jogar, girar a câmera, andar junto a paredes, abrir portas e olhar grades/texturas.

## Métricas para não confundir

Workflow de build `r67-groups-build.yml` utiliza 800 e 10.000 quadros por **invocação**, sem usar tempo de execução do host como FPS. Workflow de análise `r67-groups-validate.yml` mede os valores reais via contadores de VBlank na WRAM com ROMs sem profiler, 3× prefixo em tics 64/128/256 para R66/G4/G8/G16, e compara cinco snapshots Pixel4 de 3344 bytes, incluindo mudanças por fase horizontal e pixels que saem da janela.

Amostras não provam o desempenho do DEMO3 completo. O usuário deve medir **2.134 quadros completos** em mesma resolução, clock e crop; reportar média, min/max 1 segundo, SGDK FREE/BLOCK, e comparar movimento visual.

## Critérios de seleção

1. Sem falha, corrupção de memória, travamento, tela instável ou alteração visível na geometria/clipping.
2. Movimentação frente/trás e rotação próximas a paredes, alinhamento de texturas, portas e grades, céu, transparências e compositing; a distorção pode ser notável, mas não deve impedir o entendimento dos ambientes nem incomodar em jogo.
3. Preferir a variante mais agressiva cuja aparência ainda seja agradável **e** cujo ganho repetido no DEMO3 completo compense; não eleger exclusivamente pelo FPS.
4. Manter controle R66 7,21 FPS e referência de precisão R64A 6,91 FPS. Se houver regressão, preservar R66 e rejeitar a variante.
5. Qualquer próxima redução numérica de projeção (distância/escala/ângulo) exige experimento separado, já que altera geometria e o risco é maior que ampliar grupos de textura.

**Status FINAL:** compilação, auditorias, 15 frames amostrados, 3× prefixos, benchmarks completos de 2.134 quadros e avaliação visual do usuário concluídos. **R67-G4/G8/G16 rejeitadas por custo visual superior ao ganho; R66 é a referência aprovada.**
