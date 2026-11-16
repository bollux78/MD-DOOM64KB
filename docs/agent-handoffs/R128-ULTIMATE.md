# R128 All com Ultimate Doom

A R128 All de referência é a revisão `d49c4f0`. Este trabalho usa um
IWAD comercial local como entrada. O objetivo é uma ROM para o EverDrive
X7 com os quatro episódios, incluindo as saídas secretas, os chefes e a
progressão próprios de cada episódio.

## Primeiro marco

Os nove mapas do episódio 1 do Ultimate Doom passaram pelo conversor de
mapas da R128, pela geração dos índices espaciais e pelo alinhamento R89.
O passo de escadas da R128 também foi executado. A versão comercial de
E1M1 tem 486 linedefs contra 475 no shareware. Os outros oito mapas têm
os mesmos lumps de mapa nas duas cópias verificadas. O arquivo gerado é
o WAD intermediário do build e usa os recursos gráficos da base R128.
O primeiro episódio ainda precisa de compilação da ROM e teste em jogo.
As demos antigas de E1M1 precisam usar a geometria original de gravação.

## O que falta para os 36 mapas

- Episódios, nomes de mapas e metadados por episódio, seleção no menu,
  saídas secretas, finais, regras dos chefes e numeração nos saves.
- E2M7 tem 323 setores, E3M5 tem 268 e E4M7 tem 288. Esses mapas
  precisam de referências de setor maiores que um byte nas estruturas
  que hoje reservam 255 como sentinela. Medir RAM no carregamento de
  cada mapa depois da mudança.
- São 245 nomes de texturas de parede referenciados, 142 ausentes na
  tabela compacta de referência. Resolver índices de textura e recursos
  por banco ou conjunto de mapas, incluindo pares de interruptores.
- Há 50 tipos de objetos de campanha ausentes na tabela do port.
  E2M1 já pede Cacodemon, Lost Soul, plasma rifle e célula. Cyberdemon,
  Spider Mastermind, BFG e ações específicas exigem lógica e recursos.
  Há também ações de linedef de E4 acima do limite atual de 127.
- O compactador e o mapper precisam ser validados em conjunto. O tamanho
  do IWAD de entrada não indica o tamanho da ROM. Verificar acesso a
  recursos que cruzam páginas, SRAM e áudio no X7 antes de consolidar a
  imagem única.

O próximo marco jogável deve ser E2M1 com seus materiais e objetos
originais. Isso testa a troca de banco e a extensão da tabela de objetos
em uma fase que cabe no formato de setores atual.

## Comandos

```sh
python3 scripts/lab/audit_r128_ultimate.py /path/to/doom.wad --shareware /path/to/doom1.wad
python3 scripts/lab/convert_r128_ultimate_e1.py /path/to/doom.wad --shareware /path/to/doom1.wad --out /private/path/ultimate-e1.wad
python3 scripts/lab/r89_align_maps.py /private/path/ultimate-e1.wad
python3 scripts/lab/r128_stairs.py /private/path/ultimate-e1.wad
```
