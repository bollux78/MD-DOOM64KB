# NEXUS N02 · 2 × 2

Motor 2.5D experimental para Mega Drive. A N01 foi aprovada no console por Daniel.
A N02 usa o mesmo renderizador para E1M1, E1M2 e E1M9, em três ROMs de
inspeção. Esta variante desenha 80 × 60 pixels lógicos e os apresenta em 160 × 120,
com escala inteira de 2 × 2 e proporção 4:3. Usa cores sólidas para distinguir
pisos, tetos e paredes.

## Compilar

Requer Python 3, Java e SGDK nativo com toolchain m68k-elf. Execute neste diretório:

```sh
GDK=/caminho/para/sgdk DOOM1_WAD=/caminho/para/doom1.wad bash build.sh E1M1
```

O argumento aceita E1M1, E1M2 ou E1M9. O build produz a ROM e o relatório
de importação em `out/<mapa>/`.

## Controles

| Botão | Função |
| --- | --- |
| Esquerda/direita | Percorre as poses fixas. Na câmera livre, gira a câmera. |
| Cima/baixo | Avança ou recua na câmera livre. |
| Start | Alterna entre a pose fixa selecionada e a câmera livre. |
| A | Buffer linear de um byte por pixel e empacotamento em tiles 4 bpp. |
| B | Escrita direta no buffer de tiles 4 bpp. |
| C | Roda o benchmark de 39 quadros por caminho e exibe mediana, P95 e máximo. |

A câmera livre acompanha a altura do setor e atravessa paredes. Volte
à pose fixa com Start para retomar a inspeção dentro do mapa.

## Renderização e testes

A travessia BSP perto–longe descarta ramos distantes quando a caixa do WAD
fica inteiramente fora do frustum. A projeção usa divisão inteira de 32
bits quando o numerador cabe sem perda de precisão e mantém 64 bits para
os demais casos. O caminho direto escreve em trechos contíguos de cada tile.

Cada apresentação transfere 9.600 bytes de padrões e 600 bytes de mapa
de tiles em dois VBlanks. A primeira metade é escrita no banco oculto e a
exibição muda após a transferência da segunda metade. A tela individual mostra tempos aproximados de render,
empacotamento, espera, DMA e quadro. No lote, o tempo de cada quadro inclui
a espera até o VBlank e a apresentação. A cor magenta identifica pixels
que ficaram sem cobertura.

O teste no PC compara os tiles produzidos por A e B e usa um traçador de
raios independente para conferir a geometria das poses fixas. A comparação desta variante passou pelas 13 poses de cada mapa no Genesis Plus GX.

## Comparação em E1M1

Mesmo Genesis Plus GX, 39 quadros por caminho e as mesmas 13 poses.
Tempos em milissegundos, incluindo a apresentação. A mediana e o P95 são
medidos pela ROM. O teste no Mega Drive físico está pendente.

| Resolução interna | Viewport | A mediana / P95 | B mediana / P95 |
| --- | --- | ---: | ---: |
| 128 × 96 | 128 × 96 | 249 / 449 | 232 / 449 |
| 96 × 64 | 192 × 128 | 216 / 415 | 249 / 449 |
| 80 × 60 | 160 × 120 | 183 / 366 | 216 / 399 |
