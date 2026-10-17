# Estado e arquitetura

## Alvo e restrições

Mega Drive original: Motorola68000 a7,67MHz,64KiB de RAM principal, VDP separado, Z80 para música. Overclock existe no console, mas os tempos de hardware usados aqui são na frequência habitual de7,67MHz informada pelo usuário. Sem32X. GCC m68k-elf15.2.0 com SGDK/MARSDEV. Sem instruções68020+, escalas indexadas ou suposições de cache de CPU.

Port MD-DOOM64KB, render atual por células/tiles8x8, viewport38x22 e HUD textual em saída38x28. Não é render pixel a pixel. Cache16 na RAM principal; zona Doom43KiB. Música E1M1 VGM, flags de SFX silenciosos. Não espera explicitamente VBlank. DEMO3/NTSC60Hz;2134 quadros renderizados. Os FPS do placar são do jogo, não os ~60FPS que aparecem na barra do emulador.

`CANONICAL.md` e README antigos descrevem outras bases (p.ex.38x24): NÃO usar como configuração atual. As flags em evidence e matriz h são a autoridade.

## Base já incorporada

S2: sight BSP iterativo para eliminar estouro da pilha recursiva; S3: render BSP iterativo. P2: incremento de fração com ADD/ADDX. M1: multiplicação especializada de tangentes no caso16bits. M3: matemática de escala. R2: memoização de cellmap. HUD/FPS só atualizados quando necessário. Flat DBRA da R19. Inlining natural do compilador; não reintroduzir controle noinline perdedor.

## Opções da vencedora vc-all

|Código|Flag|Implementação e propósito|
|---|---|---|
|V3|DOOM_R20_DMA_BATCH|`src/i_genesisv.c` (`R20_UploadRows`), `src/r20_dma.h`: lote de transferências das linhas do tilemap, uma aquisição do barramento Z80, configuração comum do VDP|
|color|DOOM_R20_COLOR_ROM|`scripts/gen_colormap_cells.py`, `src/i_genesisv.c`: tabela de células constante em ROM; libera512B de RAM|
|R5|DOOM_R20_REG_COLUMNS|`src/r20_reg_columns.s/.h`, `src/r_draw.c`: kernel de paredes com ABI privada por registradores|
|c/cache|DOOM_R20_CACHE_DIRECT|`src/r_draw.c`: compõe diretamente no slot de128B do cache; remove temporário/cópia e libera128B|
|R6|DOOM_R20_FLAT_INLINE|`src/r_draw.c`: escrita DBRA de chão/teto inline e células calculadas fora do loop|
|M2|DOOM_R20_TAN32|`src/r_draw.c` e helpers de multiplicação: caso largo da tangente, mantendo caminho16bits de M1|

`vc` = V3+color. `c` = cache direto, não color. Matriz cobre todos os16subconjuntos deR5/c/R6/M2 sobrevc; maiscontrol/color/v3/no-v3 e20diagnósticos pareados.

## Detalhes que devem ser preservados

R5 usa a0=destino,a1=fonte,a2=cellmap,d0=fração,d1=passo,d2=contagem-1; clobbersd0-d7,a0,cc,memory e preservaa1/a2. Verificar wrapper e assembly, não chamar com ABI C normal. `R_DrawSky` muda `dcvars.colormap` para fullbright e não restaura no comportamento original: a memoização das paredes deve acompanhar o ponteiro REAL, não assumir colormap fixa por segmento.

V3 preserva SR e estado prévio do barramento Z80, autoincremento2; destino BG_A com stride128B e38palavras por linha. Segundo word do comando DMA é emitido a partir de operando em RAM, como workaround do SGDK/hardware. Não trocar ingenuamente por imediato/registrador. Ver rotinas exatas e evidência do SDK.

CACHE_DIRECT depende das colunas WAD totalmente cobertas: o teste atual verifica6712colunas, altura≤128 e múltipla de4. Não estender automaticamente a outro WAD sem revalidar cobertura, buracos e bytes fora da altura.
