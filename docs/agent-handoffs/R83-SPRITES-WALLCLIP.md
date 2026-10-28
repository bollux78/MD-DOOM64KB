# R83 — dois candidatos independentes sobre R82

## Base

Base aprovada pelo usuário: R82 = R81 + P1/F1. Branch de origem `exp-claudio-r82-d8088-20261028`, commit `864c0a0f0e8ccf762e496af52238987bebf4dfdd`. Handoff: `docs/agent-handoffs/R82-HANDOFF-CLAUDIO.md`.

Branch deste teste: `exp-chatgpt-r83-sprites-wallclip-20261028`.

Esta rodada contém três conjuntos, todos com PERF e PLAY:

| Conjunto | Nome da variante | Alteração além da R82 |
|---|---|---|
| Controle | `r82-p1f1` | Nenhuma |
| Sprites | `r83-sprite-p1f1` | Endereços por tabelas ROM e pares por DBRA |
| Paredes | `r83-wall-clip` | Interseção dos limites e fração inicial simplificadas |

Não há candidato combinado. Cada mudança é avaliada separadamente contra a mesma R82. Fonte, menus, save/load, cheats, paletas, resolução e regras de jogo são herdados da R82. Shadow adaptativo permanece desligado.

## Sprites: P1 e contagem por DBRA

A tabela de endereços `R80_PIXEL_BYTE` já existente é movida, sem duplicação, para antes da função de sprites. O único novo consumidor é o cálculo do destino em `R_DrawColumnSprite`.

Na composição de LUT válida e com pelo menos dois samples, o desenho usa `R60_WallDraw`, o kernel Pair-V já ligado à ROM. Ele mantém o avanço de fração de 16 bits com 9 bits fracionários e o índice de textura de 7 bits; o laço de pares termina por DBRA. O nome histórico do kernel contém “Wall”, mas a operação sobre cada post opaco do sprite é a mesma: o primeiro/último nibble cortado preserva o vizinho e os pares completos escrevem os dois texels.

O caminho C original permanece para colormaps não compostos e demais casos. Não se aplica o preenchimento de cor constante dos flats a texels de sprites. O teste host modela o ADDX/índice/fração do assembly; a validação do assembly real é o framebuffer capturado no BlastEm.

Não há tabela nova em WRAM, nem cópia adicional do framebuffer.

## Paredes: limites e fração inicial

No caminho R64A, os limites do contexto são intersectados com 76×44 antes das comparações. O limite inativo de 32767 continua correto. A checagem de x usa o intervalo sem sinal, após considerar o limite físico da tela.

A fração inicial usa a identidade modular:

`(y0-CENTERY)*step + (first-y0)*step ≡ (first-CENTERY)*step (mod 65536)`.

Assim é necessário apenas um produto para posicionar a textura na primeira linha visível, em vez do produto inicial mais a correção das linhas cortadas. O kernel de pixels e as LUTs não mudam.

## Validação

`test_r83.py` compila as funções reais de referência/candidato e compara os 3344 bytes, além das sentinelas. Inclui 284970 pares de colunas sprite/parede, cabeças/caudas ímpares, steps e fases variados, colormap composto/não composto, clipping e domínio completo de x assinado para os intervalos testados. O teste também exige que o candidato de sprites não altere o corpo da parede e vice-versa, e recusa aplicar o patch duas vezes.

O workflow `r83-compare.yml`, disparado por `.github/triggers/r83-compare.trigger`, compila cada conjunto em cópia descartável e:

1. Exige controle R82 byte a byte igual às ROMs aprovadas.
2. Exige ROM ≤4 MiB e BSS ≤57920, sem aumentar o BSS em relação à R82 correspondente.
3. Captura cada PERF uma vez, até 8000 frames por processo.
4. Exige pelo menos 100 tics comuns e nenhum framebuffer diferente.
5. Registra vblanks por frame, delta e terços **do mesmo job**.
6. Coleta disassembly e diagnóstico de pilha para os três conjuntos.

A captura é parcial e não substitui o DEMO3 completo do usuário. Não comparar totais absolutos entre jobs. Nenhum candidato está promovido a nova base apenas por esse teste.

## Reprodução

Em cópias independentes do checkout:

```sh
python3 scripts/lab/apply_r81.py
R80_EXPERIMENTS="P1+F1" python3 scripts/lab/apply_r80_performance.py
```

Para o controle:

```sh
R82_NAME=p1f1 python3 scripts/lab/apply_r82_d8088.py
```

Para exatamente um candidato:

```sh
R83_CANDIDATE=sprites python3 scripts/lab/apply_r83.py
# OU, em outra cópia:
R83_CANDIDATE=wallclip python3 scripts/lab/apply_r83.py
```

Depois: `python3 scripts/lab/build_r71a12mul_hud.py`, com os assets e o ambiente do workflow. Nome do arquivo, header e benchmark vêm da variante do builder.

## Referência de integridade do controle

- PERF: `cabdce1e8ad14ccdcd7f44db9a6377abd7b283a9dae94b093e8c1bb9519170ed`.
- PLAY: `2c734fbbc2e97eb1a3dd3ea22f9f2fd08b767c64c9b1b0f163d5a8c1d9677e82`.

Resultados da rodada devem ser acrescentados após a execução efetiva, com o número do job e a faixa de tics comum.

## Resultado efetivo desta rodada

Build e comparação: [run 40691084814](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40691084814), código compilado `d7e4e5bf6506633755ea95e49726b778aff15253`. Validação do mesmo artefato e diagnóstico de pilha limitado: [run 40692869070](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40692869070), aprovado.

A primeira execução concluiu build, integridade, reprodução exata do controle e comparação de pixels. Somente o diagnóstico adicional de pilha, que tentava chegar ao tic 640, atingiu o teto de frames. A segunda execução reutilizou os mesmos BIN/ELF, sem recompilação, e concluiu o diagnóstico até o tic 128, mantendo o teto de 8000 frames por processo. O workflow de build foi corrigido para essa parada alcançável nas próximas rodadas.

Faixa comum: **341 tics, 2 a 342**. Todas as comparações abaixo pertencem ao mesmo job de captura.

| Variante | Vblanks na faixa comum | Delta vs R82 | Terços do trecho | Frames diferentes |
|---|---:|---:|---|---:|
| R82 controle | 3866 | 0 | 0 / 0 / 0 | — |
| R83 sprites | 3837 | **−0,75%** | −0,43 / −0,93 / −1,04% | **0/341** |
| R83 paredes | 3875 | **+0,23%** | +0,19 / +0,16 / +0,42% | **0/341** |

O candidato de sprites foi mais rápido neste trecho. O de paredes não demonstrou ganho: o pequeno delta positivo é próximo do ruído de medição. Ambos são entregues para a rodada de benchmark do usuário; não se adota automaticamente o candidato de paredes.

As seis ROMs possuem 2883584 bytes. BSS idêntico por modo: PERF 57844, PLAY 57852. Nenhum novo buffer permanente. Pilha medida até o tic128: controle pico1158/folga1404 B; sprites pico1182/folga1380 B; paredes pico1186/folga1376 B. Isso é um diagnóstico parcial, não um limite demonstrado para todos os mapas.

O disassembly confirma a chamada ao kernel DBRA na função de sprites candidata e as mudanças na função de paredes. Multiplicações continuam presentes nos caminhos C de fallback; contar todas as instruções estáticas de uma função não equivale ao custo do caminho executado. Não repetir o benchmark completo automaticamente: a avaliação completa permanece com o usuário.
