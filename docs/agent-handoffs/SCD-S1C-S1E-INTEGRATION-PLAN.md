# S1c–S1e — plano de integração do engine no sub-68000 (2026-11-07)

## Base comprovada
Branch `exp-werk-scd-subport-s1s2`. S1b: build PASS / BlastEm PASS (run 42376206144); DIR + três lumps, 26331 bytes, CRC MD/sub 0x998D122A, errors/timeouts 0. START/timeout continua executando o R128 no **MD**. Não há prova de `G_Ticker` no sub. Ver `SCD-S1B-VALIDATED-TRANSPORT.md`.

## Etapas de implementação
1. **S1c (link):** Inventariar objetos S0 do motor, símbolos necessários, acessos MD-only, orçamento PRG-RAM, BSS, stack e heap. Fazer link real dos objetos no sub, sem presumir que cabem na janela de 128 KiB. Documentar símbolos faltantes e tamanhos. Trabalhar só em cópias descartáveis; nunca modificar/limpar `/home/dan/Projetos/doom-md`.
2. **S1d (boot):** Adicionar `scd_sub_system.c`, entrada de engine e callbacks de WAD/cache. Executar inicialização exigida pelo motor, incluindo `Z_Init` e `P_SetupLevel` para E1M1, com servidor MD atendendo DIR/LUMP simultaneamente. Auditar trocas de banco 1M Word RAM, deadlock e timeout; sem VDP direto no sub.
3. **S1e (ticker):** Rodar `G_Ticker` e demo E1M1 **sem renderização** no 68000 do Sega CD. Comprovar processador por breakpoint/trace. Medir 2600 tics e comparar fingerprints com a R128 sob mesmos inputs, RNG e estado inicial; registrar primeiro tic divergente, contadores de cache, requests e latência.
4. **ROM S1 de diagnóstico:** Tela legível com status e contadores, START → jogo R128 All no Mega Drive e fallback por timeout/falha. Testar boot, START e sem Sega CD no BlastEm. Separar explicitamente `build PASS/FAIL`, `blastem PASS/FAIL` e `hardware NOT TESTED/PASS/FAIL`.
5. **Limites:** Preservar S1a aprovada e jogo R128. Não avançar para S2 antes da prova real do ticker no sub. Nunca publicar WAD, ROM privada, ELF ou mídia protegida; manter em `Personal`.

## Critério de pronto
S1 só está completo com `G_Ticker` demonstravelmente executando no sub-68000, dados reais via servidor MD, 2600 tics instrumentados, fingerprints avaliados e fallback START jogável. Sucesso de compilação não equivale a jogabilidade/paridade.
