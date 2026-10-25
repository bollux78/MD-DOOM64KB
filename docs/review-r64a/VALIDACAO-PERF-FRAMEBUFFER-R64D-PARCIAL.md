# R60 PairASM × R64A Cláudio — evidências do runner e diagnóstico R64D

**Estado:** R64A candidata; R60 permanece baseline. **Data:** 25/10/2026.

## 1. A/B de desempenho informado pelo teste manual no BlastEm

Mesmo clock original e DEMO3 NTSC 60 Hz, 2.134 frames, viewport 16/16: R60 referência 6,72 FPS / 317,37 s; R64A 6,91 FPS / 308,98 s. Diferença: +2,83% FPS arredondado, −8,39 s e +24 bytes de consumo de BSS/heap na prática. **Ainda é uma execução por ROM**; repetir pelo menos 3 vezes cada. Não comparar este FPS com o tempo de processo de `blastem -b`.

Compilação m68k: [run 40216335998](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40216335998); BSS: `ref-perf=57876`, `r64a-perf=57900`, `r64a-play=57908` bytes (teto conservador 57920).

## 2. Equivalência de framebuffer Pixel4: PASSOU (5/5)

Captura por GDB Remote Serial Protocol (RSP) via Python, sem alterar nenhuma ROM; breakpoint em `I_FinishUpdate` e leitura dos **3.344 bytes de `r22_fb.pixels`**, nas mesmas posições de `_g_gametic`. Cada execução BlastEm usa no máximo 10.000 frames emulados. Os hashes e as comparações binárias conferem.

| Tic | Bytes | Bytes diferentes | SHA-256 (idêntico nas duas ROMs) |
|---:|---:|---:|---|
| 8 | 3344 | 0 | `d367593c343d8c5c26ee39a5334c363180c9eb09d8103134e43ee6e78e236323` |
| 16 | 3344 | 0 | `a5b6d0d9b6424231409d96c9332afa8da1cc0e5d56f7e2f914d3209b74e5cf3b` |
| 64 | 3344 | 0 | `df9d5f4676bcd145f142020d7d409d849f7b817d345db546cdd1b5fc600faca7` |
| 128 | 3344 | 0 | `e83a3002d147e621935dd81c6a53285f7632443f0171baea3ccf5767e472600f` |
| 256 | 3344 | 0 | `20b4c78eb1d382e89fb57b7a096ca1933851088d9acf2ff945426140ca3a9ae4` |

**Limite do teste:** cinco posições fixas no DEMO3, configuração 16/16, modo de cor padrão. Não prova todas as condições de PLAY, menus, H32/H40 e troca dinâmica de cores. O usuário precisa testar crop 0/0, 16/16, 32/32 e alternância de perfis visualmente.

[ROMs controle e A](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40216335998/artifacts/12607847038)
[5 capturas / resultado byte a byte](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218061144/artifacts/12608425086)

## 3. Dados R64D EXTRAÍDOS da WRAM — PARCIAL, NÃO DEMO3 INTEIRO

O runner conseguiu depurar diretamente o BlastEm e capturar **65.536 bytes de WRAM** no tic 128 da ROM `doom-md-r60-diag-perf.bin`, construída do R60 PairASM com os contadores de Cláudio. O bloco de 236 bytes fica no heap do SGDK em endereço físico `0xFFF2FE` (ponteiro 68000 `0xE0FFF2FE`). Verificados magic R64D, versão 1 e **50 contadores**, decodificados com o `r64d_read.py` original do pacote.

[Abrir artefato com WRAM, bloco, leitor e relatório](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218307012/artifacts/12608377377)

| Contador | Acumulado até tic 128 |
|---|---:|
| `FRAMES` | 128 |
| `AL_CALLS` | 7508 |
| `AL_REAR` | 2743 |
| `AL_LEFT` | 1386 |
| `AL_RIGHT` | 0 |
| `AL_ZERO` | 176 |
| `AL_CLIPCALLS` | 3203 |
| `AL_V1_REUSE` | 1768 |
| `XP_REAR_OK` | 2743 |
| `XP_FALSE_REAR` | 1 |
| `XP_MISSED_REAR` | 0 |
| `XP_SKIP` | 0 |
| `SEG_R0` | 666 |
| `SEG_R1` | 2459 |
| `SEG_R2` | 78 |
| `SEG_R3` | 0 |
| `SEG_R4P` | 0 |
| `SR_CALLS` | 2615 |
| `SR_COLS` | 28763 |
| `SEG_COLS` | 28763 |
| `NODES` | 3971 |
| `NODES_FULL` | 0 |
| `SUBSECTORS` | 2291 |
| `SUBSECTORS_FULL` | 0 |
| `BB_CALLS` | 3971 |
| `BB_FULL` | 498 |
| `BB_FOV` | 872 |
| `BB_OCC` | 936 |
| `BB_ACCEPT` | 2163 |
| `WALL_CALLS` | 23473 |
| `WALL_DRAWN` | 23473 |
| `WALL_PIXELS` | 149971 |
| `WALL_ASM` | 18734 |
| `WALL_FB_CMAP` | 0 |
| `WALL_FB_SHORT` | 4739 |
| `FLAT_CALLS` | 25814 |
| `FLAT_DRAWN` | 25814 |
| `FLAT_PIXELS` | 137261 |
| `DF_FRAMES` | 127 |
| `TICS` | 128 |
| `TICS_H0` | 0 |
| `TICS_H1` | 128 |
| `TICS_H2` | 0 |
| `TICS_H3` | 0 |
| `TICS_H4` | 0 |
| `TICS_H5` | 0 |
| `TICS_H6` | 0 |
| `TICS_H7P` | 0 |
| `VB_LOGIC` | 136 |
| `VB_RENDER` | 2174 |

Principais razões (dados medidos, não ciclos): faces traseiras `2743/7508` = 36,53% das chamadas R_AddLine; reuso de vértice `1768/7508` = 23,55%; kernel ASM `18734/23473` = 79,81% das colunas de parede; fallback curto `4739`; falso positivo do pré-filtro vetorial `1=1`. Não usar o pré-filtro para culling incondicional sem uma verificação correta: há uma classificação errada observada. Histogramas e estimativas detalhadas estão no arquivo `COUNTERS-PARTIAL.txt`.

O leitor original estimou, **sob premissas teóricas de ciclos** e com apenas 128 quadros iniciais: A contexto ~5,1%; B1 pré-filtro ~0,6%; B2 reuse ~0,4%; D early-out BSP ~0,3%; C cache por fragmento ~0,1%. Esses percentuais **não são medidos nem estatisticamente representativos do DEMO3 todo**. A melhoria A **realmente medida** foi ~2,83%, menor que a aproximação teórica de 5,1%.

## 4. Decisão recomendada ao Cláudio

- **Não promover ainda a R64A**: faltam repetição do benchmark (mínimo três A/B) e teste de estado dinâmico PLAY (crop/perfil/menus). A equivalência binária dos cinco quadros está confirmada.
- **Não implementar B1 como skip incondicional** por causa do `XP_FALSE_REAR=1`. Investigar caso concreto e prova de exatidão antes de usar.
- **B2 também é modesto na estimativa** (~0,4%). Considerar C/ASM equivalente apenas após teste isolado; não consumir tempo criando matrizes extensas para ganhos estimados abaixo de 1%.
- A R64D foi compilada no ramo separado `exp-r60-claudio-diag-heap`; **NÃO** misturar seus 50 contadores ao binário de desempenho R64A.
- O dump atual tem `FRAMES=128` e `DF_FRAMES=127`, não 2.134. Se o diagnóstico do candidato B depender da distribuição de todo o DEMO3, exigir mais dados antes de codificar.

Workflows: [A/B byte-exact](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218061144) e [R64D WRAM](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40218307012). Branch de validação `exp-r60-r64a-prologue-memory-safe`, mantendo `exp-r60-wall-pair-asm` intacta.
