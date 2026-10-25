# R66 — Cláudio: compartilhamento horizontal aproximado (RESULTADOS EM 68000)

**25/10/2026 · status: candidato experimental promissor, NÃO baseline promovida.**

## Objetivo de produto

DOOM-MD pretende executar o máximo possível da lógica original de DOOM no Mega Drive real, sem exigir fidelidade numérica do rasterizador. Geometria e jogabilidade precisam funcionar; distorções moderadas de textura, quantização e 'wobble' são aceitáveis **se** FPS subir materialmente e a imagem permanecer reconhecível em movimento.

## Proposta exata do Cláudio (pacote r66.zip)

README `README_R66.md`; patch `r66-colpair.patch`, SHA-256 verificado: `75000f50d2b27e8f0405714dd9a1c6ce6d6104589cdef9161758276ef3fce387`. Base R64A, independente de R65-P1 e R65-P2.

Com `DOOM_R66_COLPAIR`, o laço `R_RenderSegLoop` para x ímpar de um mesmo segmento reutiliza os cálculos da coluna par anterior:
- coordenada `texturecolumn` (elimina tangente + produto);
- `dcvars.fracstep` (elimina recíproca/LUT/DIVU), restaurada porque `R_DrawSky` pode modificá-la;
- para `midtexture` de parede de um lado só, ponteiro `dcvars.source` (elimina `R_GetColumn`/`R_ComposeColumn` subsequente).

`yl/yh`, `floorclip`, `ceilingclip`, `solidcol`, `rw_scale`, `pixhigh/pixlow`, chão/teto e BSP continuam calculados por coluna. Atenção: `maskedtexturecol[rw_x]` também reutiliza `texturecolumn` nas ímpares, portanto texturas mascaradas podem apresentar simplificação horizontal. `r66_src` pode apontar para memória de scratch/cache em composições; observar portas/céu/grades em movimento para detectar fonte sobrescrita. Nenhuma variável global nova; somente locais na pilha.

## Build e audit

Branch `exp-r66-claudio-colpair`, a partir do commit R64A `b6e774676ed58fb950058d0f78108e2bbcf859a6`. O kernel `R60_WallColumn`, as tabelas R56/R59 e os demais subsistemas estão preservados. O build script ajustou apenas o **nome da ROM controle** de `ref-perf` para `r64a-perf`, para comparação EXATA com a ROM validada anteriormente.

[Build MarsDev e ARTIFACT com ROMs/ELFs](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40231459814/artifacts/12613800904). Todos os quatro smoke tests BlastEm (800 e 10000 frames por ROM PERF, máximo por processo 10000) passaram. ROMs 2.883.584 bytes.

| Variante | BSS bytes | Status |
|---|---:|---|
| `doom-md-r60-r64a-perf.bin` | 57900 | reproduz ROM aprovada **byte a byte** |
| `doom-md-r60-r66-perf.bin` | 57900 | +0 BSS |
| `doom-md-r60-r66-play.bin` | 57908 | igual à R64A PLAY |

## Benchmark de VBlank A/B, 3 repetições (DEMO3 *PREFIXO*)

[Artifact dos 6 testes, JSON, logs e 10 framebuffers brutos](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40231845530/artifacts/12613221700).

Tempo dos contadores internos `bench_frames`, `bench_start_vb`, `_g_vblankCount` de ROMs sem instrumentação, lido via RSP. Clock nominal do Mega Drive 7,67 MHz, mesma condição visual H40/crop H16 V16. Não confundir com duração host BlastEm. Cada invocação fica abaixo de 10000 quadros do emulador.

| Tic acumulado | R64A FPS | R66 FPS | ganho |
|---:|---:|---:|---:|
| 64 (63 quadros desenhados) | 4,0645 | 4,1722 | +2,649% |
| 128 (127 quadros) | 3,9441 | 4,0446 | +2,548% |
| 256 (255 quadros) | 4,4207 | 4,5590 | +3,129% |

Três repetições em cada ponto resultaram iguais (emulação determinística). **O benchmark completo DEMO3 de 2.134 quadros ainda não foi executado nesta R66. NÃO afirmar +3,13% nos 2.134 quadros.**

## Divergência visual DELIBERADA em amostras reais de Pixel4

Para cada tic, capturadas 3344 bytes `r22_fb.pixels` tanto da R64A como da R66. Quantidade de valores nibble (4 bits) divergentes, dentre 6688 nibbles:

| Tic | Nibbles diferentes | Percentual do framebuffer |
|---:|---:|---:|
| 8 | 141 | 2,108% |
| 16 | 147 | 2,198% |
| 64 | 87 | 1,301% |
| 128 | 193 | 2,886% |
| 256 | 175 | 2,617% |

**Verificação adicional pela fórmula real de `R22_PixelByte` em Pair-V:** das 743 amostras divergentes em cinco snapshots, **742 ocorrem em x ímpar; somente 1 em x par**, na coordenada (50,37) do tic 256 (índice anterior=13, candidato=6). Todas as diferenças ficaram em `x=[6,71], y=[6,39]` do recorte visível H40 H16 V16. Isto é consistente com a mudança pretendida apenas em pares de colunas. A única diferença em coluna par deve ser investigada se se repetir/piorar em mais frames ou em jogo, mas não implica reprovação imediata num renderer aproximado.

Percentuais representam **amostras do framebuffer, não erro de cor perceptual**. A janela ativa tem 66×34 amostras; portanto 141/2244 = 6,3% dela, 193/2244 = 8,6%, etc. Capturas paradas não garantem suavidade em movimento.

## Verificações pendentes e critérios de aceitação

1. **DEMO3 completo (2.134 quadros)** da R66 PERF e da R64A PERF, mesma condição H40, crop 16/16, clock 7,67 MHz; objetivo do Cláudio >+3% FPS total. Também comparar H32/crop16 prático.
2. Qualidade visual em movimento E1M1: aproximar/afastar de paredes, girar câmera, cruzar portas, texturas compostas, grades, sky, transparências, sprites. Sacrifício controlado de textura é permitido; geometria instável, buracos e cache visualmente corrompido NÃO.
3. Iniciar e terminar E1M1 no PLAY com menu Start rápido, sound/XGM2, troca H32/H40/crops e seis perfis R59.
4. Se cenário próximo à câmera ficar muito blocado, experimentar **resolução adaptativa de cálculo por segmento** (não adicionar verificação cara em cada pixel/coluna sem custo medido) e manter a R66 simples como controle.

Não exigir hashes de framebuffer idênticos, porque o projeto **aceita perda intencional de precisão**. Preservar R60 e R64A, não mesclar até gates cumpridos.
