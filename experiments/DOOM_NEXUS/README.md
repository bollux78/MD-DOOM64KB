# NEXUS N02

Motor 2.5D experimental para Mega Drive. A N01 foi aprovada no console por Daniel.
A N02 usa o mesmo renderizador para E1M1, E1M2 e E1M9, em três ROMs de
inspeção. A imagem tem 128 × 96 pixels e usa cores sólidas para distinguir
pisos, tetos e paredes.

## Compilar

Requer Python 3, Java e SGDK nativo com toolchain m68k-elf. Execute neste diretório:

```sh
GDK=/caminho/para/sgdk DOOM1_WAD=/caminho/para/doom1.wad bash build.sh E1M1
```

O argumento aceita E1M1, E1M2 ou E1M9. O build produz a ROM e o relatório
de importação em `out/<mapa>/`. O runner usa o WAD local do projeto e arquiva
as ROMs em `~/Projetos/nexus-engine/roms/N02/<revisão>/`.

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

Cada apresentação transfere 6.144 bytes de padrões e 384 bytes de mapa
de tiles. A tela individual mostra tempos aproximados de render,
empacotamento, espera, DMA e quadro. No lote, o tempo de cada quadro inclui
a espera até o VBlank e a apresentação. A cor magenta identifica pixels
que ficaram sem cobertura.

O teste no PC compara os tiles produzidos por A e B e usa um traçador de
raios independente para conferir a geometria das poses fixas. A automação
repete a validação para cada mapa e executa o teste de inicialização no BlastEm.
