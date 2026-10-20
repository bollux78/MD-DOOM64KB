# R46 M2C/P1 — visplane, BSP e sprites 76×44 (fase de coexistência)

**Origem:** M2B aprovada pelo usuário (três ROMs funcionais). A última medição completa de FPS documentada foi a M2A: **11,80 FPS / 180,82 s, 2134 quadros** para 8×8, sem regressão em relação ao controle. A aprovação funcional da M2B não trouxe números novos de FPS.

## Mudanças concretas M2C/P1

- `src/r46_pixel4_culling.c/.h` contém **rotinas verdadeiras 76 colunas** com nomes únicos e vinculadas à ROM 8×8 sem ativação do modo:
  - `R46_P4_PlaneCanExtend`: mesma regra de compatibilidade de interseções de `R_CheckPlane` em visplanes, entrada `top[76]` fornecida pelo chamador (0xFF significa coluna não ocupada).
  - `R46_P4_BSPAnyOpen`: consulta pura no mapa `solidcol[76]`, equivalente ao teste com `memchr` usado em `R_CheckBBox`. Ainda **não** implementa a travessia da árvore BSP 4×4 nem o cálculo angular de bounding boxes.
  - `R46_P4_SpriteBounds`: clipping de faixa horizontal visível 76 colunas, preservando o limite de 2 amostras nas bordas durante gameplay.
  - `R46_P4_SpriteDepth`: escala vertical e passo de textura do sprite para 44 linhas, mantendo `COLEXTRABITS=7`; **não** implementa transformação de mundo/câmera, rotação, clipping vertical detalhado, projeção da arma ou integração com a fila de sprites.
- `R46_P4_CullingOps` valida os símbolos no ELF e obriga o linker a mantê-los. `R46_P4_CullingValidate` é chamado na inicialização, mas não lê os buffers do 8×8 nem modifica o vídeo.
- **RAM permanente adicionada: 0 B** pelos arrays de trabalho do módulo. Sem segunda `visplane_t[76]`, sem `solidcol[76]` estática, sem nova lista de sprites. Todos esses buffers exigirão propriedade segura na etapa M2C seguinte.
- O código `r_draw.c` / `r_plane.c` original continua compilado em 38×22. Não há chamada das novas rotinas no caminho de renderização ativa, logo nenhuma promessa de desempenho do modo 4×4 ainda.
- Foi mantida a escolha flexível de camada VDP: céu pode ficar no software ou plano B, arma/HUD podem usar plano B ou hardware sprites. Nenhuma alocação de VRAM adicional nesta etapa.

## Testes da CI

Workflow `.github/workflows/r46-m2c-p1.yml` executa:
1. Oracles determinísticos de P1, junto dos M1B/M2A/M2B aprovados. Contam 30 mil visplanes e >1 milhão de consultas de oclusão; conferem 20 mil limites de sprite, 3.831 profundidades e casos negativos.
2. Três builds separadas: `doom-md-r46-primary-perf.bin` (controle), `doom-md-r46-m2c-perf.bin` (8×8 com novos kernels co-linkados), `doom-md-r46-m2c-play.bin` (jogável).
3. Auditoria do ELF (símbolos e `.bss` não maior que controle), ROM linear ≤4 MiB, cabeçalho e flags.
4. Inicialização no BlastEm por 300 quadros, todos.
5. Artefato com três ROMs, relatório de memória e manifesto de hashes.

## Gate manual

Antes de avançar para M2C/P2 ou M3, executar DEMO3 completa nas ROMs PERF e comparar com 11,80 FPS e 180,82 s. Verificar na PLAY: menus, música/SFX, Off/Checker/Vertical, E1M1, transição E1M2 e SRAM.

## Ainda falta para alternância 4×4 em runtime

- M2C/P2: `visplane_t` e spans com buffers compartilhados, limites de viewport, transformações de BSP/segmentos e sprites com estado de câmera; verificar que não há mais referências fixas de 38×22 nos loops do 4×4.
- M3: gerenciamento exclusivo do framebuffer 2128 B, DMA pendente, CRAM, VRAM, bancos, imagem estática, interrupções e plano A/B.
- M4: toggle real no Options sem resetar nível, sprites ou estado.

**Não confundir M2C/P1 aprovada em CI com um renderizador 4×4 já executando no jogo.** A meta é progressão verificável sem destruir a base R39f de 11,80 FPS nem a R44 ASM de 3,88 FPS.
