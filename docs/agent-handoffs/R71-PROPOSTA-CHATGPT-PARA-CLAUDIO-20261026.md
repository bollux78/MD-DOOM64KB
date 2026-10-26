# R71 — revisão independente ChatGPT e proposta de otimizações para Cláudio
**Data:** 2026-10-26. **Status:** proposta de investigação, **NÃO** é ROM/benchmark/merge aprovado.

## Decisão do mantenedor
**Abandonar R70-D** como linha de desenvolvimento. Não criar combinações com R70-D, não fazer mais builds/otimizações nessa branch e não promovê-la. Conservar branch/run/artifact **apenas como registro do experimento negativo**, sem deletar histórico.

**Manter R66** `f5a9daa7a0bd7225bbc227630defc73c67c34f1e` como controle imutável, **R70-A12** como melhor candidata atualmente medida, ainda **não promovida a baseline de hardware**. R71 deve oferecer experimentos isolados, com ganho de pixels **exatamente iguais** aos da R66/R70-A12 no mesmo modo, e Cláudio deve fazer sua revisão crítica e propor hipóteses adicionais antes da compilação.

## 1. Evidência confirmada da R70
Fontes: runs [R70-A 40366427794](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40366427794), [R70-A 40362045678](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40362045678), [R70-D 40368984208](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40368984208); handoffs [R70-A](../agent-handoffs/r70a-segloop.md) e [R70-D](https://github.com/bollux78/MD-DOOM64KB/blob/exp-claudio-r70d-segloop-asm-20261026/docs/agent-handoffs/r70d-segloop-asm.md); DEMO3 NTSC/clock stock, H40, recorte H/V16, 2134 quadros da tela de resultados, 2133 tics comuns de comparação.

| Variante | FPS exibido no hardware/BlastEm do mantenedor | Tempo DEMO3 exibido | Vblanks vs controle na captura RSP | Diferenças do framebuffer vs R66 |
|---|---:|---:|---:|---:|
| R66 controle | 7,21 | 295,88 s | referência | — |
| R70-A1 `LOCALS` | 7,25 | 294,53 s | **−0,47%** | **0 bytes**, 2133 tics |
| R70-A2 `INVARIANTS` | 7,26 | 294,05 s | **−0,63%** | **0 bytes**, 2133 tics |
| R70-A12 ambas | 7,26 | 293,77 s | **−0,72%** | **0 bytes**, 2133 tics |
| R70-D ASM completo | 7,20 | 296,38 s | **+0,16%** (mais lento) | **0 bytes**, 2133 tics |

As telas do mantenedor mostram as cinco ROMs com 2134 frames. As porcentagens são do **comparador de vblanks do runner**, não calculadas a partir dos FPS arredondados da tela. A captura também reporta 7,22 FPS equivalentes para R66 sobre os 2133 intervalos comuns, enquanto a tela final mostra 7,21 sobre 2134 frames: **não confundir universos/denominadores**. Repetição do controle apresentou sequência de vblanks idêntica. O ganho pequeno é determinístico nesse ambiente, mas não garante melhoria material no Mega Drive real ou em outras cenas.

- A1 usa `DOOM_R21_SEGLOOP_LOCALS`; A2 copia invariantes do segmento para locais. O loop `R_RenderSegLoop` é **inlinado por LTO em `R_Subsector.lto_priv.0`**: aumento de **+74 bytes A1, +518 bytes A2, +774 bytes A12**, não medir somente a presença de símbolo `R_RenderSegLoop`. Nenhum aumento da BSS: **57.900 bytes** nos controles/variantes, com teto atual de **57.920 bytes**, margem de **20 bytes**.
- R70-D gerou um laço 68000 com `struct r70d_seg` e callouts C para paredes/sky/flats e caminhos excepcionais. Ficou mais lento apesar de `2133/2133` quadros visualmente idênticos. A build mudou **25 símbolos** no relatório de disassembly, inclusive funções não relacionadas, demonstrando que LTO/layout pode interferir na avaliação; diferenciar efeito local de layout.
- O comparador R70-D escreveu `Fastest pixel-identical variant ... r70d (+0.16%)`, **formulação enganosa**, pois é a única candidata pixel-idêntica analisada além do controle e é **mais lenta que R66**. Ajustar o relatório para nunca declarar vencedora uma variante regressiva frente ao controle.
- As primeiras runs R70-A falharam por **harness instável**: o teste legado incluía `flat.UNREAD.colormap` não inicializado/ASLR, inclusive controle diferente dele próprio. O teste estrito corrigido passou em **20.000 cenários**, com **8.955.451 eventos** e **5/5 mutantes**. [Diagnóstico completo](../review-r70/R70A-DIFFTEST-DIAGNOSIS.md).
- O comparador de pixels lê o **framebuffer do renderer 76×44 (3344 bytes)**, não prova identidade de HUD, CRAM, áudio, VDP, toda a campanha ou comportamento no cartucho. A política R66 COLPAIR já é **aproximação deliberada** em relação às versões anteriores: exigência de identidade R71 é **relativa à R66**, não ao Doom PC.

## 2. Onde procurar ciclos — profiling R68 completo
[R68 run12](https://github.com/bollux78/MD-DOOM64KB/blob/exp-claudio-r68-profiling-20261025/docs/review-r68/R68-RESULTS-run12-fulldemo.md), [revisão metodológica independente](https://github.com/bollux78/MD-DOOM64KB/blob/exp-chatgpt-r70-renderer-review-20261026/docs/agent-handoffs/R68-R69-REVIEW-CHATGPT-20261026.md):

- **74,6%** do tempo medido em **BSP + paredes + planos** (fases instrumentadas); logic 13,2%, sprites/masked 9,6%.
- Amostras de PC da DEMO3 completa: **30,3% no grupo C de colunas**, **14,0% em setup + geometria de segmentos**, **11,8% no kernel ASM da parede**, 8,3% sprites, 7,3% chão/teto, 7,3% BSP.
- Esses valores **NÃO** são tempo exclusivo de uma função, tampouco economia esperada se a função desaparecer: grupos abrangem múltiplas funções e código LTO; sampling tem quantização em buckets de 8 bytes, exclusão de VBlank e overhead. **Não** comparar FPS de ROM instrumentada com R66/R70-A não instrumentadas.
- Prioridade: **reduzir preparação/repetição de trabalho em C por coluna**, mantendo o **kernel R60**; em segundo lugar geometria por segmento. A R70-D demonstrou que reescrever *todo* o laço em assembly não garante ganho.

### Código efetivo do caminho quente (verificação do repositório, branch R70-A)
- `src/r_draw.c:2708-3179`: `R_RenderSegLoop` (inclui COLPAIR e A1/A2).
- `src/r_draw.c:2591-2624`: `R_DrawSegTextureColumn` escolhe simples/múltipla/composta, chama `R_GetColumn`, `W_GetLumpByNum`, `R_ComposeColumn`.
- `src/r_draw.c:1404-1435`: `R_GetColumn`, `patchcount==1` e busca em patches.
- `src/r_draw.c:2630-2679, 3571-3581`: rotas **experimentais pré-existentes** `DOOM_R20_WALL_HOIST` e `DOOM_R20_COMPOSITE_HOIST`; há um `#error` contra ativá-las simultaneamente.
- `src/r22_video.inc:680-854`: **`R42_DrawPackedWall` está aqui** (incluído por `src/i_genesisv.c`, NÃO em `src/r_draw.c`); por coluna valida clipping, seleciona LUT via `R64A_Get/R64A_LUT`, calcula fração/destino e chama `R60_WallDraw` no caminho de LUT composta/Pair-V quando `!colormap && count>=2`.
- `src/r22_video.inc:88-123`: `r64a_ctx` já possui contexto da janela/paleta por frame, `R64A_Get` faz verificação em cada coluna; no caminho normal só reconstitui contexto quando inválido.
- `src/r60_pair_wall.h` e `.s`: interface e kernel de colunas efetivamente usado; **preservá-lo** no primeiro experimento R71.
- `src/r_draw.c:3266-3581`: `R_StoreWallRange`, setup de `rw_distance`, projeção nos extremos, scalestep, tiers, slopes e chamada ao seg loop.
- **Armadilha crítica:** `src/r_sky.c:62-78`: `R_DrawSky` **sobrescreve `dcvars->colormap`, `fracstep`, `texturemid` e `source`**. Não hoistar `colormap`, `fracstep` ou origem de textura supondo estado constante após céu. Respeitar exatamente os efeitos originais na coluna seguinte, inclusive a restauração COLPAIR do `fracstep`.

## 3. Experimentos R71 propostos — isolados e mensuráveis

### R71-B1 — prologue/colormap/clipping do R42 por coluna (**prioridade alta**)
**Hipótese (NÃO medida):** eliminar trabalho repetitivo no C de `R42_DrawPackedWall` e/ou especializar o fast path dominante antes de chamar `R60_WallColumn`. Inspecionar o disassembly real de `R_Subsector`, `R42_DrawPackedWall` e `R_DrawSegTextureColumn` para contar cálculos de janela, seleções de LUT, endereços, teste `count`, prólogo/MOVEM e consultas redundantes em `R64A_Get/R64A_LUT`.

Possíveis alternativas **mutuamente exclusivas na primeira rodada**:
- **B1a:** preparar uma visão imutável de `r64a_ctx` e/ou metadados de clipping por **segmento** quando é seguro, passar por locais/stack, manter fallback para sprites/sky/transições de menu. Não replicar 24 bytes de contexto em BSS nem copiar cegamente a cada coluna.
- **B1b:** fast path dedicado ao caso normal de **parede texturizada + colormap composta válida + count>=2 + viewport corrente**, de forma que as checagens repetidas de colormap/janela sejam hoistadas, e manter a rotina original para casos de borda/sky/colormap não usual. Não duplicar o loop de pixels: chamar o kernel R60 já validado.
- **B1c:** cache local/por segmento, **chaveado pelo colormap efetivo e paridade** (e modo R59), de `R64A_LUT`, revalidando após `R_DrawSky` e mudanças de modo/paleta; avaliar se a revalidação custa mais do que economiza.

**Não presumir que um inline/novo parâmetro é mais barato.** GCC pode gerar mais spills, chamadas e code growth. Disassembly e medição decidem. **Nenhuma alteração de shading, seleção de amostras, CRAM ou COLPAIR.**

### R71-B2 — resolução de fonte de textura uma vez por segmento (**prioridade alta, mas verificar R20 antigo**)
**Hipótese:** `R_DrawSegTextureColumn` repete resolução de patch/coluna por parede. Há uma implementação anterior sob `DOOM_R20_WALL_HOIST` para texturas **single-patch, não sobrepostas**, e sob `DOOM_R20_COMPOSITE_HOIST` para hash de coluna composta. Primeiro **localizar os benchmarks/fracassos históricos R20**: não repetir uma otimização antiga apenas porque ela existe.

- Testar **uma** rota de cada vez (simples, composta). Pré-calcular `W_GetLumpByNum(patches[0].patch_num)` e `widthmask` **apenas quando o ponteiro é válido durante todo o uso**. Preservar `patch->columnofs[texcolumn & widthmask] + 3` e mascaramento.
- Evitar chamar `R20_PrepareWallSource` três vezes desnecessariamente; a seleção de mid/top/bottom decorre da parede. Medir ganho de segmentos largos vs custo de preparação de segmentos curtos.
- Guardar contexto **na pilha** se possível (não criar 3 novos globais): **BSS tem só 20 bytes de margem**; verificar impacto de stack/heap e lifetime de dados em `__far`/SRAM/scratch.
- Não cachear `dcvars.source` de coluna composta ou buffer temporário sem comprovar lifetime. R66 já reutiliza `r66_src` nas ímpares; preservar **ordem de chamadas e resultado**; considerar portas, texturas com múltiplos patches e masked.
- A rota R20 `WALL_HOIST` e `COMPOSITE_HOIST` são incompatíveis por design; o plano R71 **não** manda ligá-las juntas.

### R71-B3 — eliminar custos intermediários de chamada/estrutura (**prioridade média**)
Se o disassembly comprovar muitas cargas/armazenamentos de `draw_column_vars_t`, CALL/RET ou MOVEM no trajeto `R_RenderSegLoop → R_DrawSegTextureColumn → R_DrawColumnWall → R42_DrawPackedWall → R60_WallDraw`, testar **exatamente um** wrapper especializado de parede, deixando sprite/fuzz/flat intactos. Atenção: o compilador/LTO já inlina várias rotinas. Comparar código real, não apenas o número de funções no fonte. **Evitar a arquitetura R70-D** de laço ASM grande com callouts C.

### R71-C1 — setup/geometria por segmento (**fase seguinte, independente da B**)
Examinar `R_StoreWallRange`, `R_ScaleFromGlobalAngle`, `R_PointToDist`, `FixedMul`, `R15_SETUP_PRODUCT`, divisões signed e bounds. Buscar subexpressões repetidas, reloads de `__far`/SRAM e indireção do estado, com prova de identidade bit a bit. Preservar sinal, overflow, truncamento, saturação, ordem de avaliação e os casos `stop==start`, escala extrema, ângulos nos limites, portas e pisos altos. **Não** reativar aproximações geométricas e **não** combinar B e C na primeira matriz.

### R71-L (exploração posterior, maior risco)
`DOOM_R21_LAZY_TEXCOL` hoje é **explicitamente incompatível com `DOOM_R66_COLPAIR`** no código (`#error`). Só reconsiderar se Cláudio demonstrar prova de equivalência e protocolo correto de invalidar `r66_arm` e `r66_src` ao pular colunas. Não remover o guard apenas para compilar. Não iniciar esta linha antes de B1/B2; requer testes extras de sky, masked, clipping e parity.

## 4. Plano experimental / instrumentação / acceptance gates

1. **Cláudio revisa criticamente este plano antes de codificar** e devolve priorização própria (mín. 3 hipóteses: custo atual em assembly, provável economia por evento, frequência estimada, risco visual/memória, ferramenta de prova, flag e hipótese de refutação). Não transformar a proposta em ordem para implementar tudo.
2. Criar branch nova de R71 **a partir de R70-A commit `4668ca9`**, não de R70-D. R66 deve compilar com flags R71 **off** em **ROM byte-idêntica** ao SHA256 `2c93cdbb78c72eabcdd2f816db6849f6dd877420a59c44424fae6b7a4ae7ca36`. R70-A12 sem flags R71 mantém ROM/bench própria. Código fora dos guards não deve modificar a R66. Um experimento por flag, nomes propostos `DOOM_R71_B1`, `DOOM_R71_B2`, `DOOM_R71_C1`.
3. Primeiro usar provas no **host**, compilando texto real das funções quando viável, asserções de equivalência para eventos **efetivamente lidos** (não repetir falha `flat.UNREAD.colormap`), e mutantes sensíveis. Cobrir bordas, top/bottom, masked, céu que altera `dcvars`, par/ímpar, R57 crop 0/16/32 e H32/H40, tintas/tabelas R59, source/cache lifetime, texturas simples/compostas, escala e uint16 wrap. UBSan/ASan onde aplicável; sem validar pixels pelo hash da ROM.
4. No runner `x360-linux`, compilação **não instrumentada**, uma pasta/checkout por variante para evitar arquivos cruzados; build MarsDev/SGDK real. Conferir `m68k-elf-objdump` e **`R_Subsector.lto_priv.0`** (LTO), símbolos/stack; ROM ≤ 4 MiB, **BSS ≤ 57.920 B** (preferir zero de incremento), integridade do WAD local previamente pinado. Sem publish do WAD. Não usar R70-D como referência.
5. Matriz **primeira rodada**: R66 controle, R70-A12 controle incremental, R71-B1 isolada sobre R66, R71-B2 isolada sobre R66. Se um B vencer, testar depois `R70-A12+B` para ganho aditivo; não presumir aditividade. Opcional controle repeat para determinismo; não misturar C1 até fechar B.
6. Capturar DEMO3 completa em **BlastEm stock clock NTSC 60 Hz**, mesmos 2134 frames, H40 crop H16/V16, mesmos flags de cor e conteúdo. Comparar por **game tic comum** e **bytes reais do framebuffer**; reportar vblanks totais, FPS eq., tempo exibido, deltas vs R66 **e vs A12**, p50/p90/p99, terços da demo e cenas extremas; `run-to-run` controle. Uma captura com `status: timeout` apesar de 2134 frames merece diagnóstico de condição de término, não deve ser descrita como sucesso de processo sem explicação.
7. **Critérios de abandono:** qualquer diferença de pixels não justificada num caminho prometido bit-exato => reprovar; falha de heap/stack ou BSS => reprovar; ganho ≤0,3% em BlastEm => tratar como marginal/descartar salvo ganho claro em hardware; ganho ≥0,5–1% sem regressão em terços => candidato a hardware; regressão >0,5% em algum terço => investigar/perder prioridade. Estes são **critérios propostos**, não garantia estatística; bench determinístico pode sofrer mudanças de layout.
8. **Hardware**: usuário decide promoção após testar ROMs em Mega Drive real, stock clock, E1M1–E1M8, portas, cielo, masked, música XGM2, START/menu rápido, H32/H40 e crop. Não inferir validade de todo o jogo a partir da DEMO3.

## 5. Perguntas expressas ao Cláudio
1. Qual é o gargalo **exato no disassembly** do caminho `R42_DrawPackedWall / R_DrawSegTextureColumn` sob A12? Quantos acessos, chamadas, branches e qual frequência na DEMO3? Mostrar evidência, não supor 30% de uma função.
2. Existe benchmark histórico R20 que **desaprova** `DOOM_R20_WALL_HOIST` ou `DOOM_R20_COMPOSITE_HOIST`? Quais condições eram diferentes (8×8 vs Pixel4, compilador, LTO, R66 COLPAIR)? Se negativo, explicar por que não repetir.
3. B1 é seguro com `R_DrawSky` alterando `dcvars` e com `R64A_FrameBegin/End`, mudanças H32/H40/R57, modo de cor R59 e `fullcolormap`? Demonstrar caso de exceção e fallback.
4. Há uma ideia **nova e mais barata** que B1/B2/C1? Proponha ao menos 2 alternativas suas, ordenadas por ROI; inclua cálculo ou contagem de eventos e estratégia de rollback.
5. Por que a R70-D alterou 25 símbolos e perdeu velocidade? A hipótese callouts/MOVEM/context struct é plausível, mas distinguir de layout/LTO com comparação em `R_Subsector` e regiões executadas.
6. Como tornar `r70_compare.py` correto ao anunciar vencedora: exigir **delta < 0** vs controle e `0` bytes divergentes; tratar `R70-D +0,16%` como regressão, não 'fastest'.

## Resumo executivo
**Não perseguir novamente R70-D. Não trocar o kernel R60 de parede.** Explorar **B1: prologue/LUT/clipping**, **B2: resolução de fonte por segmento**, então **C1: geometria de segmento**. Cláudio deve propor suas próprias variantes, auditar os guards existentes e revisar o plano. O objetivo é **ganho mensurável acima da R70-A12** mantendo **exatamente o mesmo framebuffer** e preservando a R66.
