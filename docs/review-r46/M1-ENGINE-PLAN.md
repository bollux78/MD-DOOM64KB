# R46 M1 — auditoria real da coexistência 8×8/4×4 (WIP)

**Esta branch não possui toggle funcional.** Ela é a próxima etapa de engenharia, derivada da R45 com os 8×8 R39f e 4×4 R44 ASM/intermissão aprovados, mais R43 Gray **opcional**.

## Referências de desempenho medidas pelo usuário

| ROM | FPS médio | DEMO3, 2.134 quadros |
|---|---:|---:|
| R45 8×8 R39f | 11,80 | 180,82 s |
| R45 4×4 R44 ASM | 3,88 | 550,30 s |
| R45 4×4 Gray | 3,86 | 552,75 s |

O usuário aprovou a R45 cell-play e considerou Gray conforme a solicitação, mas sem preferência por ela. **Preservar o visual original do 4×4 como padrão**; eventualmente desejará *apenas chão/teto cinzas, com paredes originais*. Não dar prioridade a esse refinamento até a ROM dual existir.

## Saída do auditor

Execute `python3 scripts/lab/audit_r46_dual_contract.py` para mapear os acoplamentos em `src/i_genesisv.c`, `r_draw.c`, `r_plane.c`, `d_main.c`, `r22_video.inc`, `wi_libt.c` e os scripts de build. Ele valida que a árvore está na arquitetura antiga de seleção **compile-time**; não confundir seu sucesso com coexistência na ROM.

### Bloqueadores reais

- Video: `i_genesisv.c` inclui `r22_video.inc` somente sob `DOOM_R22_PIXEL4`, senão compila o 8×8 com os **mesmos símbolos externos**, portanto duas unidades de tradução idênticas causariam colisões de símbolos; solucionar nomes, callbacks e estado.
- Geometria 3D: `VIEWWINDOWWIDTH/HEIGHT`, `MAPWIDTH`, `CENTERX/CENTERY`, projeção, ângulo-x, clip/floor/ceiling, planos e sprite scale gerados **para somente uma geometria**. Trocar o vídeo sem trocar tabelas gera geometria errada e risco de corrupção.
- **WRAM 64 KiB**: no 8×8, tilemap `38×28×2=2128` B; no 4×4, framebuffer `1672` B, mapa `38×21×2=1596` B, BSS/heap/stack apertados. A correção da intermissão R40b recicla **210 B** da memória do tilemap durante imagens estáticas. Não declarar que a coexistência cabe antes de medir linker/heap com ambos.
- **VRAM**: 8×8 requer padrões sólidos+checker+vertical; 4×4 usa dois bancos dinâmicos próximos da fonte SGDK. A troca deve encerrar DMA/ISR, reconfigurar tiles, CRAM, WINDOW/HUD com troca atômica de callback.
- **R44 ASM** é nativo 4bpp 76×44, stride 38; nunca tentar aplicar `R20_REG_COLUMNS`/ `FLAT_INLINE` diretamente.
- **WIMAP0**: intermissão deve continuar nas dimensões **38×22 caracteres**, mesmo em pixel4 76×44.
- **Cores**: `DOOM_R43_GRAY_CRT` opcional; não impor cinza em paredes ao integrar.

### Etapas e gates

1. Namespace isolado de renderizadores e enum estável; testar que ambos podem *linkar* numa única ROM/ELF sem colidir nomes ou ultrapassar WRAM. Essa etapa **ainda não está implementada**.
2. Tabelas de ângulos, projeção, clipping, pisos, sprites e buffers separados/compartilhados com seleção segura fora dos hot loops.
3. VDP/CRAM e VBlank preparados para transição segura com DMA concluído, imagem estática e texto sem ghosting.
4. Somente então ligar `Render: 8x8 / 4x4` no Options. Não reiniciar nível nem zerar objetos, e manter Dithering Off/Checker/Vertical ao retornar para 8×8.

A CI desta branch neste estágio valida apenas a **auditoria de dependências**, não compila nem valida um backend duplo em runtime. R45 continua a referência funcional de ROMs individuais até passar pelos gates anteriores.
