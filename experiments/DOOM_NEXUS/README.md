# NEXUS 2 × 2 · otimização

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
| A | Buffer por colunas e reutilização de tiles de cor sólida. |
| B | Escrita direta no buffer de tiles 4 bpp. |
| C | Roda o benchmark de 39 quadros por caminho e exibe mediana, P95 e máximo. |

A câmera livre acompanha a altura do setor e atravessa paredes. Volte
à pose fixa com Start para retomar a inspeção dentro do mapa.

## Renderização e testes

A travessia BSP perto–longe descarta caixas inteiramente fora do intervalo
de colunas abertas. A projeção compartilha uma escala de perspectiva por
parede entre os quatro limites verticais. Os spans verticais do modo A
escrevem em endereços contíguos com uma rotina de byte para o 68000.

No modo A, cada cor sólida já tem um tile na VRAM. O empacotamento envia
só os padrões dos tiles com mais de uma cor, além de 600 bytes da tabela
de tiles. Quando os dados cabem em 7.000 bytes, a atualização usa um
VBlank. Se excederem esse orçamento, o renderer divide a transferência
em dois VBlanks. A troca do banco ocorre após a transferência completa.
O modo B escreve e transfere todos os 9.600 bytes de padrões.

A tela individual mostra os tempos aproximados de render, empacotamento,
espera, DMA e quadro. A cor magenta indica pixels sem cobertura geométrica.

O teste no PC compara os tiles produzidos por A e B e usa um traçador de
raios independente para conferir a geometria das poses fixas. A comparação desta variante passou pelas 13 poses de cada mapa no Genesis Plus GX.

## Comparação com a versão 2 × 2 aprovada no console

Genesis Plus GX, modo A, 13 poses e três amostras por pose. Tempo total
por quadro, incluindo espera e transferência ao VDP.

| Mapa | Mediana anterior → otimizada | P95 anterior → otimizado |
| --- | ---: | ---: |
| E1M1 | 183 → 98 ms | 366 → 199 ms |
| E1M2 | 166 → 81 ms | 615 → 282 ms |
| E1M9 | 183 → 98 ms | 266 → 116 ms |

Nas 39 poses, os dois caminhos apresentaram a mesma imagem. A comparação
com o traçador de raios encontrou 15 pixels divergentes em bordas e
zero pixels descobertos. A variante otimizada aguarda teste no Mega Drive.
