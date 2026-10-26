# Pedido de revisão ao ChatGPT — R68 (profiling) e R69 (matriz de janela)

Autor: Cláudio. Repositório: github.com/bollux78/MD-DOOM64KB. Revisão independente, somente leitura.
Não faça merge, promoção, force-push nem altere as branches do Cláudio. Não dispare workflows sem autorização do mantenedor.

## Branches e commits
- R68 (profiling): `exp-claudio-r68-profiling-20261025`, head `04fef1a`.
- R69 (matriz de janela): `exp-claudio-r69-window-matrix-20261026`, head `9720d08`.
- Base imutável: R66 `f5a9daa` (7,21 FPS, crop 16/16, H40). R64A (6,91) e R60 (6,72) são referências imutáveis.

## O que foi feito
1. R68 instrumenta o ROM (contadores, amostrador de PC no HInt, 8 marcas de fase vblank+contador V) sem alterar o R66 quando as flags estão indefinidas.
2. Runs 1-9 do workflow `r68-prof-build.yml` (runner `x360-linux`). Run 8: fases. Run 9: SPLIT (noinline) + grupos de função, 18.000 frames emulados (autorizado pelo mantenedor).
3. R69: workflow `r69-build.yml` com 7 ROMs (crops 32/24/16/8/0 em H40, H32 16/16) para medir tamanho de janela vs vblanks/frame.

## Resultados a verificar
- Fases (run 9, 912 frames, tics 0-912, ~43% da DEMO3): lógica 11,1%, setup 2,1%, BSP+paredes+planos 77,1%, masked+sprites 9,0%, HUD 0,1%, flip/vídeo 0,6%.
- Amostras de PC por grupo: C ao redor da coluna de parede 30,5%; setup/geometria por segmento 15,0%; chão/teto 10,2%; kernel ASM da parede 9,3%; sprites 7,9%; BSP 7,6%; lógica 6,9%.
- Variação por trecho: terço 1 = 13,5 vb/frame, terço 2 = 6,2, terço 3 = 9,7.
- Janela: cada passo de crop dá ~+7-8% de FPS; área escala de forma sublinear.
- Arquivos: `docs/review-r68/R68-RESULTS-run8-phases.md`, `R68-RESULTS-run9-groups.md`, `R68-RESULTS-run6-split.md`, `docs/review-r69/R69-RESULTS.md`.

## Checklist de revisão
1. **Inércia**: `scripts/lab/check_r68_inert.py <base R66 extraído> <branch>` deve dar IDENTICAL nos 7 arquivos. Confirme que `R68_HIT`/`R68_MARK` e os `#if` não mudam o código com as flags indefinidas.
2. **Layout**: `r68_block_t` = 356 B (`src/r68_prof.h`); offsets do handler `src/r68_prof_hint.s` (RING=128, head 256, samples 260, bad 264) batem com `scripts/lab/test_r68.py`. Rode `python3 scripts/lab/test_r68.py`.
3. **Decodificação das marcas** (`scripts/lab/r68_capture.py`): `mark_lines` converte vblank<<8|contador V em linhas NTSC (262 linhas, vint na linha 224). Há ambiguidade conhecida de 6 linhas (0xE5-0xEA durante o vblank). Avalie se o viés é aceitável.
4. **Agrupamento** (`GROUPS` no mesmo arquivo): confira se os regex classificam as funções certas e se "other" (6,8%) esconde algo relevante.
5. **Amostragem**: o HInt não vê o VBlank (~15% do frame). Confirme que as conclusões são lidas como participação nas linhas ativas e não como FPS.
6. **Segurança do workflow**: `.github/workflows/r68-prof-build.yml` (push só nesta branch/arquivo, grupo de concorrência próprio, sem `cancel-in-progress`, permissões mínimas, `persist-credentials: false`, sem segredos impressos). O limite de 10.000 frames foi ultrapassado na run 9 por autorização explícita do mantenedor.
7. **Controle**: o ROM R66 reconstruído deve ser idêntico byte a byte ao artefato original (run-id 40231459814).
8. **Limites do estudo** (o relatório deve dizer): captura cobre só ~43% da DEMO3; overhead do amostrador de alguns %; a regressão (R²≈0,75) tem coeficientes instáveis por colinearidade; `-b 10000` vs ~4.930 vblanks contados não foi explicado.

## O que eu NÃO afirmo
- Nenhum ganho de FPS foi medido. R68 é diagnóstico, não benchmark.
- Nenhuma otimização foi implementada. O R66 segue baseline.

## Formato esperado da resposta
Lista de achados por severidade (bloqueante / importante / menor), com arquivo:linha e proposta de correção. Diga explicitamente se concorda com a leitura "o gargalo é o C por coluna de parede e o setup por segmento, não o kernel ASM" e quais dados adicionais pediria. Não corrija nada nas branches do Cláudio; registre em branch sua (`exp-chatgpt-<tema>-<data>`).

## Próximo passo proposto (aguarda decisão do mantenedor)
Branch nova para otimizar `R_RenderSegLoop`, `R42_DrawPackedWall` e `R_StoreWallRange` sem perda visual, com prova de equivalência por pixel nos testes host, antes de qualquer ROM.
