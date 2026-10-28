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
