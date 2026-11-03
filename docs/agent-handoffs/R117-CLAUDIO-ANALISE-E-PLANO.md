# R117: análise de desempenho após a R116 e plano (Cláudio para o Werk)

**Branch:** `exp-claudio-r117-perf-20261103`. Ela parte de `exp-claudio-r117-performance-handoff-20261103`, que já contém a base `exp-chatgpt-r116-benchmark-accuracy-20261103`.
**Estado:** código pronto e **não executado**. Pela regra do usuário, o Werk executa no runner com os parâmetros abaixo.

## 0. Resposta curta
1. **O FPS mínimo de 0,3 é carga de mapa, não gameplay.** Há prova no código e nos números (seção 1). A R117 `meas` corrige a janela e passa a mostrar as cargas separadamente.
2. As demos dessincronizam e o jogador morre. O "use" da demo então **recarrega o mapa**, várias vezes por demo. O tempo oficial (9.213 s) inclui essas recargas. A `meas` conta quantas foram e quanto tempo levaram.
3. Os gargalos estão em três frentes:
   - **(a) loop de segs/colunas em `R_Subsector`** e **(b) desenho de colunas de parede**: demonstrados, mas só no início do E1M1 (perfil R110);
   - **(c) lógica de jogo em combate** (IA, colisão, visão, acessos à SRAM do mapa): fortemente indicada pelos tempos da sonda R116 sem render, ainda não demonstrada por rotina.

   O workflow R117 mede as três por mapa.
4. Há caminho para ganhar sem mudar pixel. O alvo mais promissor para os piores momentos (combate) é a lógica, e lá a equivalência pode ser provada de forma exata (seção 4).

## 1. Origem do FPS mínimo (0,3)
A sequência de chamadas é esta:
- `G_DoPlayDemo` chama `I_BenchmarkWindowReset()` dentro do bloco R116, **antes** de `G_ReadDemoHeader`;
- `G_ReadDemoHeader` chama `G_InitNew`, que chama `G_DoLoadLevel`, que chama `P_SetupLevel`, tudo **síncrono**.

Assim, a janela de 1 s de cada demo, a partir da segunda, começa com a carga inteira e fecha no primeiro quadro: 1 quadro dividido por cerca de 3,3 s dá **0,3 FPS**.

O número escala com o clock: 0,6 FPS a 13 MHz, ou seja, carga de ~1,7 s, limitada pela CPU. É exatamente o padrão de uma carga.

Mortes também recarregam: `G_DoReborn` gera `ga_loadlevel` e chama `G_DoLoadLevel`, e **nenhuma** janela é zerada nesse caminho. Na sonda R116 (run 41637745015), `leveltime < gametic` em E1M2, E1M3, E1M4, E1M5, E1M6, E1M9 e na especial, ou seja, houve recargas.

**Correção (`apply_r117.py`, variante `meas`):**
- `G_DoLoadLevel` mede a si mesmo e chama `R117_LoadDone`, que reinicia a janela **depois** de toda carga (primeiro mapa, próxima demo e recarga por morte).
- A média, os quadros e o tempo **não mudam**: continuam pelo relógio de parede.
- Linhas novas na tela:

  | Linha | Conteúdo |
  |---|---|
  | 9 | `1% LOW FPS` |
  | 11 | `MIN AT E1Mx TIC n` (local da pior janela) |
  | 13 | `WORST/P99 FRAME VB` |
  | 16 | `LOADS / LONGEST S` |
  | 18 | `LOAD TIME (SECONDS)` |

- O estado novo vai forçado para `.data`, cerca de 150 B: o BSS não muda, e a pilha perde ~150 B de folga (veja a seção 5).
- O custo por quadro é de algumas instruções.

**Atenção à zone:** o mínimo de 832/448 B vem da entrada **"E1M6 UV-Max no cap"**, um modo de teste que **não** é o jogo entregue. No jogo, a R115 limita o E1M6 UV ao conjunto HMP (9,7 KB livres, R114). Na sonda R116 essa entrada deu 1.408/576. Isso não muda o benchmark oficial, mas o alerta de memória não deve ser lido como risco do jogo. Decisão do usuário: manter ou não o E1M6 sem limite no Run All oficial.

## 2. Dados que já existem
**Perfil R110** (BlastEm, R107, DEMO3 no início do E1M1, ~470 tics, amostra por VBlank):

| Função | % |
|---|---|
| `R_Subsector` (loop de segs/colunas inline, 6 cópias) | 34,7 |
| `R60_WallColumn` (kernel de parede, hoje R113) | 12,0 |
| `R_DrawSegTextureColumn` (preparo da coluna) | 10,6 |
| `D_DoomLoop` (inclui espera) | 7,8 |
| Sprites (`R_DrawColumnSprite`, `R_DrawVisSprite`, `R_ProjectSprite`) | 8,2 |
| `R_PointToAngle16` + `R_ScaleFromGlobalAngle` | 5,7 |
| `R23_MapRead` (SRAM) | ~3,5 |
| `P_CheckSight` | 1,6 |
| `P_RecursiveSound` | 1,3 |

**Sonda R116 sem render** (run 41637745015): tics alcançados em ~9.950 quadros emulados, que incluem boot e cargas:

| Demo | Tics | VB/tic (aprox., limite superior) |
|---|---|---|
| E1M1 | 2.601 (terminou) | ≤ 3,8 |
| E1M8 | 3.300 (terminou) | ≤ 3,0 |
| E1M4 | 3.523 | ~2,8 |
| E1M2 | 2.485 | ~4,0 (com recargas) |
| E1M5 / E1M6 / E1M6S | ~1.700 | ~5,8 |
| E1M9 | 1.312 | ~7,6 |
| E1M3 | 1.254 | ~7,9 (com recargas) |
| **E1M7** | **919, sem recarga** | **~10,4** |

O quadro médio do Run All é de ~12 VB (60/4,96). Se o E1M7 gasta ~10 VB por tic só em lógica, **nos mapas de combate a lógica pode ser metade ou mais do quadro**. A R110 não via isso porque media o começo do E1M1, com pouco combate.

Ressalva: parte do tempo pode ser carga ou espera escondida (por exemplo, texto do HUD esperando o VBlank). O R117 separa esses casos.

## 3. Os 3 maiores gargalos

| # | Gargalo | Evidência | Status |
|---|---|---|---|
| 1 | Loop de segs/colunas (`R_Subsector`: clip por coluna, preenchimento de flats R95, chamadas de parede) | R110: 34,7% | demonstrado (E1M1) |
| 2 | Colunas de parede (kernel R113 + `R_DrawSegTextureColumn`) | R110: 22,6% | demonstrado (E1M1) |
| 3 | Lógica em combate: IA, colisão (`P_TryMove`/`P_CheckPosition`/secnodes), visão, propagação do som e **acessos à SRAM do mapa** (validcount de linha, secnodes, cabeças do blockmap) | sonda R116: até ~10 VB/tic | indicado; o R117 demonstra |

Cada acesso `R23_GET`/`R23_SET` abre uma janela de SRAM com a IRQ mascarada (R104): `move sr`, `ori`, duas escritas em `$A130F1`, `movep`, mais a chamada. Estimo **~120–150 ciclos por campo**. `P_BlockLinesIterator` lê o validcount de cada linha na SRAM, e `P_CreateSecNodeList`/`P_DelSeclist` fazem várias operações de secnode a cada movimento de coisa.

## 4. Cinco propostas, por ganho esperado / risco / esforço
As estimativas são provisórias e serão revistas com o perfil R117. Os critérios de aceite valem para todas (seção 6).

| # | Proposta | Rotina | Ganho esperado | Risco | Esforço |
|---|---|---|---|---|---|
| A | **Janela única de SRAM por operação lógica**: validcount lido e escrito numa só janela; `P_CreateSecNodeList`/`P_DelSeclist` com uma janela por lista; cabeça do blockmap e cadeia na mesma janela. Janela limitada (≤ ~2.000 ciclos) para não atrasar o VBlank. | `p_maputl.c`, `p_map.c`, `p_sight.c`, `r23_mapmem.c` | ~60–100 ciclos economizados por acesso fundido; **3–8% nos mapas de combate**, ~1% no E1M1 | médio (SRAM/IRQ: regra R104, teste no console obrigatório) | médio |
| B | **Loop de colunas de `R_Subsector` em asm**, só para o caso comum (parede sólida + flats R95), com registradores alocados à mão. As tentativas em C falharam por spills (R111). | `R_Subsector`/`R_RenderSegLoop` | 15–25% de 35% = **5–9% no render** | alto (6 cópias, pixel-idêntico obrigatório) | alto |
| C | **Kernel de parede**: desenrolar 2× e manter a fase em registrador entre pares. Hoje são ~116 ciclos por par; alvo ~95. | `r113_hilut_wall.s` | ~18% de 12–15% = **2–3%** | baixo (A/B de pixels) | baixo/médio |
| D | **Tempo de carga** (`P_SetupLevel`: inicialização do blockmap e do mapa na SRAM, sondas de SRAM, R84/R24). Não acelera o gameplay; encurta recargas e melhora a média oficial porque as demos recarregam muito. | `p_setup.c`, `r22_blocklinks.c`, `r23_mapmem.c` | depende de LOADS × duração (a `meas` mede); provavelmente **1–3% da média** | baixo | baixo/médio |
| E | **Sprites**: o caminho mascarado sem `LSL.B #4` (técnica R113), com guarda para a LUT composta. | `R_DrawColumnSprite` | **0,3–0,5%** | baixo | baixo |

Ordem recomendada:
1. Rodar o R117 (perfil).
2. Escolher a proposta. A **A** é a primeira candidata se o perfil confirmar a lógica nos mapas pesados; se não, a **C**.
3. A **D** é independente e pode vir em paralelo (só a média).
4. A **B** só depois da A e da C.

## 5. O que o workflow `r117-claudio-profile.yml` faz (o Werk dispara)
1. **Build** de dois conjuntos com a cadeia completa até a R116:
   - `base` = R116 exatamente como no handoff do Werk;
   - `meas` = R116 + `apply_r117.py`.
   - Confere ROM ≤ 4 MiB e BSS ≤ 57.920.
   - Copia ROMs e ELFs **só** para `/home/dan/Projetos/Personal/r117-profile/run-<id>-<attempt>/{c-base,c-meas}/`.
2. **Perfil da `base` (PERF)**, 3 rodadas por demo (30 no total, ≤ 9.800 quadros cada, `scripts/lab/r117_profile.py`):
   - `logic`: sem render desde o início; dá VB/tic da lógica e categorias de lógica.
   - `r150` e `r450`: sem render até o tic 150 ou 450, depois render ligado. Dão VB/quadro, P99, as piores janelas de 1 s dentro do trecho e as categorias da pior janela.

   As categorias vêm do nome da função, e helpers (`__mulsi3`, `R23_MapRead`…) entram na categoria de quem chamou. Amostras ≥ 90 no mesmo tic contam como `LOAD`.
3. **Smoke da `meas`:** PERF da demo 1 com render (3.000 quadros) e boot do PLAY.
4. **Upload** só de relatórios: `R117-PROFILE-SUMMARY.json`, `PROFILE.json`/`frames.tsv`/`samples.tsv` (só PCs e contagens), logs, MANIFEST e BUILD.log. **Nada de ROM, ELF ou demo.**

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r117-perf-20261103
date -u > .github/triggers/r117-claudio-profile.trigger
git add .github/triggers/r117-claudio-profile.trigger; and git commit -m "R117: trigger profile"; and git push
```

**O que me trazer:**
- as 10 notas "R117 demo k";
- o artefato `r117-profile-reports`;
- os avisos de ROM/BSS da `meas`;
- qualquer `::warning` de rodada de perfil.

**Para o usuário (opcional, demora ~2,5 h):** Run All na `r117-meas-pl` com o procedimento oficial, para ter LOADS e o mínimo de gameplay real. Isso **não** substitui o baseline de 4,96: a média é calculada do mesmo jeito.

**Pilha:** a `meas` acrescenta ~150 B em `.data`. A folga medida antes era de ~930 B (pico 1.632 de 2.562), então deve sobrar ~780 B. Se o Werk quiser confirmar, use `r82_stack_probe.py` na `meas` (opcional).

## 6. Critérios de aceite para qualquer otimização (como o handoff R117 pede)
- Controle e candidata no mesmo job, uma mudança por commit.
- **Pixels idênticos:** `r70_capture`/`r70_compare` com Off e On A2/L3 pós-passe.
- **Lógica idêntica** (vale para a A, a D e qualquer coisa fora do render), usando a sonda sem render (`r116_demo_probe.py`, 10 demos), que tem que dar os mesmos números da `base`:
  - `ticks_seen`, `last.gametic` e `last.leveltime`;
  - `r116_res` (kills, items, secrets, mortes, tic de saída).

  Mais forte, se precisar: hash de posição/ângulo/vida de todos os mobjs a cada 35 tics.
- Zone, pilha e BSS sem piora; nenhum `I_Error`.
- Run All oficial: média ≥ 4,96 e mínimo de gameplay não pior. Na `meas` o mínimo passa a ser de gameplay; a comparação justa é `meas` base contra `meas` candidata.
- Console por último. Mudanças em SRAM/IRQ (proposta A) **exigem** console antes de aceitar.
