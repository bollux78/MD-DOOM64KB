# MD-DOOM64KB — Cláudio: fontes R60 PairASM e diagnóstico de desempenho

**Snapshot exato:** branch `exp-r60-wall-pair-asm`, commit `c670a08af0646c35a4859eae4d2ccc2f4f9a6263`.
A branch `handoff-r60-claudio-diagnostics` parte do mesmo commit e **não altera o renderer**.
Baseline medida: R60 PairASM **6,72 FPS no clock original (~7,67 MHz)** no DEMO3 de 2.134 quadros (aproximadamente; depende do mesmo viewport e parâmetros). Compare tempo bruto, não apenas FPS arredondado.

## 1. Mapa dos fontes entregues

O código **não tem** `src/r_pair_wall.s`: o kernel real é **`src/r60_pair_wall.s`**, com ABI e protótipos em `src/r60_pair_wall.h`.
O código **não tem** `src/r_main.c`: o pipeline de renderização, clipping e BSP fica em **`src/r_draw.c`**; declarações em `src/r_main.h`.

| Arquivo | Responsabilidade |
|---|---|
| `src/r_draw.c` | `R_RenderSegLoop`, `R_StoreWallRange`, `R_AddLine`, `R_CheckBBox`, `R_RenderBSPNode`, `R_RenderPlayerView`; paredes, flats, sprites |
| `src/r60_pair_wall.s` | Kernel ASM Pair-V Fast comprovado, **não substituir por R61/R62** |
| `src/r60_pair_wall.h` | Protótipo/ABI do kernel |
| `src/r_main.h` | Tipos/interfaces do render |
| `src/r22_video.inc` | `R42_DrawPackedWall`, `R60_WallColumn`, `I_FinishUpdate`, `R22_UploadBack`, VDP/LUT |
| `src/i_genesis.c` | VBlank de 60 Hz, relógio de Doom, `I_GetTime` e callbacks |
| `src/d_main.c` | `D_DoomLoop`, `TryRunTics`, `D_BuildNewTiccmds`, modo singletics |
| `src/g_game.c` | Ticker do jogo e leitura do DEMO3 |
| `src/p_tick.c` / `src/p_tick.h` | Tickers de entidades/thinkers |
| `scripts/lab/build_r60_wall.py` | Flags da R60, perf/play A/B, auditoria de memória |
| `scripts/lab/build_r35_linear.fish` | Compilação Pixel4 com identidade e recursos |
| `.github/workflows/r60-wall-asm.yml` | CI reproduzível da R60 |

Os arquivos estão em `fontes/`, preservando caminhos relativos do repositório. O pacote contém também `SOURCE-SHA256SUMS.txt`.

## 2. O que significavam lazy / locals / phase na R63/R64

Essas opções **NÃO estão habilitadas na baseline R60**. Foram selecionadas por macros experimentais:

- **`lazy` = `DOOM_R21_LAZY_TEXCOL` (C, em `R_RenderSegLoop`)**: antecipa a decisão se há um tier de parede visível ou textura mascarada e **evita calcular `texturecolumn` e `fracstep`** quando esses valores não serão usados. Permanece exato apenas se todo caminho de consumo for considerado; céu estabelece sua própria fase.
- **`locals` = `DOOM_R21_SEGLOOP_LOCALS` (C, em `R_RenderSegLoop`)**: copia o estado mutável do loop (`rw_scale`, `topfrac`, `bottomfrac`, `pixhigh`, `pixlow` e respectivos passos/limites) de statics/globais para variáveis locais, que o compilador pode manter em registradores; grava de volta ao fim do loop. Objetivo: reduzir loads/stores por coluna.
- **`phase` = `DOOM_R63_PHASE_ASM` (ASM, em `R42_DrawPackedWall`)**: substitui o cálculo em C da **fase inicial da textura após clipping vertical**, usando `R63_Phase` e `MULU.W` com aritmética modular de 16 bits; não altera a rasterização da coluna em si. `pswap` invertia operandos da multiplicação; no 68000 isso pode afetar o custo da `MULU`.

Outros auxiliares eram `tan` (produto tangente 16×32 ASM), `clip`/`bbox` (buscas 0/1 ASM) e combinações.
**Resultados isolados R63:** `lazy` 6,72 FPS / 317,58 s; `locals` 6,72 / 317,75 s; `phase` 6,65 / 320,97 s; `ctl` 6,67 / 319,97 s. **R64:** `ll` (lazy+locals) 6,74 / 316,77 s; `allnop` (sem phase) 6,76 / 315,68 s; `allref` (com phase) 6,73 / 316,90 s. Diferenças pequenas em execuções únicas no BlastEm, não confirmam ganho repetível no hardware. **Não transportar automaticamente essas experiências descartadas para R60**.

Referência histórica para consultar a implementação original **sem usar como base de desenvolvimento**: commit `c1e0a73962cb9cd9d539034be67ac892c5441b7d` da R63; arquivos `src/r_draw.c`, `src/r22_video.inc` e `src/r63_asm.h`. As fontes históricas R63 ficam referenciadas pelo commit acima, mas **não são a base deste ZIP**: ele reúne exclusivamente os arquivos R60 e este diagnóstico.

## 3. Política real de tics por quadro no PLAY

**Fato no código da R60, não estimativa:**

- `src/i_genesis.c`: o VBlank NTSC incrementa `ticcount` a **60 Hz**; `I_GetTime() = ticcount * TICRATE / 60`. `TICRATE` do Doom é **35 Hz**.
- `src/d_main.c`: **PLAY normal = `singletics == false`**, chama `TryRunTics()`. O laço produz tics de input conforme `I_GetTime`; se existem tics pendentes, executa `M_Ticker`, `G_Ticker` e incrementa `_g_gametic` repetidamente **antes de renderizar**.
- Consequência: **não há um limite fixo de um tic por frame renderizado no PLAY**. Se renderizar a 6–7 FPS, podem acumular aproximadamente 5–6 tics de jogo por quadro exibido, com variação e esperas conforme o tempo real; o número não é constante e não é uma medição executada aqui.
- `D_BuildNewTiccmds` limita a antecedência da fila quando `maketic - _g_gametic > 3`; **não confundir essa condição com limitar a quantidade total de tics por frame**.
- **PERF/timedemo:** `singletics == true` força **um gametic por iteração externa**, portanto os 2.134 quadros DEMO3 são medidos para benchmarking mesmo a FPS inferior a 35; é diferente do PLAY e não mantém simulação em tempo real.
- **Benchmark iniciado pelo menu no PLAY:** `D_R50_BenchmarkStart()` também seta `singletics=true`; ao sair, `D_R50_BenchmarkFinish()` ressincroniza `maketic` e relógio. É uma exceção temporária ao PLAY normal.
- Não adotar 20, 15 ou 10 tics/s sem experimento próprio e explícito: modifica semântica/velocidade/latência do jogo. Medir FPS de renderização separadamente da cadência de simulação.

## 4. O que investigar (antes de programar)

1. Quantificar **trabalho invisível**: segmentos descartados após clipping, subsectors ignoráveis, colunas/tier nunca desenhados; coletar contadores por quadro e testar impacto da instrumentação.
2. Verificar decisões estruturais anteriores a `R_RenderSegLoop`: evitar setup de paredes que não produzirão pixels, preservando ordering, portas, masked walls e sprites.
3. Examinar consumo por coluna em `R_RenderSegLoop`: expressões invariantes por segmento, `DIVU`/`MULU`, mapeamento de textura e setup de escala. Preferir hoisting/remover trabalho a somente reescrever C em ASM.
4. BSP: comparar `R_CheckBBox`, `R_AddLine`, `R_RenderBSPNode`; criar métricas de nós visitados, nós realmente úteis e rejeição por abertura/oclusão.
5. Flats e sprites: reduzir overdraw e conversões redundantes, respeitando as regras de recorte, textura, dither e transparência.
6. **Não modificar** kernel `R60_WallColumn`, LUT composta/CM6/R59, ABI, H32/H40, crops, áudio, mapa/recursos ou política de tics na primeira matriz.

Critério: **alteração estrutural isolada**, com ROM controle e candidata em PERF/PLAY, DEMO3 em mesmo clock (padrão 7,67 MHz), mesma resolução/crop/modo de cor, checagem visual e hardware. Buscar ganhos materiais (idealmente >=5% real), mas não alegar melhora somente com ciclo teórico.

Referências para custo 68000/tempo de bus: Núcleo integrado `Nuked-MD-FPGA` e `Genesis_MiSTer`, com ROM/WRAM/SRAM, wait states, DMA e arbitragem adequadamente modelados. Não alegar simulação HDL se ela não foi executada.

**Entrega esperada do Cláudio:** mapa de gargalos com evidências do código, ranking de hipóteses, propostas de A/B com critérios de integridade visual e ganho, sem compilar dezenas de variações antes de um diagnóstico.
