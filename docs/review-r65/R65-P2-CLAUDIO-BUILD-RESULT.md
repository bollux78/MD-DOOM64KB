# R65-P2 Cláudio — resultado do build m68k e bloqueios objetivos

**25/10/2026. Candidato experimental, NÃO mesclar.** Branch `exp-r65-p2-claudio-wall-front`, base pinned R64A `b6e774676ed58fb950058d0f78108e2bbcf859a6`. R60 PairASM e R64A originais não foram alteradas.

## Proposta recebida

O `r65.zip` do Cláudio contém `README_R65.md`, `r65-wall-front.patch`, SHA256SUMS; SHA-256 do patch recebido: `7462a33eb606f631c21a4196daeb52df95b93cdcca25bdd08cb8ce0285147366`. Propõe cindir `R42_DrawPackedWall` em `R42_DrawPackedWall_Slow` (corpo original noinline) e uma frente curta com R64A LUT / `R60_WallDraw`; fallback para os demais casos. Hipótese de ~80–100 ciclos poupados por invocação ASM = ~1,1–1,3% FPS **não medida**. O próprio Cláudio exige verificar menos registradores no MOVEM; se isso não acontecer, descartar sem benchmark.

Aplicados os dois hunks de código da proposta em `src/r22_video.inc` e `scripts/lab/build_r35_linear.fish`; script de build adaptado para manter controle chamado `r64a-perf` exatamente como a ROM pinned (o `ref-perf` do patch mudaria a identidade / título da ROM). Não incluí o harness de host `test_r65_front.py` na branch. As 3,6 milhões de colunas e 5 mutações são resultados **declarados no README do Cláudio**, não retestados nesta execução. O antigo `test_r57_viewport.py` tem um extrator textual que não suporta a nova diretiva `#ifdef`; teste de menu R57 passou e a igualdade de pixels foi planejada para ROM real.

## Compilação real (sucesso)

[Run MarsDev 40228942556](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40228942556) / [artifact com ROMs PERF e PLAY, ELFs, ASM, BSS, flags e logs](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40228942556/artifacts/12611782970).

| Variante | BSS m68k | Teto conservador | Tamanho ROM |
|---|---:|---:|---:|
| R64A PERF (controle) | 57.900 B | 57.920 B | 2.883.584 B |
| R65-P2 PERF | 57.900 B | 57.920 B | 2.883.584 B |
| R65-P2 PLAY | 57.910 B | 57.920 B | 2.883.584 B |

A R64A PERF recompilada tem **SHA-256 = `07ef5fe652eed2780c34382dc8d9b764fccf80dda8297647c7a73f391ede02b5`**, igual à referência pinned. Todos os smoke runs BlastEm PERF a 800 e 10.000 frames por processo retornaram exit 0. Isso NÃO prova ausência de glitches visuais ou execução integral de DEMO3. Paletas e kernel ASM inalterados; flags PERF diferem apenas `DOOM_R65_WALL_FRONT`.

O PLAY P2 consumiu **+2 B de BSS em relação à R64A PLAY (57.908 B)**. Não foi declarada uma nova variável estática pela proposta; o `+2 B` pode resultar da realocação/alinhamento pelo compilador, mas **viola a exigência de BSS idêntico** e deixa apenas 10 B abaixo do limite conservador.

## O critério decisivo da proposta falhou: MOVEM não encolheu

Disassembly de `m68k-elf-objdump -d --no-show-raw-insn` da R64A e R65-P2 PERF reais (mesmo toolchain):

```asm
; R64A R42_DrawPackedWall — 8 registradores
0000f160 <R42_DrawPackedWall.lto_priv.0>:
    lea %sp@(-28),%sp
    moveml %d2-%d7/%a2/%fp,%sp@-

; R65-P2 front — TAMBÉM 8 registradores
0000f5a6 <R42_DrawPackedWall.lto_priv.0>:
    moveml %d2-%d7/%a2-%a3,%sp@-

; R65-P2 fallback preserva o prólogo original de 8 regs e locals
0000f1de <R42_DrawPackedWall_Slow.lto_priv.0>:
    lea %sp@(-28),%sp
    moveml %d2-%d7/%a2/%fp,%sp@-
```

A front R65 tem apenas 83 instruções estáticas, contra 286 no corpo original (os caminhos nunca executam todas as instruções); isso **não comprova redução de ciclos por chamada**. A frente não tem `lea sp(-28)`, mas ainda salva oito registradores e pode custar chamada extra de fallback. **O principal mecanismo estimado pelo Cláudio não aconteceu: critério de descarte atingido.**

## Tentativa de teste de igualdade de pixels com depurador BlastEm

[Run 40229401136](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40229401136). A R64A controle passou nos cinco pontos 8/16/64/128/256. A R65-P2 não chegou ao primeiro frame lido: BlastEm em modo RSP/GDB `-D` encerrou com mensagem de host JIT `jmp: ... out of range of a 32-bit displacement`, seguida de `BlastEm RSP EOF`. **Isso não é evidência de pixels diferentes nem prova conclusiva de bug na ROM:** é falha do emulador/depurador nessa execução; o smoke `-b` sem depurador concluiu normalmente. Os testes de 5 framebuffers e 3× A/B R65-P2 **não foram concluídos**.

## Recomendação

**Devolver ao Cláudio para revisão, não promover e não pedir teste de hardware agora.** O próprio gate do README determina descartar quando a front não economiza registros. Se quiser uma P2-revisada, o objetivo deve ser reduzir efetivamente o conjunto salvo no `moveml` — sem novo BSS — e preservar o hot path de forma compatível com R60 ASM. Depois repetir imagem e benchmarks, usando o mesmo clock original ~7,67 MHz.

Preservar referência R60 (6,72 FPS) e R64A (6,91 FPS no DEMO3 completo, 2.134 frames, H40 crop 16/16).
