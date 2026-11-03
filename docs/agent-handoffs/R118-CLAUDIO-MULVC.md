# R118: primeiras otimizações exatas de lógica (Cláudio para o Werk)

**Branch:** `exp-claudio-r118-mulvc-20261103`, criada a partir de `exp-chatgpt-r117-meas-lowmem-20261103` (R117 lowmem, aprovada no BlastEm pelo usuário).
**Estado:** código pronto, **não executado**. O Werk dispara.

## 1. O que o perfil R117 mostrou (run 41665591138, base R116, BlastEm)
**Só lógica (10 demos):**

| Função | % |
|---|---|
| `P_CheckSight` | 18,5 |
| `P_MobjThinker` | 12,0 |
| `P_CheckPosition` | 11,1 |
| **`__mulsi3`** (multiplicação 32×32 da libgcc) | **10,7** |
| `R23_MapRead` / `R23_MapWrite` (estado do mapa na SRAM) | 8,5 + 4,6 |
| `P_SetThingPosition` | 6,0 |
| `R_PointInSubsector` | 5,2 |

**Com render:**
- A lógica ocupa ~25–45% do quadro nos mapas de combate.
- As piores janelas são E1M3 (1,35 FPS), E1M7 (1,6) e E1M9 (1,8), e nelas visão e colisão aparecem entre as primeiras categorias.
- O resultado bate com o Run All da R117 meas: o mínimo de gameplay (1,4 FPS) ficou no E1M3, tic 306.

## 2. Candidatas (uma de cada vez e a combinação, sem RAM nova)

| Set | Mudança | Por que é exata |
|---|---|---|
| `meas` | controle (R117 lowmem) | — |
| `mul` | (1) liga os caminhos já existentes `DOOM_R47_MUL_LOGIC` (`p_sight.c`, `p_maputl.c`) e `DOOM_R47_MUL_BSP` (`R_PointOnSide` → `R_PointInSubsector`); (2) em `P_DivlineSide`, que roda a cada nó e linha da visão, usa **um MULS.W** por produto | Os helpers R47 dão exatamente os 32 bits baixos do `__mulsi3`. Os dois fatores de `P_DivlineSide` são `int32 >> 16`, que sempre cabem em int16. O `scripts/lab/test_r118_mul.py` confere 1,2 milhão de casos. |
| `vc` | Em `P_CrossSubsector` (visão), o validcount da linha é testado e marcado numa **única janela de SRAM** (`R89_VisitLine`, o mesmo que `P_BlockLinesIterator` já usa), em vez de `R23_GET` + `R23_SET` (duas janelas mais o despacho genérico) | Mesma semântica: pula se for igual, senão grava. Os dois lados são uint16. |
| `mulvc` | as duas | — |

## 3. O workflow `r118-claudio-mulvc.yml`
1. **Build** dos 4 sets (pl + pf).
   - Confere ROM ≤ 4 MiB e BSS ≤ 57.920.
   - **Confere que `.data` e `.bss` de cada candidata são iguais aos do controle.** A lição da R117: qualquer byte de RAM pode quebrar o boot.
   - As ROMs ficam só em `/home/dan/Projetos/Personal/r118-mulvc/run-…/`.
2. **Identidade da lógica:** `r118_logic_check.py`, 10 demos × 4 builds, sem render.
   - A cada 100 tics grava uma impressão digital: gametic, leveltime, índices do `P_Random` (se os símbolos existirem), contagem de thinkers, sha1 de x/y/z de todos os mobjs e a posição do jogador.
   - Os checkpoints em comum precisam ser idênticos. Divergência gera `::error`.
3. **Pixels:**
   - Shadow Off: DEMO3 com `r70_capture`/`r70_compare` nos 4 sets (também dá o tempo do DEMO3).
   - Shadow On: A2 e L3 pós-passe com `r93b_capture`, em meas × mulvc.
   - Pixels diferentes fazem o step falhar.
4. **Tempo nas demos pesadas:**
   - `r117_profile.py` com render a partir do tic 150 em E1M3, E1M7, E1M9 e na especial, nos 4 sets.
   - `r118_ab.py` compara os VBlanks no **mesmo intervalo de tics**, que tem o mesmo trabalho porque a lógica é idêntica.
5. **Smoke do PLAY** da mulvc.
6. **Upload** só de relatórios.

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r118-mulvc-20261103
date -u > .github/triggers/r118-claudio-mulvc.trigger
git add .github/triggers/r118-claudio-mulvc.trigger; and git commit -m "R118: trigger"; and git push
```

**O que me trazer:**
- as notas `R118 logic dK` (10);
- `R118 DEMO3 Shadow Off A/B`;
- `R118 Shadow On mode 1/2`;
- `R118 heavy-demo rendered A/B`;
- os avisos de ROM/BSS e o resultado da checagem de `.data`/`.bss`;
- o artefato `r118-mulvc-reports`.

## 4. Expectativa e critério
- **Expectativa (estimativa):**
  - `mul`: −1 a −3% de VBlanks nas demos pesadas, perto de zero no DEMO3;
  - `vc`: −0,5 a −2%.
  - O ganho deve aparecer mais nas piores janelas (mínimo) do que na média.
- **Para aprovar:**
  - lógica idêntica nas 10 demos;
  - pixels idênticos;
  - RAM igual;
  - ganho no A/B das demos pesadas.
- **Depois:** o usuário faz o Run All oficial no BlastEm com a ROM pl aprovada (comparar com a R117 meas: 4,96 de média e 1,4 de mínimo), e por último o console. A `vc` mexe numa janela de SRAM: o caminho é o mesmo da `R89_VisitLine`, já validada no console, mas ainda assim tem que passar no console.

## 5. Próximos alvos (R119+, dependem deste resultado)
1. **Secnodes na SRAM:**
   - `P_CreateSecNodeList`, `P_DelSeclist` e `P_AddSecnode` usam vários `R23_GET`/`SET`, cada um com sua janela;
   - `node_address` divide por `sizeof(msecnode_t)`, o que pode virar `__udivsi3`;
   - alvo: acessores especializados e uma janela por operação. São `P_SetThingPosition` (6%) e boa parte de `R23_MapWrite`.
2. **`P_CheckPosition`/`PIT_CheckLine`:** mesma técnica, aplicada à leitura da cabeça do blockmap e da cadeia de things numa janela.
3. **`P_CheckSight`:** o corpo do laço de segs (18,5%). Precisa do disassembly do runner (`objdump` de `P_CheckSight`, só texto, sem dados de demo) para ver o código gerado.
