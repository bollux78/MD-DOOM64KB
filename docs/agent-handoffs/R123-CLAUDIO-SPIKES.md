# R121: resultado, e R123: candidatas para os picos do E1M7 (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`. **Base:** R122 layout, que o usuário aprovou no console (som corrigido).
**Estado:** código pronto, **não executado**. O Werk dispara.

## 1. O que a R121 provou (run 41754556915)
- **A/A:** o mesmo ROM em dois processos dá `frames.tsv` idêntico e 0,00%. A medida é determinística.
- **R120 refeita** com o BlastEm fixo (divisor 7) e o A/B estrito: tudo válido.

  | Variante | Total | Demo 3 | Demo 7 | Demo 9 | Demo 10 |
  |---|---|---|---|---|---|
  | sight | +0,10% | +0,16% | +0,08% | +0,03% | +0,12% |
  | collision | +0,06% | +0,05% | +0,05% | +0,11% | +0,02% |
  | both | +0,17% | +0,21% | +0,14% | +0,17% | +0,17% |

  Bate com o Run All do usuário (+0,14%). **O falso +167% foi mesmo o controle rodando com o 68000 7× mais rápido.** A R120 não traz ganho, como já se sabia.
- **E1M7 e E1M3 (R119 both):** o mínimo vem de **picos de um quadro só**.

  | Mapa | Tic do pico | VBlanks do quadro | Mediana |
  |---|---|---|---|
  | E1M7 | 296 | 59–60 | 20 |
  | E1M7 | 424 | 57 | 20 |
  | E1M7 | 333 | 49 | 20 |
  | E1M7 | 185 | 50 | 20 |
  | E1M3 | 305 | 51 | 19 |
  | E1M3 | 416 | 49 | 19 |

  - Dentro de todos os picos, cerca de metade das amostras é **`L_MOVE_COLLIDE` de tiro instantâneo**: `P_PathTraverse`, `PIT_AddThingIntercepts`, `PIT_AddLineIntercepts`, `P_PointOnDivlineSide`, `P_BlockLinesIterator`, `R23_MapRead` e `make` (montagem dos proxies dos things da ROM, R24).
  - Ou seja, os picos são **disparos**: espingarda (até 3 traços de mira + 7 de bala, de 2.048 unidades) e metralhadora, do jogador e de zumbis/sargentos, somados ao render normal.
- **Lógica do E1M7:**

  | Função | % |
  |---|---|
  | `P_CheckSight` | 23,3 |
  | `P_CheckPosition` | 14,5 |
  | `P_SetThingPosition` | 12,5 |
  | `P_MobjThinker` | 8,9 |
  | `R_PointInSubsector` | 6,6 |

  - A instrução logo depois de cada janela de SRAM (`move.w d0,sr`) junta ~9% das amostras de lógica. São VBlanks que chegaram com a interrupção mascarada, o que mede o tempo passado dentro das janelas.
  - `P_MobjThinker` acumula 104 amostras logo no prólogo, que salva 11 registradores para todos os mobjs, inclusive cadáveres parados.
- **Render:** `R23_MapRead`/`R23_MapWrite` chamados a partir de `R_Subsector` somam ~1,9% de todas as amostras. São as flags de linha na SRAM.

## 2. Candidatas R123 (exatas, sem RAM nova), contra a R122 layout
| Variante | Mudança | Por que é exata | Alvo |
|---|---|---|---|
| `flags` | Em `R_AddLine`, quando a linha precisa ter as flags recalculadas: o `r_flags` já veio na leitura de 4 bytes do `r_validcount` e é reaproveitado (em vez de 1 `R23_GET` por regra), e `R_RecalcLineFlags` devolve o byte que acabou de gravar (em vez de lê-lo de volta da SRAM). | Mesmos bytes gravados, mesmas flags usadas. Com a R81, `r_flags` é um byte, igual ao que a leitura de 4 bytes já devolvia. | 2 janelas de SRAM a menos por linha visível por quadro (render) |
| `idle` | `P_MobjThinker` sai imediatamente quando o mobj não tem momento, está no chão, tem `tics == -1` e não é candidato a renascer no Nightmare. O corpo original virou `P_MobjThinkerFull` (noinline) e roda nos demais casos. | Nesses casos o original não faz nada: copiei exatamente os testes dele. | cadáveres e decorações paradas (prólogo de 11 registradores) |
| `shoot` | Em `PIT_AddThingIntercepts`, um thing sem `MF_SHOOTABLE` continua ocupando a vaga dele (mesmos testes de lado, mesmo teste de sinal de "atrás da origem", mesmo limite de 64 interceptações), mas com `frac = FRACUNIT+1` em vez da divisão longa `FixedDiv`. | `PTR_AimTraverse` e `PTR_ShootTraverse` (os dois únicos que adicionam things) ignoram esses things ("corpse or something", `return true`, sem efeito). Uma entrada > FRACUNIT nunca é visitada antes de uma interceptação válida. O estouro em 64 continua idêntico. | picos de tiro com cadáveres/itens na linha de fogo |
| `all` | as três | — | — |

O que não fiz, por não ser exato ou por adicionar RAM:
- **Cortar o traço depois do primeiro acerto:** muda o caso de estouro de 64 interceptações, em que o original cancela o tiro.
- **Ordenar as interceptações:** fica mais lento quando a bala para no primeiro obstáculo, que é o caso comum.
- **Validcount em RAM:** custa RAM.
- **Janelas de SRAM longas:** o Z80 e o 68000 poderiam ler a ROM acima de 2 MB durante a janela, a mesma lição da R122.

## 3. O workflow `r123-claudio-spikes.yml`
Os mesmos portões da R122, com 5 builds (control = R122 layout; `flags`, `idle`, `shoot`, `all`):
- ROM ≤ 4 MiB, BSS ≤ 57.920, `.data`/`.bss` iguais aos do controle;
- **música abaixo de 2 MB em todas as ROMs** (`r122_z80_layout.py --require`);
- BlastEm fixo no divisor 7;
- lógica 10/10 idêntica (as 5 variantes);
- pixels Off (5 variantes) e On A2/L3 (control × all);
- A/B estrito nas demos 3/7/9/10, render a partir do tic 150. No E1M7 isso cobre o pico do tic 296. Os `PROFILE.json` trazem `spike_frames` por variante para comparar os picos;
- smoke do PLAY (all);
- ROMs só em `/home/dan/Projetos/Personal/r123-claudio-spikes/run-…/`.

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r121-e1m7-20261103
date -u > .github/triggers/r123-claudio-spikes.trigger
git add .github/triggers/r123-claudio-spikes.trigger; and git commit -m "R123: trigger"; and git push
```

**O que me trazer:**
- as notas R123 (Z80 layout, logic dK, DEMO3 A/B, Shadow On, heavy-demo A/B);
- o artefato de relatórios;
- se possível, os `spike_frames` do E1M7 por variante (estão nos `PROFILE.json` de `time-c-*/d7-ab`).

## 4. Expectativa honesta
- **Ganhos estimados:**
  - `flags`: ~1–3% no render;
  - `idle`: ~1–2% da lógica nos mapas com muitos cadáveres;
  - `shoot`: corta parte dos picos de tiro, só quando há things não-atiráveis cruzando a linha de fogo.
- **Juntas:** algo como 2–4% de média e talvez 5–15% nos picos.
- Os picos são feitos de muitos traços de tiro (cada um com até 64 blocos do blockmap, janelas de SRAM e proxies R24). Não existe alteração exata que os elimine.
- Se a `all` não mostrar ganho material no A/B estrito e no Run All do usuário, recomendo **parar a otimização do E1 e fixar a R122 layout** (com o som corrigido) como base final.
