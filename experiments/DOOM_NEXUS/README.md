# NEXUS N01

Protótipo independente de renderização 2.5D para Mega Drive. A ROM importa a
geometria de E1M1 de um WAD local e apresenta poses fixas a 128 × 96, em
cores sólidas. A sequência começa no spawn e aproxima a câmera de uma
passagem entre setores de alturas diferentes.

## Compilar

Requer Python 3, Java e SGDK nativo com toolchain m68k-elf. Execute neste diretório:

```sh
GDK=/caminho/para/sgdk DOOM1_WAD=/caminho/para/doom1.wad bash build.sh
```

O build produz `out/nexus-n01.bin` e `out/map-audit.json`. O importador
confere E1M1, E1M2 e E1M9. A ROM recebe somente E1M1. No runner, a automação
confere o SHA-256 do WAD usado pelo projeto e arquiva a ROM localmente em
`~/Projetos/nexus-engine/roms/N01/<revisão>/`.

## Controles e medições

| Botão | Função |
| --- | --- |
| Esquerda/direita | Percorre as poses fixas. |
| A | Buffer linear de um byte por pixel e empacotamento em tiles 4 bpp. |
| B | Escrita direta no buffer de tiles 4 bpp. |
| C | Mede 39 apresentações por caminho, alternando a ordem A/B. Exibe mediana, P95 e máximo. |

Os dois caminhos compartilham a travessia BSP perto–longe, a projeção
em ponto fixo e uma janela de oclusão vertical por coluna. Cada apresentação
transfere 6.144 bytes de padrões e 384 bytes de mapa de tiles. O mapa de
tiles aponta para o novo banco depois da transferência dos padrões. A
cor magenta indica pixels para os quais a geometria recortada não forneceu
cobertura.

A tela individual mostra os tempos aproximados de render, empacotamento,
espera, DMA e quadro, a partir do contador do SGDK. No lote, o tempo de cada
quadro inclui a espera até o VBlank e a apresentação. Os números no
emulador e no console devem ser registrados separadamente.

`tools/check_render.c` confere a paridade exata de tiles entre A e B. A
referência em `tools/reference.py` resolve os cruzamentos dos raios por
distância, sem percorrer a BSP, e informa diferenças junto a bordas e no
interior das superfícies. O runner mantém o relatório ao lado da ROM.
