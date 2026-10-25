# R65 — conclusão da primeira rodada e pedido de R65-P2 ao Cláudio/Werk

**Status 25/10/2026:** R60 histórica intocada. R64A permanece melhor candidato de desempenho. R65-P1 **rejeitada**. Somente clock original 68000 (~7,67 MHz) conta para o projeto.

## 1. Evidência confiável

**R60→R64A (DEMO3 completo do usuário, 2.134 quadros):** 6,72→6,91 FPS, 317,37→308,98 s (+2,83% FPS).
**R64A PLAY:** funciona e reproduz ~6,91 FPS no teste manual, com capacidade de H32/H40 e crop. Testes manuais de todas as transições de cor/menu/mapa não foram declarados exaustivos.

**Repetições CI (PREFIXO, 3× cada ROM):** R60→R64A nos tics 64,128,256:
- tic 64: 3,9416→4,0645 FPS = +3,118%;
- tic 128: 3,8043→3,9441 FPS = +3,675%;
- tic 256: 4,2618→4,4207 FPS = +3,727%.
Mesmos VBlanks nas três rodadas de cada ROM, dispersão zero sob emulação determinística. **Não extrapolar para 2.134 quadros.** `-b` <=10.000 quadros por execução. [Repetições / dados](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40224191416/artifacts/12610034618).

**Equivalência gráfica comprovada nas amostras:** R60 × R64A 5/5 framebuffers `r22_fb.pixels` de 3.344 B nos tics 8,16,64,128,256. Não equivale a prova para todos os quadros/modos.

**R64D:** dump completo de WRAM 65.536 B no tic 128 decodificado com os 50 contadores de Cláudio: `SR_CALLS=2615`, `SEG_COLS=28763`, `WALL_CALLS=23473`, `WALL_ASM=18734`, `FLAT_CALLS=25814`, `AL_CALLS=7508`, `AL_REAR=2743`, `AL_V1_REUSE=1768`, `XP_FALSE_REAR=1`. [Dump e leitor](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218307012/artifacts/12608377377). B1/B2 líquidos recalculados pelo leitor v2 do Cláudio não justificam novos riscos.

## 2. Experimento R65-P1 — fracassou, descartado

Branch própria [`exp-r65-p1-early-wall-crop`](https://github.com/bollux78/MD-DOOM64KB/tree/exp-r65-p1-early-wall-crop). Modificação mínima e zero-BSS em `src/r_draw.c`: antes de `R20_WALLCOL`, testou se `dcvars` tinha alguma interseção com `[R57_YMIN,R57_YEND)`; caso totalmente fora, pulou preparação de textura. Decisões de clipping, BSP, textura mascarada, visplanes e atualizações de colunas não foram alteradas.

**Resultados:** compilação MarsDev bem-sucedida, flags PERF iguais exceto `-DDOOM_R65_EARLY_WALL_CROP`, BSS 57.900 B PERF / 57.908 B PLAY, ASM intacto, BlastEm 800 e 10.000 passes, 5/5 framebuffers byte-identical R64A × R65, ROM R64A controle recompilada **idêntica ao pin anterior**.

**Entretanto houve regressão reproduzível em 3× A/B prefixo:**

| Tic | R64A FPS | R65-P1 FPS | Diferença |
|---:|---:|---:|---:|
| 64 | 4,0645 | 4,0428 | −0,535% |
| 128 | 3,9441 | 3,9157 | −0,719% |
| 256 | 4,4207 | 4,3814 | −0,888% |

Testes de equivalência e seis medições: [run 40225100146](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40225100146/artifacts/12611206289).
ROMs/ELFs, logs e flags: [run 40224741397](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40224741397/artifacts/12610328445).

**Decisão fechada:** NÃO mesclar R65-P1, NÃO pedir teste manual dessa variante. O pré-teste extra em todas as chamadas custou mais do que economizou no prefixo.

## 3. Auditoria REAL de código de máquina 68000 (R60 e R64A PERF originais)

Extraído em runner com `m68k-elf-objdump -d --no-show-raw-insn` e `m68k-elf-nm -nS`, **sem recompilar ou instrumentar ROM**. São estáticas do código gerado (contagem de instruções existentes em caminhos alternativos), **não** ciclos dinâmicos, frequências reais ou proof of hotspot.

[Baixar disassembly completo, extratos e STATIC-AUDIT.json](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40225386035/artifacts/12611076849).

| Símbolo | R64A — instruções estáticas | Classes estáticas relevantes |
|---|---:|---|
| `R_PointToAngle16.lto_priv.0` | 361 | 8 × DIVU, 8 chamadas |
| `R_ScaleFromGlobalAngle` | 249 | 22 × MULU, 2 × MULS, 1 × DIVU |
| `R_DrawSegTextureColumn` | 297 | 1 × MULS, 1 chamada |
| `R42_DrawPackedWall.lto_priv.0` | 286 | 4 × MULU, 2 × MULS |
| `R_DrawColumnFlat.isra.0` | 149 | 4 × MULU |
| `R60_WallColumn` | 57 | 0 DIV/MUL |

O `R_RenderSegLoop`, `R_StoreWallRange`, `R_AddLine`, `R_CheckBBox`, `R_RenderBSPNode` **não aparecem como símbolos independentes** nesse binário otimizado/LTO; podem ter sido internalizados e/ou incorporados a outras funções. A auditoria entrega o disassembly total para localizá-los. Não interpretar ausência do símbolo como ausência de execução. Não somar toda instrução listada como se cada chamada percorresse todos os ramos.

## 4. Pedido de próxima proposta R65-P2 (AINDA NÃO implementada)

Cláudio/Werk: antes de criar patches, identificar **uma única operação estrutural quente** que possa ser eliminada/antecipada **por segmento ou por quadro**, sem acrescentar testes em cada coluna como fizemos na P1.

Ordem sugerida de inspeção — NÃO é ranking de ciclos medidos:
1. `src/r_draw.c` `R_StoreWallRange`: 2 chamadas a `R_ScaleFromGlobalAngle` para cada fragmento com >1 coluna; aritmética fixed-point e divisão de escala. Conferir caminhos executados em ASM real + distribuição de `SR_CALLS` do R64D. Preservar overflow, arredondamento e exatidão.
2. `R_RenderSegLoop`: custo de `R15_TAN_PRODUCT`, `FixedReciprocal`, busca de coluna de textura, `dcvars` e chamadas `R_DrawSegTextureColumn`. Variantes históricas `DOOM_R21_LAZY_TEXCOL` e `DOOM_R21_SEGLOOP_LOCALS` já deram pouco resultado; não repeti-las sem hipótese distinta.
3. BSP: `R_PointToAngle16` / `R_CheckBBox`, com cuidado para preservar FOV/oclusão. B1 pré-teste vetorial tem `XP_FALSE_REAR=1`; nenhuma rejeição aproximada incondicional.

**Condições para a P2:** branch separada do HEAD da R64A limpa; R60 protegida, macro opcional, zero BSS, ASM e paletas idênticas, fonte/flags auditáveis, Pixel4 5/5, 3+3 prefix, DEMO3 completo 2.134 quadros no clock original e manual PLAY/hardware para candidatos promissores. Mesmo FPS na ROM não é suficiente sem equivalência de renderização.

**Próxima decisão:** apresentar o `objdump` do hotspot mais promissor, instrução concreta eliminável e impacto estimado líquido, **antes** de criar mais uma ROM de produção.
