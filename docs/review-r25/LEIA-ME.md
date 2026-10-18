# R25 — músicas do episódio completo

Base: R24, com mapas E1M1–E1M9 e seletor inicial de fases.

- `doom-md-r25-episode-play.bin`: episódio 8×8, trilha completa.
- `doom-md-r25-episode-p4.bin`: episódio 4×4, trilha completa.
- `doom-md-r25-episode-perf.bin`: timedemo DEMO3 8×8, trilha por mapa.
- `doom-md-r25-control.bin`: controle timedemo 8×8 anterior, música E1M1 anterior.
- `doom-md-r25-play-control.bin`: controle jogável 8×8 anterior.

A confirma a fase e abre a seleção de dificuldade. Cada mapa E1M1–E1M9
recebe sua faixa. Abertura/menu usam Intro; placar entre fases usa Inter;
final do episódio usa End (Victory). O loop solicitado pelo jogo é respeitado.
Bunny pertence ao final de outro episódio e não é usado no E1.

Fonte: DOOM 32X: Resurrection, revisão
55bf94b43a039ae0a0d2f09ad9bc23bea5963714.
https://github.com/viciious/d32xr/tree/55bf94b43a039ae0a0d2f09ad9bc23bea5963714/content/files/VGM
Arranjos VGM: Spoony Bard. Composição original: Robert Prince.
Os direitos e créditos originais são preservados.

## ROM e SRAM

A trilha XGM completa acrescenta aproximadamente 1,2 MB; as ROMs musicais
ultrapassam 2 MiB. Código, constantes de interrupção e todas as músicas
ficam abaixo de 2 MiB. O WAD é colocado depois das músicas.
SRAM continua sendo memória de trabalho normal do jogo. Cada acesso aos
heads, estado de mapa, contatos e cache abre a janela SRAM e restaura ROM
antes de retornar. Nenhum buffer persistente de música é alocado na RAM 68k.
O cache copia apenas entre SRAM e o buffer RAM de 128 bytes já existente.
O VInt/Z80 lê músicas abaixo de 2 MiB mesmo enquanto a janela está aberta.
O layout é conferido no ELF de cada build; ROM total limitada a 4 MiB.

## Testes de uso

1. Conferir abertura, menu e início de cada fase pelo seletor.
2. Deixar uma música completar o loop e conferir efeitos sonoros simultâneos.
3. Concluir E1M1: Inter no placar, E1M2 no próximo mapa.
4. Conferir vitória em E1M8.
5. Comparar timedemo com controle e testar em hardware a 7,67 MHz.

O exame de formato/conversão e o teste CPU não substituem ouvir as músicas
nem validar o mapper do cartucho no hardware. As ROMs de controle preservam
a arquitetura anterior para comparação.
