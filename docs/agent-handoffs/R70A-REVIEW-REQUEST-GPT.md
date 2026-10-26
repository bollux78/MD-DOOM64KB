# R70-A — pedido de revisão ao ChatGPT (resultado da run 40362045678)

Repo `bollux78/MD-DOOM64KB`, branch `exp-claudio-r70a-segloop-20261026`, commit `d1cb436` (base R66 `f5a9daa`, intacta).
Workflow `.github/workflows/r70a-build.yml`: agora só `workflow_dispatch` (gatilho push removido). Disparo: `gh workflow run r70a-build.yml --ref exp-claudio-r70a-segloop-20261026`. Autorização do mantenedor: "autorizo compilação em todas as branchs e versões sempre"; ele pediu que o ChatGPT faça a próxima compilação.

## 1. Falha da run anterior (40356754608) — resolvida
Teste diferencial `test_r70a_segloop.py`: divergência A2/A1+A2 era instabilidade do harness. Em modo `--legacy` (hasheia campos de `dcvars` que a rotina não lê) a primeira diferença é sempre `flat.UNREAD.colormap` (ponteiro/ASLR) e o MESMO binário de controle diverge de si mesmo entre duas execuções; em modo estrito é idêntico. Estrito: 20.000 cenários, 8.955.451 eventos, controle = A1 = A2 = A1+A2; 5/5 mutantes detectados. Detalhe: `docs/review-r70/R70A-DIFFTEST-DIAGNOSIS.md`. Correções de workflow: disassembly só com 4 ELFs e stderr do objdump preservado; capturas/comparação imprimem "SKIPPED - build/capture unavailable".

## 2. Run 40362045678 (commit d1cb436): SUCCESS
- Controle reconstruído byte-idêntico à R66 aprovada (run 40231459814). ROMs: 2.883.584 B cada, BSS 57.900 B (limite 57.920).
- SHA-256: controle `2c93cdbb…ca36`, A1 `32cbcbb8…55f7`... (completos na anotação "R70 ROM table"/`dist/r70/ROM-TABLE.md`).
- DEMO3 completa no BlastEm, 2133 tics comuns, pixels reais do framebuffer 76x44:

| variante | FPS eq. | vblanks vs R66 | terços | pixels |
|---|---:|---:|---|---|
| R66 | 7,22 | — | — | — |
| A1 LOCALS | 7,25 | −0,47% | −0,53/−0,20/−0,65 | 0 bytes diferentes |
| A2 INVARIANTS | 7,26 | −0,63% | −0,63/−0,58/−0,67 | 0 bytes diferentes |
| A12 | 7,27 | −0,72% | −0,72/−0,48/−0,93 | 0 bytes diferentes |
Repetição do controle: sequência de vblanks idêntica (determinismo). Sem regressão em nenhum terço. p50/p90/máx iguais (6/15/26; A2 máx 25).

## 3. Leitura e ressalvas
- Equivalência visual preservada; ganho reproduzível mas pequeno (0,5–0,7%, ≈ +0,05 FPS), diferenças entre A1/A2/A12 na faixa de ruído. Candidato: A12 (mais rápido), mas A2 sozinho já rende 0,63%; critério "não forçar combinação" não é violado.
- `R_RenderSegLoop`/`R_StoreWallRange` são inlinadas por LTO em `R_Subsector.lto_priv.0`: +74 B (A1), +518 B (A2), +774 B (A12); abs-long 355→307/358/290.
- Anotação "R70 host test log" contém tabela sintética (−1,76% / "DIFFERS") de `test_r70_tools.py`: dados inventados, NÃO é desempenho real.
- BlastEm mede vblanks por quadro (resolução de 1 vblank); confirmação final no Mega Drive real pelo mantenedor.
- Artifact `doom-md-r70a-ab` (ROMs .bin/.elf, manifest, capturas, relatórios): baixar via Actions (o proxy do Cláudio bloqueia o download).

## 4. Perguntas
1. Aprova A12 (ou A2) como candidata a validação em hardware?
2. Dado o ganho de <1%, seguir para R70-B (`R42_DrawPackedWall`/`R_DrawSegTextureColumn`) ou R70-C (`R_StoreWallRange`)? Nunca simultâneos.
3. Quer repetir a run para outra confirmação de ruído antes de decidir?
