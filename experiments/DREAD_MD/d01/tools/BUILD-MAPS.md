# Builds por mapa do DREAD-MD D01

```sh
GDK=/caminho/sgdk bash experiments/DREAD_MD/d01/tools/build_map.sh \
    /caminho/freedoom1.wad E1M1 /caminho/saida 'FREEDOOM DREAD MD E1M1'
```

O script usa Python com NumPy e Pillow, um compilador C nativo, a toolchain
m68k-elf e SGDK. Gera uma ROM e um ELF local para cada chamada. Use diretórios
diferentes para WADs diferentes. Todas as fases usam o renderer D01 em modo
de linhas, com as duas larguras de tela disponíveis no menu. Isso evita
a cópia de texturas em words. Estes builds têm título de diagnóstico, HUD e
arma extraídos do WAD compatível e começam sem o driver de música.

O modo `--geometry-only` testa geometria e texturas de um WAD como o Heretic.
Ele dispensa o HUD, a arma e os objetos do Doom. A ROM de Heretic é um teste
privado, sujeito à autorização antes de publicação.

Os índices de setor agora têm 16 bits. O gerador de PVS e o console usam a
mesma contagem de setores do mapa convertido. Em mapas acima de 2.730 vértices,
o cache de transformações usa 2.048 posições com chave, para limitar RAM.

Cada build contém um único mapa. Portas existentes e recorte de sprites vêm
do D01, com objetos e monstros estáticos. Ainda faltam transições de fase,
recursos compartilhados e compressão do PVS para um episódio na mesma ROM.

## Doom shareware em uma ROM

```sh
GDK=/caminho/sgdk bash experiments/DREAD_MD/d01/tools/build_map.sh \
    /caminho/doom1.wad EPISODE /caminho/saida 'DREAD MD DOOM SHAREWARE'
```

Gera `EPISODE.bin` com E1M1 a E1M9. Na abertura, START, A, B ou C
mostram o menu. Cima e baixo movem o cursor. A ou START confirmam e B
volta. NEW GAME entra em E1M1, SELECT LEVEL lista as nove fases e
BENCHMARK roda o percurso fixo de E1M1. Para escolher outra fase,
reinicie a ROM. Durante o jogo, START abre a pausa do D01.

A paleta ajustada para E1M1 é compartilhada pelo episódio. O empacotador
deduplica colunas de paredes, tabelas de colunas e blocos de sprites. As
colunas mantêm o formato consumido pelos escaladores 68000. Cada linha
do PVS é comprimida separadamente e a ROM só descomprime ao entrar em outro
subsetor. Geometria de uso direto permanece na ROM, com o ID de linedef
redundante de cada seg removido. HUD, rostos e arma usam um dicionário
compartilhado, com quadros de DMA preparados fora do VBlank. O build também
embute a introdução e as nove faixas no formato XGM2. A abertura usa a
arte do D01, com fundo escurecido e texto branco enquanto o menu está aberto.

`DREAD_PREPARED_MAPS` permite reaproveitar uma conversão offline. Os nove
subdiretórios devem vir do mesmo WAD e da mesma paleta, cada um contendo
`mapdata.c` e `pvs.c`.
