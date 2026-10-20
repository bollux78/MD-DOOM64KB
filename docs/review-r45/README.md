# R45 — Consolidação R39f + R44 ASM/intermissão + R43 cinza (em teste)

## Objetivo
Este é um **marco de integração do código-fonte**, ainda **NÃO** uma ROM com troca real 8×8/4×4 em runtime. O objetivo é verificar que os caminhos de compilação da R39f (38×22 tiles), R44 ASM (76×44 pixels amostrados) e a paleta cinza R43 coexistem na mesma árvore sem regressões. Na etapa posterior M1, os dois backends ainda precisarão coexistir dentro do mesmo ELF.

## Fontes e auditorias
- Ponto de partida: branch `r40c-dual-runtime` com R39f Off / Checker / Vertical no 8×8, R40b anti-flicker no 4×4, XGM2, SFX, SRAM e MOVEP.
- `src/r22_video.inc` portado seletivamente de `r44-pixel4-intermission-fix`: **R42_DrawPackedWall ASM**, somente para 4×4 e guardado por `DOOM_R42_WALL_ASM`; nenhum dos kernels asm do 8×8 é utilizado (o R22 ainda proíbe `R20_REG_COLUMNS` / `FLAT_INLINE`).
- `src/wi_libt.c` da R44: intermissão/textos usam **38×22 caracteres**, independentemente de amostragem 3D em 76×44; capturas do usuário confirmam `E1M1: Hangar`, `FINISHED`, porcentagens e tempos corretos.
- `scripts/lab/gen_r43_gray.py` da R43: gera tabela alternativa `r43_gray_palette.h` usando PLAYPAL para 4×4. Só ativa com `DOOM_R43_GRAY_CRT`. **A paleta cinza ainda NÃO foi aprovada visualmente pelo usuário**; esta branch serve para o teste final.
- Nenhum código do renderizador 8×8 R39f foi descartado.

## ROMs propostas (Actions artifact)
- `doom-md-r45-cell-perf.bin`, `doom-md-r45-cell-play.bin`: 8×8 real, dithering triplo.
- `doom-md-r45-asm-p4perf.bin`, `doom-md-r45-asm-p4play.bin`: 4×4 real, kernel R44 ASM, paleta original.
- `doom-md-r45-gray-p4perf.bin`, `doom-md-r45-gray-p4play.bin`: kernel R44 ASM, paleta 4×4 experimental com cinzas.

## Valores de referência
- R39f/R40c 8×8: ~**11,80 FPS** em DEMO3 2.134 quadros, 180,82 s.
- R44 ASM 4×4: **3,88 FPS**, 550,30 s, 2.134 quadros. A R44 foi aprovada pelo usuário em gameplay/intermissão e troca de fase.
- A R43 cinza alterou a LUT de cores sem mexer no kernel de paredes; **a equivalência de FPS ainda deve ser medida**.

## Teste visual e integridade
1. Executar R45 asm-play e gray-play no mesmo ponto de E1M1, alinhando ângulo e distância. Observar chão, teto, linhas nas paredes, sprites/arma, iluminação. Identificar marrons residuais: a nova paleta neutraliza índices PLAYPAL cinzas, não troca semanticamente todas as texturas marrons.
2. Terminar E1M1 nas duas ROMs 4×4; verificar nomes, porcentagens, Time/Total/Par, transição E1M2 e ausência de flicker da R40b.
3. Confirmar menus Music/SFX, audio PCM/XGM2, preservação do estado. Testar 8×8 Off / Checker / Vertical na R45-cell-play.
4. Correr os três PERF até DEMO3 2.134 frames e comparar média/min/max/duração; verificar que gray ≈ asm em FPS. São ROMs independentes, **não** teste do runtime toggle.
5. Só após confirmar os controles/visuais continuar a integração M1 da futura dual ROM e eventualmente incorporar a paleta cinza vencedora.

**Critério de entrega:** ROMs e scripts auditados no CI, cabeçalho/tamanho real ≤4 MiB, smoke BlastEm, logs e ZIP. Smoke 300 frames não substitui teste da intermissão e nem garante estabilidade no Mega Drive real.
