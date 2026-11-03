# R116 demotest: testes de demo por mapa (Cláudio para o Werk)

**Status:** código pronto na branch `exp-claudio-r116-demotest-20261102`, **ainda não compilado nem executado**. O primeiro run (41559960872) foi cancelado a pedido do usuário: a execução e a depuração ficam com o Werk.

## 1. Objetivo
Um teste real de compatibilidade de demo por mapa (E1M1–E1M9), com combate, para:
- **Sincronia:** provar que a lógica do motor continua idêntica à do Doom 1.9. Isso inclui as otimizações (R88 ai, R22/R23 SRAM, blockmap etc.).
- **Memória:** medir a folga mínima da zone em cada mapa em combate real.
- **FPS no console:** dar ao usuário FPS por mapa (Benchmark › Demo tests).

**Descoberta importante:** o DEMO3 do benchmark **nunca foi teste de sincronia**. O cabeçalho dele diz mapa 7 e o build força o E1M1 (veja `audit_r26.py`: `header_map=7, effective_map=1`). Então este é o primeiro teste de compatibilidade de demo do motor e **pode falhar**. Se falhar, o resultado é um achado a investigar, não um erro do teste.

## 2. Demos
- Origem: DSDA (dsdarchive.com), categoria UV-Max.
- Sorteio aleatório com semente 20261102. Filtros: engine DooM v1.9 / cl2 / cl3 / Chocolate; 1 jogador; sem TAS; até 3:00 (E1M6 até 4:00).
- O cabeçalho de cada demo foi validado: v109, skill 3, E1, mapa certo, sem respawn/fast/nomonsters.
- Ficam **privadas** no runner, em `/home/dan/Projetos/Personal/demos/` (o usuário já descompactou lá). Cada arquivo é conferido pelo sha256 de `assets/r116-demos.json`.
- Os `*_altN.lmp` são reservas: duas por mapa.
- Nada de demo, ROM ou ELF vai para o git ou para os artifacts, porque são demos de terceiros e o repositório é público.

| Índice | Lump | Demo | Tempo-alvo (leveltime) |
|---|---|---|---|
| 1 | DTE1M1 | Robin Woehler 0:54.71 | 1915 |
| 2 | DTE1M2 | Kinetic 1:27.74 | 3071 |
| 3 | DTE1M3 | Vile 2:24.66 | 5063 |
| 4 | DTE1M4 | Anders Johnsen 1:53.03 | 3956 |
| 5 | DTE1M5 | Bainshie-Doom 2:17.94 | 4828 |
| 6 | DTE1M6 | Jonathan Rimmer 3:22.83, **sem o limite da R115** (nocap) | 7099 |
| 7 | DTE1M7 | Ocelot 2:42.77 | 5697 |
| 8 | DTE1M8 | Coincident 1:08.20 | 2387 |
| 9 | DTE1M9 | kuckkuck 2:03.77 | 4332 |
| 10 | DTE1M6S | **Especial** gerada, ver abaixo | sem gabarito |

**Especial E1M6 (DTE1M6S):**
- Gerada em `r116_add_demos.py:special_demo()` com um LCG determinístico.
- Cabeçalho UV, então o limite da R115 entra e o mapa nasce com os monstros do HMP. Entre UV e HMP só o spawn muda, conferido em `p_inter.c`, `p_mobj.c` e `p_enemy2.c`.
- 4.200 tics: anda, atira, aperta use a cada 10 tics e troca para shotgun/chaingun. Quando o jogador morre, o use recarrega o nível.
- Não existe demo HMP do E1M6 no DSDA (verificado).
- Passa se não houver I_Error. Os números do primeiro run viram referência para regressão.

## 3. Arquivos
- `scripts/lab/r116_add_demos.py`:
  - acrescenta os 10 lumps ao fim do diretório do WAD convertido; os números dos lumps existentes não mudam;
  - gera `src/r116_demos.h`, com a tabela das demos e o `r116_res_t`.
- `scripts/lab/apply_r116.py`: aplicado **depois de `apply_r115.py`**. Muda:

  | Arquivo | Mudança |
  |---|---|
  | `g_game.c` | `r116_sel` (1..10) troca o DEMO3 em `G_DoPlayDemo` |
  | `g_game.c` | o mapa do cabeçalho é usado como gravado |
  | `g_game.c` | IA forçada em Normal durante o teste e restaurada depois |
  | `g_game.c` | no primeiro `G_DoCompleted` grava `r116_res` (exit leveltime, kills, items, secrets, totais, mapa, secretexit) e chama `R116_Done()`; a demo para no tic seguinte |
  | `g_game.c` | `R116_End()` em `G_CheckDemoStatus` |
  | `g_game.c` | zone mínima (total e maior bloco) a cada 4 tics em GS_LEVEL |
  | `g_game.c` | conta mortes (`G_DoReborn`) |
  | `p_setup.c` | `r116_nocap` desliga o limite UV→HMP do E1M6 |
  | `d_main.c` | `r116_norender` pula o `D_Display` inteiro (só para a sonda) |
  | `d_main.c` | `D_R116_SelectDemo` |
  | `m_text.c` | Benchmark ganha "Demo tests" (submenu com 10 itens) |
  | `r22_benchmark.inc` | tela de resultado mostra o título da demo e as linhas 19–25: EXIT TIC x/alvo, KILLS, SECRETS, ZONE MIN, DEATHS, **SYNC: OK/FAIL** |
  | `build_r35_linear.fish` | chama o `r116_add_demos.py` depois do `r89_align_maps.py` (exige `R116_DEMO_DIR`) |
  | builder | prefixo `r116-`, conjunto `demotest` |

  Todo o estado novo fica em `.data`, então o BSS não deve mudar (R115 = 57.884, limite 57.920).
- `scripts/lab/r116_demo_probe.py`:
  - roda uma vez no BlastEm por demo (≤ 9.800 quadros);
  - no primeiro `G_Ticker` escreve `r116_sel=k` e `r116_norender=1`;
  - para em `R116_Done`, `R116_End`, `I_Error` ou no limite de quadros;
  - critério UV-Max: `|exit-alvo| ≤ 1`, kills e secrets em 100% e o mapa de saída certo.
- `.github/workflows/r116-claudio-demotest.yml`:
  - build pl e pf;
  - **copia ROMs e ELFs para `/home/dan/Projetos/Personal/r116-demotest/run-<id>-<attempt>/`**;
  - sonda as 10 demos e faz um smoke do PLAY;
  - envia só os relatórios (`r116-probe.json`, logs, MANIFEST, BUILD.log).
- `assets/r116-demos.json`: só metadados (sha256, jogador, tempo, URL).

## 4. Como rodar
```fish
cd MD-DOOM64KB; git fetch origin; git checkout exp-claudio-r116-demotest-20261102
date -u > .github/triggers/r116-claudio-demotest.trigger
git add .github/triggers/r116-claudio-demotest.trigger; and git commit -m "R116: trigger"; and git push
```
O resultado sai nas notas do step "Demo sync probe", uma linha por demo: PASS/FAIL, `end`, exit/alvo, kills, secrets, zone e mortes.

## 5. O que pode dar errado (nada disso foi testado)
- **Compilação:** o C novo só passou por uma checagem de sintaxe no host para `g_game.c` e `d_main.c`. `m_text.c` e `r22_benchmark.inc` não foram checados, porque faltam headers gerados no host. Pontos prováveis de erro:
  - `secretexit` (nome ou visibilidade em `G_DoCompleted`);
  - `memset` / `<string.h>` em `g_game.c`;
  - `__attribute__((section(".data")))` com inicializador zero (se o linker reclamar de conflito de seção, use inicializador não zero ou tire o atributo e confira o BSS);
  - `bench_u32` precisa estar definida antes do bloco R116 em `r22_benchmark.inc` (o bloco é inserido logo antes de `I_BenchmarkShowResults`).
- **Repack:** os lumps novos vão no fim do arquivo, com um diretório novo, e o `repack_wad.py` reorganiza tudo depois. Se algum passo seguinte validar o número de lumps, ajuste esse passo.
- **Limite de quadros:** com `r116_norender` cada tic deveria custar menos de um quadro. Se der `end=frame_limit`, o campo `last` mostra até onde chegou. Para o E1M6 (7.303 tics), troque pela reserva mais curta ou estude o custo por tic.
- **Dessincronia** (`demo_end_no_exit`, ou exit diferente do alvo):
  1. Confirmar com uma reserva (`*_altN.lmp`: troque o `primary` em `assets/r116-demos.json`; o sha256 já está lá).
  2. Se as reservas também falharem, é o motor. Bisseccione pela cadeia de apply: rode o mesmo teste sem `apply_r88` ai, sem R22/R23 etc. Primeiras suspeitas: R88 ai (ordem do `P_Random`/IA), a ordem da lista de things no blockmap em SRAM (R22) e as mudanças do conversor de mapas (R24).
  3. Para achar o tic exato da divergência seria preciso um traço de referência (por exemplo, Chocolate Doom com `-statdump` ou um dump por tic). Hoje não temos um.
- **E1M8:** a saída é a morte do jogador no piso de saída (setor 11). O `G_DoCompleted` pega esse caso normalmente.

## 6. No console (para o usuário, depois do PASS no runner)
- Arquivo: `doom-md-r60-r116-demotest-pl.bin`, na pasta privada.
- Caminho: Benchmark › Demo tests › mapa.
- A tela final traz FPS e SYNC.
- Shadow e Off/On seguem a configuração atual.

## 7. Regras
- AGENTS.md: branch própria, sem merge, ROM ≤ 4 MiB, BSS ≤ 57.920, BlastEm ≤ 10.000 quadros por run.
- Demos, ROMs e ELFs da R116 **nunca** vão para artifact nem para o git.
- Todo acesso à SRAM continua passando por `R25_SRAM_BEGIN`/`END`.
