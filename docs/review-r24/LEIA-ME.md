# R24: episódio 1 completo e seletor de fases

- episode-play: campanha jogável 8x8, seletor E1M1..E1M9 e dificuldade.
- episode-p4: mesma campanha e seleção em 4x4 real, 76x44 amostras.
- episode-perf: timedemo 8x8 com a arquitetura do episódio completo.
- control / play-control: os dois controles 8x8 da base anterior, WAD antigo.
- cpu-probe: teste interno, não usar no console.

O seletor abre ao iniciar. Também existe Select Level no menu principal.
New Game começa em E1M1. A sequência normal segue E1M1..E1M8; saída
secreta de E1M3 leva a E1M9, e E1M9 retorna a E1M4. E1M8 mantém o final.
E1M1/E1M8 preservam os lumps da base validada; os demais são conversões
reais do Doom shareware 1.9. Normais de paredes incluem a correção R23b.

Para caber, itens e ornamentos não sólidos, sem IA/ações de estado, usam
registros na ROM. Animações são calculadas pela mesma sequência de estados,
com a fase inicial aleatória preservada. Coleta usa P_TouchSpecialThing,
com um bit de remoção por objeto. Inimigos, barris, decoração sólida e
teleport destinations mantêm objetos completos, física e thinkers normais.
Sprites fixos entram no mesmo projetor e clipping dos sprites dinâmicos.
Contatos na SRAM usam índices compactos (12 bytes por nó), com as mesmas
listas em dois sentidos. A capacidade é calculada por mapa e monitorada.

SRAM permanece obrigatória. Música é a E1M1 já existente em todas as fases;
não foram convertidas as outras músicas. Pisos/tetos mantêm cores planas.
Esta leva requer teste visual e jogável de cada mapa, portas, chaves,
coleta, teleportes, saída normal, secreta e final.

Validação do build f57aff64425d534ff0fe6faf6f364763fc77f3f8:
- CI concluiu; ROMs do episódio têm 2097152 bytes, dentro da janela de SRAM.
- CPU MC68000: nove mapas em médio e difícil; dez alocações temporárias por
  carga, remoção e verificação do heap; coleta real de munição da ROM passou.
- Callbacks compilados do menu selecionam corretamente as nove fases e
  a dificuldade média. Rótulos cabem nas38 colunas. A confirma.
- Ainda falta sua validação visual/jogável, incluindo saídas e final.
- Valores de memória no JSON são da marca DONE da carga, antes dos efeitos.

Comece por doom-md-r24-episode-play.bin (8x8) ou episode-p4.bin (4x4).
Os controles usam o WAD antigo e não têm o seletor do episódio completo.
