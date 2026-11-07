# Atualização Z7 / Z6 hardware — 07/11/2026

**Z6 hardware PASS**, confirmado por foto: 2600 TICS PASS, hash 182C31E7 igual ao BlastEm, requests 11, bytes 63309, erros 0. **Z7 comparação independente concluída, workflow SUCCESS**: run 42426895978 / commit 1c2dd15. 27 checkpoints MD G_Ticker e sub P_Ticker. Tic 0 coincide; primeiro checkpoint divergente 100 (objetos/RNG), trajetória diverge no 200. MD morre no tic 541, respawna uma vez e termina com saúde 100; sub tem primeiro checkpoint morto no 2300 e termina com saúde 0. Divergência real, causa exata ainda não isolada; não exigir identidade bit a bit (critério do usuário). Próximo marco: P_Init / switches e G_Ticker completo no sub, inclusive rebirth/reload. Renderização ainda não usa estado sub.

**Ler primeiro [SCD-Z7-MD-SUB-COMPARISON.md](./SCD-Z7-MD-SUB-COMPARISON.md)**. O estado abaixo é histórico e suas menções a Z6 não testada/ausência de comparação estão superadas.

# Atualização Z6 — 07/11/2026

Z5 aprovada pelo usuário no console nesta conversa. **Z6: 2600 chamadas reais de P_Ticker no sub-68000, build/link estrito e BlastEm PASS**, run 42417494369, commit 04a66b6. 27 checkpoints devolvidos da PRG-RAM e hash 182C31E7 conferido; 11 requests, 63309 bytes, 0 erros/timeouts. Heap da variante ticker 224 KiB; payload 81988 bytes, RAM end 0x736D0. **Saúde final 0: comparação MD/sub pendente.** Não é G_Ticker completo nem renderização a partir do sub. Z6 hardware ainda não testado. ROM `/home/dan/Projetos/Personal/scd-subport-s1e-z6/run-42417494369-1/doom-md-scd-s1e-z6.bin`. START ainda executa R128 no MD.

Ler primeiro [SCD-Z6-REAL-SIMULATION.md](./SCD-Z6-REAL-SIMULATION.md), com prova, limites e próximos passos. As afirmações abaixo de que não houve ticker no sub são históricas: P_Ticker agora foi executado, G_Ticker completo ainda não.

# Handoff geral — DOOM-MD R128 → Sega CD sub-68000 (07/11/2026)

> ## Atualização que substitui o estado antigo da Z5 — 07/11/2026
>
> **Z4 aprovada em console real**, reafirmado pelo usuário nesta retomada.
>
> **Z5 AGORA É ROM REAL, COM BUILD/LINK E BLASTEM PASS**, não apenas diagnóstico. [Run 42414041898](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42414041898), commit `226ff84a1b4b6ce236b61d3c39491ce2e57aa7e3`.
> - `P_SetupLevel(1)` real percorre a inicialização inteira, inclusive `P_LoadThings2`, `P_SpawnSpecials` e `P_MapEnd`, **sem retorno antecipado pós-P_GroupLines**.
> - No sub: jogador iniciado via `PST_REBORN`; teste exige jogador com saúde 100, subsector válido, monstros presentes (`_g_totalkills>0`), geometria e heap íntegros.
> - Matemática/BSP extraídos **literalmente** de `r_draw.c` gerado: `FixedMul`, `FixedMulAngle`, `FixedMul3232`, `FixedMul3216`, `FixedApproxDiv`, `R10_ReciprocalSmall`, `R_PointOnSide`, `R_PointInSubsector`, `SlopeDiv`, `R_PointToAngle3`; tabela `tantoangleTable` exata e `r47_mul.h`. Automapa e estado sky usam fontes originais, com GC de seções.
> - Fronteiras de hardware: chamadas S_StartSound/S_StartSound2/S_StopSound são silenciosas apenas no sub; pré-carga de texturas P_LoadTexture/R_GetTexture e hooks de framebuffer MD R115_LevelEnd/Start não executam vídeo no sub. **Não há stubs de spawn/gameplay**.
> - Bug no probe antigo corrigido: não linkar `logic-slice.o` juntamente com os objetos individuais.
> - Link estrito: **39 objetos, PASS**; payload sub **83.224 bytes**, RAM end **0x57B88**, dentro de 512 KiB e do loader de 128 KiB.
> - BlastEm: stage=5, served=10, errors=0, timeouts=0, bytes=52895, marcador sub **0x5A6D**, CRC MD=CD **0x5547100C**; MD fallback G_Ticker PASS. O workflow agora reprova se Z5 build/runtime falharem; não usa mais falso verde do probe.
> - **ROM privada para console:** `/home/dan/Projetos/Personal/scd-subport-s1d-z5/run-42414041898-1/doom-md-scd-s1d-z5.bin`. Tela `S1D Z5 FULL P_SETUP`, `SETUP PASS`, `TRANSFER PASS`; START/timeout → R128 no MD.
> - **Z5 hardware: AINDA NÃO TESTADO. G_Ticker no sub: AINDA NÃO EXECUTADO.** O jogo do fallback segue no MD. Próxima etapa é demo/ticker real no sub e 2600 tics/fingerprints independentes (S1e), mantendo WAD/input/relatório no MD.
>
> **O restante deste documento é histórico anterior e suas menções a Z5 apenas diagnóstica foram superadas por esta atualização.**


**Ler primeiro:** [`SCD-S1C-S1E-INTEGRATION-PLAN.md`](./SCD-S1C-S1E-INTEGRATION-PLAN.md), [`SCD-SUBPORT-S1S2-CLAUDIO.md`](./SCD-SUBPORT-S1S2-CLAUDIO.md) e [`SCD-S1B-VALIDATED-TRANSPORT.md`](./SCD-S1B-VALIDATED-TRANSPORT.md).

**Repo:** `bollux78/MD-DOOM64KB`. **Branch de trabalho:** `exp-werk-scd-subport-s1s2`. **HEAD imediatamente anterior a este handoff:** `ca923368846190aaf33d5be02903447e9dd1db35`. Usar branch experimental, nunca sobrescrever versões aprovadas ou editar `/home/dan/Projetos/doom-md`.

## Alvo e critérios inegociáveis

1. Primeiro executar **`P_SetupLevel` completo, `G_Ticker` e demo de 2.600 tics no 68000 do Sega CD**; depois render S2. Até aqui, `G_Ticker` do fallback está no **Mega Drive**, não no sub. Não declarar motor migrado prematuramente.
2. Toda ROM apresentada ao usuário precisa mostrar diagnóstico + **START/timeout (~15 s) → R128 jogável no MD**, independentemente de a etapa do sub passar ou falhar.
3. Usuário prefere **duas variantes/etapas sequenciais no mesmo workflow**, com ROMs e relatórios separados; um diagnóstico não deve bloquear à toa outra investigação. Não mascarar falha: cada etapa tem seu veredito.
4. **Build, BlastEm, console físico e execução da lógica no sub são provas diferentes.** O usuário aceita pequenas divergências da demo se o gameplay funcionar, mas exige registro e análise.
5. ROM/IWAD/ELF privados ficam sob `~/Projetos/Personal` no runner self-hosted; não colocar binários no GitHub. `S1a`, `Z1` aprovada e o R128 original devem ser preservados. Só editar árvore de compilação descartável em `$RUNNER_TEMP`.

## Status verificado

| Marco | Resultado real |
|---|---|
| S0/S1c | Compilação dos objetos e diagnósticos de link; não são ROMs com gameplay no sub. |
| S1b | [run 42376206144](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42376206144) PASS: DIR + 3 lumps, 4 transações, 26.331 B, CRC MD/CD `998D122A`, START → gameplay no MD. |
| S1d RAM | 28 módulos e RAM direta sem MD SRAM/R23, link diagnóstico; [42388960828](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42388960828) e [42389565745](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42389565745) PASS; ainda havia ~70 externos no probe. |
| Z0 | [42394549410](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42394549410) PASS: `Z_Init`, alocação/free/heap e WAD no sub. |
| **Z1** | [42395731404](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42395731404) PASS, **usuário aprovou em console físico**; 9 lumps + DIR, 52.895 B, CRC `5547100C`. |
| **Z2/Z3** | [42401064058](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42401064058) PASS ambos no BlastEm. Z2 preserva nove lumps em cache; Z3 constrói runtime geometry PRG-RAM. Usuário testou no console e relatou Doom carregando; HUD dizia `TRANSFER FAIL` com `MAP PASS`, zero erros, CRC igual — **bug de texto, não de transporte**. |
| **Z4** | **[42404785842](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42404785842) SUCCESS: link estrito + BlastEm PASS**. Pela primeira vez o **`P_SetupLevel(1)` real** roda no sub até `P_GroupLines`, sem spawn/especiais. Marcador `0x5A5D`, 10 transações/52.895 B, 0 erros/timeout, CRC MD/CD `5547100C`, START → R128 no MD PASS. **Z4 APROVADA NO CONSOLE FÍSICO pelo usuário em 07/11/2026**. |
| **Z5** | Executou diagnóstico de **link estrito da inicialização inteira** no mesmo run; `S1d Z5 strict link: FAIL objects 36`. A etapa diagnóstica saiu com status 0 intencional; **não existe ROM Z5 validada**. |
| S1e/S2 | `G_Ticker` real no sub e render offload **ainda não implementados/validados**. |

**Última ROM Z4 privada do runner:**
`/home/dan/Projetos/Personal/scd-subport-s1d-z4/run-42404785842-1/doom-md-scd-s1d-z4.bin`.
Sub payload = **8.240 bytes**; fim da RAM `0x451D8`. Marcador Z4 `0x5A5D`; fallback do MD passou no BlastEm. Hardware PASS informado pelo usuário em 07/11/2026 (tela Z4 e fallback aprovados).

**Relatório Z5:** `/home/dan/Projetos/Personal/scd-subport-s1d-z5-link/run-42404785842-1/link_report.json`. Símbolos faltantes verificados incluem `FixedMul`, `FixedMulAngle`, `R_PointToAngle3`, `R_PointInSubsector`, `S_StartSound`, `S_StopSound`; há mais no relatório completo.

## Dois bugs históricos: não repetir

1. **Falso `TRANSFER FAIL`** em Z1/Z2/Z3: ao trocar `const bool pass=r.stage==5` por predicado de 10 transações, o script preservava o velho `r.serviced==4` da S1b. Resultado era `10 && 4`, impossível. Comprometia só o texto na tela, com CRC/dados corretos. **Corrigido em `5673b57`** nas rotinas `s1d/build_zone.py` e `s1d/build_setup.py`. ROMs antigas continuam mostrando FAIL, não é razão para mexer no transporte.
2. **Link Z4 não achava `R115_LevelEnd`**, rotina de duplo framebuffer exclusiva do **MD**. Runs [42402235521](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42402235521)/[42402895451](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42402895451) falharam. **Corrigido em `f7289af`**: remover APENAS esse hook da cópia gerada de `p_setup.c` para o sub sem render, preservando `Z_FreeTags`. Z4 passou em [42404785842](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42404785842).

## Arquivos centrais

- `.github/workflows/scd-subport-s1b.yml`: atual workflow, Z4 link/ROM/teste e Z5 link probe em sequência; mantém prova S1b e análise RAM.
- `experiments/DOOM_SCD_SubPort/s1d/build_setup.py`: link **estrito** da Z4, faz patch experimental da árvore R128 e gera ROM Mode 1; com `--full` executa diagnóstico Z5 e salva `link_report.json` sem ROM Z5.
- `s1d/setup_sub_main.c` e `s1d/setup_bsp_state.c`: entrada real e globais BSP da Z4; `s1d/test_setup.py`: teste BlastEm e fallback.
- `s1d/resident_sub_main.c`, `s1d/build_zone.py`, `s1d/test_live.py`: Z2/Z3; cache residente/alloc real de geometria.
- `s1d/scd_sub_system.c`: zone 112 KiB / runtime no sub; `s1d/logic_slice.py`: compilação de subconjunto e link diagnóstico.
- `experiments/DOOM_SCD_SubPort/scd_proto.h`, `scd_sub_transport.c`, `scd_md_server.c`, `scd_sub_w_wad.c`, `s1b/s1b_md.c`: comunicação real. PRG-RAM do sub = 512 KiB; cache WAD 128 KiB; swap 1M Word RAM comandado pelo MD, não iniciar DMNA no sub.
- `src/p_setup.c`, `src/p_tick.c`, `src/p_mobj.c`, `src/p_spec.c`, `src/p_map.c`, `src/g_game.c`: lógica real da R128 **gerada**. É crítico conferir código após `scripts/lab/apply_r*.py`, não só o `src/` no GitHub.
- `s1e/compare_logic.py`: comparador de traces **independentes** a cada 100 tics, ainda sem prova de execução dos 2.600 tics no sub.

## Ação concreta para o próximo agente

1. Confirmar branch/HEAD. Z4 foi aprovada no console pelo usuário em 07/11/2026; continuar para Z5 e integração completa. Ler o relatório Z5 completo e **catalogar dependências alcançáveis** — não deduzir somente pelos trechos visíveis no log.
2. Portar matemática/BSP do jogo e inicialização de monstros/especiais reais (`P_LoadThings2`, `P_SpawnSpecials`, `P_MapEnd`); **não** usar stubs artificiais de lógica que fariam falso PASS. Áudio/vídeo podem ser hooks sem execução de hardware no sub, com arquitetura explícita.
3. Preparar duas etapas sequenciais: uma ROM de runtime realmente ampliada para testar no BlastEm e console, e um probe/ROM mais avançado, mantendo o fallback via START e isolando resultados.
4. Depois de `P_SetupLevel` completo, executar demo E1M1 com `G_Ticker` **no segundo 68000**, 2.600 tics sem render, medir fingerprints reais e independentes, contagem de mobjs e memória. Só então S2.
5. Comunicar resultados distintos de compilação, BlastEm, console, fase geométrica e gameplay real. Nunca confundir `G_Ticker` observado no MD com ticker no Sega CD.

**Atalhos de referência:** [histórico detalhado](./SCD-S1C-S1E-INTEGRATION-PLAN.md) · [arquitetura S1/S2](./SCD-SUBPORT-S1S2-CLAUDIO.md) · [S1b transporte](./SCD-S1B-VALIDATED-TRANSPORT.md).

**Segurança:** dados WAD/ROM/ELF e outras informações privadas não são commitados; não tocar no checkout principal. Este documento é somente código/links/relatório de trabalho.
