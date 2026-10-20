# R46 — M1A concluída: rotinas 4×4 vinculadas ao executável 8×8

**Fonte testada:** commit `6803599772882202b7ac7a68ed9650930ec0bacf` (correção `string.h`); workflow `r46-m1-dual-linked.yml` ajustado no commit `041caf1815452226adc05812542035c37196e814`. Execução final aprovada [Actions #39363640958](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39363640958), [artifact #12239100299](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39363640958/artifacts/12239100299).

## O que efetivamente foi feito

- A build primária permanece `VIEWWINDOWWIDTH=38`, `VIEWWINDOWHEIGHT=22`, kernel R20 de tile word, tri-dither Off / Checker / Vertical da R39f.
- O novo arquivo `src/r46_pixel4_secondary.c` é compilado **no mesmo ELF** com `-DDOOM_R46_M1`: `R46_P4_Wall` usa a técnica ASM R42/R44 (escrita nibble packed, stride 38), e fornece `R46_P4_Sprite`, `R46_P4_Flat`, `R46_P4_Clear` e `R46_P4_ExpandPair`, todos com símbolos próprios e tabela de funções `R46_P4_Ops()`.
- `R46_P4_Validate()`, chamada na inicialização real de `src/i_genesisv.c`, confirma a tabela de capacidades 76×44 e os ponteiros de funções, **sem tocar no framebuffer durante gameplay 8×8**.
- O framebuffer 4×4 de **1672 bytes reutiliza** os 2128 bytes de `_s_screen`; não há segundo framebuffer em BSS. Os módulos 4×4 não podem desenhar enquanto o modo 8×8 possui esse buffer. A mudança de ownership durante o frame é trabalho M2/M3.
- O CI verifica pelo executável ELF os símbolos `R46_P4_Ops`, `R46_P4_Validate`, `R46_P4_Wall` e `_s_screen`, além de comparar o consumo real da memória `.bss`.

## Resultados automáticos (não benchmarks do usuário)

| Medida no ELF | Controle primário | R46 M1 ROM com kernels 4×4 vinculados |
|---|---:|---:|
| Text | 2.674.580 bytes | 2.674.068 bytes |
| Data | 452 bytes | 452 bytes |
| BSS | 57.724 bytes | 57.692 bytes |
| Delta BSS | — | **-32 bytes** |
| Imagem ROM linear | 2.752.512 bytes | 2.752.512 bytes |

A diferença text/BSS é resultado da composição/link-LTO de builds distintas; **não** significa que o kernel 4×4 tenha tamanho negativo ou que otimizações automáticas relevantes já tenham sido comprovadas. Não se reservou outro bloco de 1672 bytes. Ambas ROMs passaram pelo boot do BlastEm 300 quadros; isso não mede o ganho FPS ou o funcionamento do modo 4×4 em gameplay.

## Binários entregues para teste

| ROM | Conteúdo | Teste |
|---|---|---|
| `doom-md-r46-primary-perf.bin` | 8×8 R39f controle puro | DEMO3 2134 quadros |
| `doom-md-r46-m1-perf.bin` | 8×8 ativo + rotinas 4×4 ASM vinculadas | DEMO3 2134 quadros, comparar com controle |
| `doom-md-r46-m1-play.bin` | 8×8 ativo + rotinas 4×4 ASM vinculadas | Jogabilidade e menus R39f intactos |

**Ainda não há alternância real de renderização.** O 4×4 vinculado é o kernel gráfico/nibble mais sprites/flats, **não** o pipeline completo 76×44 de BSP/projeção/visplanes nem o upload/VDP. Não chamar esta ROM de dual runtime final. É o marco de **vinculação M1A**, não o término de M1–M4.

## Próximas tarefas: R46 M1B/M2/M3/M4

1. **M1B:** integrar/namespace-isolar o upload de tiles nativos, CRAM, par de bancos VDP, ISR e texto, sem duplicar buffers nem comprometer o `r40b` overlay. Investigar reutilização faseada de `r22_map` de 1596 bytes; a BSS total está apertada.
2. **M2:** especializar a geometria de `r_draw.c` e `r_plane.c`, projeção/angular lookups, clipping e sprites para 38×22 versus 76×44; preservar os dois hot paths, sem branch por pixel. O global `CENTERY` 8×8 não pode ser reutilizado pelo kernel 4×4: R46 usa explicitamente 22 no secundário.
3. **M3:** fazer a troca segura de framebuffer/VDP/CRAM/ISR com DMA concluído e propriedade exclusiva de `_s_screen`, mantendo título/intermissão Bayer8 e texto em 38×22 caracteres.
4. **M4:** habilitar `Render: 8x8 / 4x4` no menu sem reiniciar E1M1 nem perder estado e os toggles música/SFX/dithering. Validar ambas as renderizações com timedemos 2134 quadros, hardware CRT e SRAM.
5. A paleta cinza R43 continua **opcional**, não padrão; preferência futura: chão/teto neutros, paredes na paleta original.

**Baselines do usuário:** R45 8×8 11,80 FPS / 180,82 s; R45 4×4 ASM 3,88 FPS / 550,30 s. Ainda não há FPS R46 M1 medido pelo usuário.
