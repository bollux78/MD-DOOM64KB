# Trechos confirmados por execução

Sintaxe abaixo normalizada; bytes e sintaxe GNU originais nos `.txt` ao lado.

## Saída direta (executada sem SRAM e com SRAM8)

```asm
07E39A: move.w #17,d7       ; 18 bandas de tiles na vertical
07E39E: move.w #144,d6      ; distância entre duas tiras adjacentes de 4 pixels
07E3A2: move.w #288,d4      ; próximo par de tiras
07E3A8: moveq #39,d5       ; 40 tiles na horizontal
07E3AA: movea.l a2,a0      ; metade esquerda da linha de 8 pixels
07E3AC: lea (a2,d6.w),a1   ; metade direita
07E3B0: move.w (a0)+,d0
07E3B2: swap d0
07E3B4: move.w (a1)+,d0    ; junta quatro pixels + quatro pixels
07E3B6: move.l d0,(a6)     ; emite linha 1 na porta C00000
07E3B8: move.l d0,(a6)     ; DUPLICA fisicamente a linha
; Mais três grupos iguais completam oito linhas do tile.
07E3D8: adda.w d4,a2      ; pula para o próximo par de tiras
07E3DA: dbra d5,07E3AA
07E3DE: addq.l #8,a4      ; próxima banda: avança quatro linhas fonte de 2 bytes
07E3E0: dbra d7,07E3A6
```

A repetição é de palavras de pixels no VDP, não de scroll por H-int. No caminho `07E3EA`, o corpo equivalente usa `(a6)+` para escrever em memória; o destino observado é `20A600`. O modelo independente `repack.py` confere os 23.040 bytes resultantes.

## Núcleo de colunas — exemplo de variante

```asm
06FF16: add.l  [FF01B8],d4 ; avanço fracionário (significado completo em investigação)
06FF1C: move.l [FF01BC],d3
06FF22: addx.l d3,d0      ; propaga carry para valor empacotado
06FF24: move.l [FF01C0],d3
06FF2A: addx.l d3,d1
06FF2C: move.w [FF01D0],d3
06FF32: addx.w d3,d2
06FF34: add.l  [FF01D4],d6
06FF3A: movea.l (a4)+,sp ; destino da coluna; SP deixa de ser a stack normal
06FF3C: move.l  (a4)+,d3 ; recorte empacotado, 8 bytes sequenciais ao todo
06FF3E: beq    070354    ; coluna encerrada
```

Não atribuir automaticamente cada metade dos registradores a uma borda até decodificar todas as variantes. A preparação `0770B6` contém multiplicações e divisões reais; a ausência dessas instruções no pequeno avanço de coluna não significa ausência no frame.

## Seleção e desenho de paredes

```asm
086C70: movea.l [FF31C6],a0
086C76: move.l  (a0),-(sp)
086C78: jsr 07E150        ; interpretação do stream/lista de candidatos
086C7E: jsr 07E132        ; paredes
086C84: addq.l #4,sp
086C86: jmp 07E140        ; sprites
```

O timing usa essas entradas e retornos observados. O stream lido por `077402` não foi completamente decodificado neste checkpoint; chamar isso de um conversor de mapas reconstruído seria prematuro.
