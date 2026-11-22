# Tamanho das paletas por fase — medição sem compilar ROM

A pedido do usuário, não executar build, linker nem CI até ele dizer **compile**. A C5 publicada permanece a ROM de referência.

Foram reconvertidos offline os nove mapas shareware, usando uma paleta própria de16 cores ajustada aos assets e níveis de iluminação de cada mapa. O cálculo reproduz o empacotamento/deduplicação atual e confere os tamanhos da C5. Conversores Python e de música foram usados apenas para obter os dados finais; nenhuma ROM nova foi compilada.

| Dados | C5 compartilhada | Por fase | Aumento |
|---|---:|---:|---:|
| Texturas e ponteiros de colunas |1.589.616|3.273.184|1.683.568 bytes|
| Sprites do cenário |243.808|989.542|745.734 bytes|
| Céu |9.728|58.368|48.640 bytes|
| Paletas CRAM |32|288|256 bytes|
| **Total** |||**2.478.198 bytes (2,363 MiB)**|

A C5 usa4.166.794 bytes antes do preenchimento e é distribuída em4.194.304 bytes (4MiB). Somar somente os assets medidos leva a6.644.992 bytes de conteúdo, ou aproximadamente6.684.672 bytes (6,375MiB) após o preenchimento de128KiB usado no projeto. É estimativa de arquivo, não resultado de linker. Faltam código, alinhamento, ponteiros e adaptação ao mapper.

A música End convertida para XGM2 ocupa32.344 bytes. Somada ao cálculo anterior, conteúdo estimado6.677.336 bytes: ainda próximo do mesmo bloco de6,375MiB, mas com pouca margem para as demais alterações. A paleta por fase elimina bastante compartilhamento, principalmente de sprites. Não cabe em4MiB com esta organização; requer mapper/organização de bancos ou outra estratégia.

Dithering do chão final mantém64 tiles (2.048 bytes). Um ensaio de dithering nas armas do WAD acrescentou2.208 bytes, mas NÃO é mais a proposta: o usuário autorizou usar a folha guns_optimized_pal.png, cujo enquadramento/quadros precisam fechar antes de calcular a troca definitiva. Não somar o ensaio às armas novas.

Pendências C6: IDKFA com munição infinita enquanto ativo; música End; chão dither; armas fornecidas pelo usuário e alinhamento/bob; corrigir flashes pretos da C5. A C5 faz unpack na interrupção e esconde peças durante transferências parciais; investigar antes de compilar. Clarão no viewport permitido somente para tiros do jogador e explosões de barril, jamais para tiros de inimigos; desacoplar da função de som compartilhada.

Scripts refletem o layout desta sessão: executar a partir da pasta que contém dread-gameplay/, dread-gameplay-cache/, pixel4-control/ e r128-local-sgdk/. São ferramentas de medição de dados; não invocam make/gcc/linker nem geram ROM.
