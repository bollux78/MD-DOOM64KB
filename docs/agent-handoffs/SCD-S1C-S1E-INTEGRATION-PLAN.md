# S1c–S1e — plano de integração do engine no sub-68000 (2026-11-07)

## Base comprovada
Branch `exp-werk-scd-subport-s1s2`. S1b: build PASS / BlastEm PASS (run 42376206144); DIR + três lumps, 26331 bytes, CRC MD/sub 0x998D122A, errors/timeouts 0. START/timeout continua executando o R128 no **MD**. Não há prova de `G_Ticker` no sub. Ver `SCD-S1B-VALIDATED-TRANSPORT.md`.

## Etapas de implementação
1. **S1c (link):** Inventariar objetos S0 do motor, símbolos necessários, acessos MD-only, orçamento PRG-RAM, BSS, stack e heap. Fazer link real dos objetos no sub, sem presumir que cabem na janela de 128 KiB. Documentar símbolos faltantes e tamanhos. Trabalhar só em cópias descartáveis; nunca modificar/limpar `/home/dan/Projetos/doom-md`.
2. **S1d (boot):** Adicionar `scd_sub_system.c`, entrada de engine e callbacks de WAD/cache. Executar inicialização exigida pelo motor, incluindo `Z_Init` e `P_SetupLevel` para E1M1, com servidor MD atendendo DIR/LUMP simultaneamente. Auditar trocas de banco 1M Word RAM, deadlock e timeout; sem VDP direto no sub.
3. **S1e (ticker):** Rodar `G_Ticker` e demo E1M1 **sem renderização** no 68000 do Sega CD. Comprovar processador por breakpoint/trace. Medir 2600 tics e comparar fingerprints com a R128 sob mesmos inputs, RNG e estado inicial; registrar primeiro tic divergente, contadores de cache, requests e latência.
4. **ROM S1 de diagnóstico:** Tela legível com status e contadores, START → jogo R128 All no Mega Drive e fallback por timeout/falha. Testar boot, START e sem Sega CD no BlastEm. Separar explicitamente `build PASS/FAIL`, `blastem PASS/FAIL` e `hardware NOT TESTED/PASS/FAIL`.
5. **Limites:** Preservar S1a aprovada e jogo R128. Não avançar para S2 antes da prova real do ticker no sub. Nunca publicar WAD, ROM privada, ELF ou mídia protegida; manter em `Personal`.

## Atualização verificada em 07/11/2026 — antes da validação Z0

- **S1c:** [run 42377127507](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42377127507) PASS — símbolos `Z_Init`, `P_SetupLevel`, `G_Ticker` encontrados, mas executável de diagnóstico ainda com recursos gráficos e sem funções de plataforma.
- **S1d slice original:** [run 42378872339](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42378872339) PASS — 28/28 arquivos e link, porém com definições R23/SRAM.
- **S1d RAM direto:** [run 42388960828](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42388960828) PASS — 28/28, sem R23_MAPMEM/R22_SRAM_BLOCKLINKS, nenhum símbolo de acesso MD/SRAM proibido, 77 referências externas na compilação parcial.
- **S1d RAM com módulos reais:** [run 42389565745](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42389565745) PASS — 28 componentes de lógica + sistema, WAD/cache e transporte = 31 objetos, link relocável/diagnóstico, 70 referências externas; `_end=349948` (341,7 KiB), **provisório** pois símbolos faltantes foram ignorados no link. Não declarar executável funcional a partir deste dado.
- **S1d-Z0 (histórico anterior à validação):** códigos `s1d/zone_sub_main.c`, `scd_sub_system.c`, `build_zone.py`, `test_zone.py` e etapa no workflow `scd-subport-s1b.yml` adicionados. Objetivo: provar no BlastEm **Z_Init real + Z_MallocStatic/Z_Free/Z_CheckHeap no sub**, somado ao transporte WAD e ao fallback START no MD. Verificar relatório de CI posterior ao commit `2ee3f12`; **não há PASS comprovado de Z0 nesta atualização**. ROM Z0 não é `P_SetupLevel` nem `G_Ticker` no sub.
- O marcador `0x5A1D` é escrito no registrador de argumento do sub (`FF8024`) só após o teste de zona e CRC. O MD captura em `A12024` **apenas se stage==5** (evita acessar periférico inexistente no MD sem Sega CD). `test_zone.py` exige marcador + CRC igual + `G_Ticker` **no MD**, não no sub.
- Todos os artefatos binários, WAD e ELF permanecem em `~/Projetos/Personal` no runner. `/home/dan/Projetos/doom-md` não é modificado.

### S1d-Z0 — primeiro build e execução comprovados

**Run [42394549410](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42394549410): build PASS / BlastEm PASS / hardware NOT TESTED.**
Correção do erro original: `zone_sub_main.c` precisava incluir `i_system.h`, commit `9aa67e2`.
- ROM privada: `/home/dan/Projetos/Personal/scd-subport-s1d-z0/run-42394549410-1/doom-md-scd-s1d-z0.bin`.
- Sub image 8194 bytes; BSS end `0x45058`, abaixo de `0x7E000`.
- Registros observados via BlastEm/MD: `stage=5`, `served=4`, `bytes=26331`, `errors=0`, `timeouts=0`; `mdcrc=subcrc=0x998D122A`.
- Marcador `0x5A1D`: sub 68000 passou por `Z_Init`, alocação e preenchimento/checagem de 256 bytes, `Z_Free`, `Z_CheckHeap`, e WAD I/O. O teste confirma o marcador lido pelo MD.
- `G_Ticker` depois de START/timeout foi alcançado **no Mega Drive**, não no sub.
- Esta é a **Z0 de diagnóstico**, ainda não S1d com `P_SetupLevel` nem S1e de 2600 tics. Sem teste de console até confirmação do usuário.

### Próximo passo após o PASS do Z0
1. Link estrito do núcleo sem `--unresolved-symbols=ignore-all`, resolvendo por etapas os 70 símbolos remanescentes e adicionando apenas módulos realmente necessários à demo E1M1.
2. Portar inicialização do mapa `P_SetupLevel` e runtime de demo ao segundo CPU, com rastreamento dos checkpoints e da memória; manter a ROM diagnóstica com START → R128 no MD.
3. Somente depois rodar `G_Ticker` no sub para 2600 tics e usar o comparador `s1e/compare_logic.py`; divergências são reportadas, não reprovação automática, conforme critério do usuário.

## Critério de pronto
S1 só está completo com `G_Ticker` demonstravelmente executando no sub-68000, dados reais via servidor MD, 2600 tics instrumentados, fingerprints avaliados e fallback START jogável. Sucesso de compilação não equivale a jogabilidade/paridade.
