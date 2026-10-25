# MD-DOOM64KB — R65-P1, handoff ao Cláudio / Werk

> **RESULTADO FINAL (25/10/2026): R65-P1 REJEITADA POR REGRESSÃO.** Compilou e passou BSS / ASM / 5 framebuffers byte a byte, mas perdeu -0,53%, -0,72%, -0,89% nos prefixos tic 64/128/256, em três repetições por ROM. Nenhuma divergência de pixels. **Não mesclar na R64A.** A hipótese de pular busca de textura fora da janela não compensou o overhead das checagens neste DEMO3. Logs e arquivos: [run 40225100146](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40225100146/artifacts/12611206289). Manter R64A como candidata e buscar novo hotspot, sem adicionar checks por coluna sem contagem de descartes.


**Data:** 25/10/2026. **Clock de referência único:** Mega Drive original, ~7,67 MHz. Overclock pessoal não entra nos resultados oficiais.

**Branches intocadas:** `exp-r60-wall-pair-asm` (R60 histórica); `exp-r60-r64a-prologue-memory-safe` (R64A).
**Branch de diagnóstico R65:** `exp-r65-structural-profiling`.
**Branch isolada candidata:** `exp-r65-p1-early-wall-crop`.

## 1. O que foi validado

- DEMO3 completo do usuário, 2.134 frames, janela 16/16: R60 6,72 FPS / 317,37 s; R64A 6,91 FPS / 308,98 s, +2,83% FPS no mesmo ambiente.
- A versão PLAY R64A também funcionou corretamente; usuário mediu 6,91 FPS / 309,03 s e explorou H32/H40 e crop. A referência de desempenho é **clock original**.
- Byte-identidade `r22_fb.pixels` R60 × R64A em tics 8,16,64,128,256: 5/5 quadros × 3.344 B = zero diferenças (run [40218061144](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218061144)).
- BSS: R64A PERF 57.900 B; PLAY 57.908 B; limite conservador 57.920 B (margens **20 B e 12 B**).
- R64D 50 contadores, dump WRAM real extraído no tic 128. 23.473 chamadas a paredes, 18.734 em ASM; 28.763 iterações de coluna, 25.814 chamadas a flat; `XP_FALSE_REAR=1`. Run [40218307012](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218307012).
- O leitor R64D v2 do Cláudio desconta overhead das verificações: B1 e B2 estimados líquidos pequenos (aproximadamente 0,1% e 0,2% nas hipóteses padrão). **Não implementar B1 como rejeição incondicional**.

### Repetição independente AUTOMATIZADA na R65 (somente PREFIXO de DEMO3)

Workflow [40224191416](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40224191416): 3× R60 + 3× R64A, ROMs PERF originais sem qualquer contador. Extrai `bench_frames`, `bench_start_vb` e `_g_vblankCount` diretamente da WRAM via RSP, interrompendo apenas `I_FinishUpdate` e lendo antes da atualização da contagem do quadro atual.

| Tic | R60 FPS até esse tic | R64A FPS até esse tic | Ganho |
|---:|---:|---:|---:|
| 64 | 3,9416 | 4,0645 | +3,118% |
| 128 | 3,8043 | 3,9441 | +3,675% |
| 256 | 4,2618 | 4,4207 | +3,727% |

Três repetições iguais até o último VBlank em cada controle/candidato (desvio observado zero nesse cenário determinístico). **Não significa que o benchmark completo foi repetido 3 vezes:** o limite do usuário de no máximo **10.000 quadros por invocação BlastEm** impede o DEMO3 todo numa única execução automatizada de processo; 3× DEMO3 completo manual ainda pendente.

## 2. Motivação estrutural R65

O perfil R62 antigo colocava `WALL SETUP` em ~29,2% e `BSP` em ~17,3% das amostras por VBlank; amostragem de outra ROM / sessão, **não medição direta de ciclos da R64A stock**. O R64D identifica ~183 chamadas de parede e ~202 flats por quadro no prefixo. Evitar uma etapa custosa de busca/preparação antes do rasterizador pode ter custo-benefício melhor que micro-otimizar B1/B2.

`src/r_draw.c`:
- `R_RenderSegLoop` calcula geometria, clip de teto/chão, texcol, fracstep e chama `R20_WALLCOL` para tier mid, top ou bottom.
- `R20_WALLCOL` resolve o patch de textura (ou compõe coluna) via `R_DrawSegTextureColumn`, **antes** do rasterizador.
- `src/r22_video.inc` `R42_DrawPackedWall` rejeita por limites `R57_YMIN`/`R57_YEND` depois de toda essa preparação se a coluna está 100% fora do recorte vertical.

## 3. R65-P1: primeiro experimento isolado (NÃO ganho comprovado)

No `R_RenderSegLoop` substituímos somente três sites `R20_WALLCOL` por `R65_WALLCOL`, que testa:

```c
if (dcvars->yh >= R57_YMIN && dcvars->yl < R57_YEND)
    R20_WALLCOL(...);
```

Como `R42_DrawPackedWall` já descarta integralmente as colunas acima de `YMIN` ou abaixo de `YEND`, o objetivo é evitar **lookups de textura e chamadas de desenho que seriam descartadas**. A macro vale apenas sob `DOOM_R65_EARLY_WALL_CROP`, exige `DOOM_R64A_PROLOGUE`/R57/Pixel4/WallASM e **não introduz estado estático**. Fora dessa flag, mapeia diretamente para `R20_WALLCOL` da R64A.

**Não alterar:** avanço de `topfrac`, `bottomfrac`, `pixhigh`, `pixlow`, clips e solidcol; silhuetas/visplanes, masked-texture bookkeeping e BSP; kernel R60 ASM; R64A cache, modos R59, H32/H40, janela e controles.

**Hipótese com risco:** o custo das duas comparações extras por chamada pode ser maior que o custo de preparar texturas descartadas, principalmente com crop 0; se A/B mostrar regressão, **rejeitar imediatamente**. Variações dinâmicas de crop/cores no PLAY ainda pedem teste do usuário. Alterações indiretas no cache de texturas devem ser monitoradas em outras fases e hardware.

## 4. Critérios concretos da R65-P1

1. Compilar `r64a-perf` controle, `r65-perf` candidato, `r65-play` (MarsDev do runner). Verificar que `r64a-perf` recompilada é binariamente idêntica à R64A validada no run 40216335998.
2. **BSS = 57.900 B na PERF, 57.908 B na PLAY** ou sem qualquer acréscimo; sempre <=57.920.
3. Flags PERF diferem exclusivamente `-DDOOM_R65_EARLY_WALL_CROP`. ASM `R60_WallColumn` presente e tabelas R56/R59 sem alteração.
4. BlastEm smoke 800 e 10.000 quadros **por execução**. Process exit 0 não basta para alegar equivalência gráfica.
5. Comparar **5 framebuffers idênticos** em tics fixos, de novo R64A vs R65, dentro da mesma configuração sem profiler.
6. Benchmark prefixo A/B ≥3 execuções e DEMO3 completo manual, **sempre H40, crop 16/16, perfil de cor igual** para comparação. Repetir com H32/16/16 e sem crop para caracterizar ganho dependente do recorte, não misturar condições.
7. PLAY funcional: Start abre menu rápido; troca de 6 perfis de cor, H32/H40 e crops 0/8/16/32 em jogo; map progression E1M1–E1M8, portas, sprites, música, SRAM e hardware real.

**Decisão:** Só integrar na baseline caso apresente ganho repetido e nenhum byte/frame divergente ou regressão. Não perseguir custo estimado pequeno sem medir.

## 5. Pedido seguinte ao Cláudio

Depois de avaliar o R65-P1, procurar **uma única otimização** mais geral que melhore também a imagem sem crop:
- `R_StoreWallRange`: custo de `R_PointToDist` / `R_ScaleFromGlobalAngle`, `R15_SETUP_PRODUCT`, `rw_scalestep`; risco de overflow/DIVS.
- `R_RenderSegLoop`: caso custo de `R_LoadColorMap`, `R15_TAN_PRODUCT`, `FixedReciprocal`, seleção de textura; `DOOM_R21_LAZY_TEXCOL` e `DOOM_R21_SEGLOOP_LOCALS` já testados antes com ganho mínimo, portanto **não repetir sem hipótese nova**.
- `R_CheckBBox`: ângulos e `memchr`; extrair ciclos do ASM gerado antes de nova micro-otimização; 1 falso positivo no B1 vetorial exige fallback exato.
- Preservar todos os bytes de desenho; zero BSS e poucos acessos extra à WRAM.

A R60 nunca deve ser alterada; R64A permanece a candidata base até R65 passar em todos os gates.
