# Mega EverDrive X7 in-game menu (Down+Start) — aplicado ao Manifold (r087)

Base: handoffs EVERDRIVE-X7-INGAME-MENU-WERK.md e HANDOFF_Mega_EverDrive_X7_Menu_InGame_Generico.md
(solução validada no Tile Palette Studio: V-Int ativa + polling do pad nas duas fases de TH a cada vblank).

## Auditoria
- Jogo (mapas SGDK): V-Int ligada e SR aberto; `JOY_update()` só roda em `update_joy()` uma vez por quadro
  renderizado (2–8 FPS em combate) → o X7 não via o ciclo TH=0/TH=1 a cada vblank.
- Menu multimap (`menu.c`): rodava com SR=0x2700 e V-Int desligada (reg1=0x44), lendo o pad por polling do flag de vblank.

## Correção (menor possível; `_VINT`, task_lock, callbacks SGDK intactos)
- `crt0.s`, vetor nível 6 (`stub30`): a cada vblank lê TH=0 e TH=1 (2 nops entre escrita e leitura), restaura o latch de TH
  (não atrapalha um `JOY_update`/`pad_read` interrompido) e então: na fase de menu (flag `0xFF0034 == 'MVIN'`) dá `rte`;
  na fase de jogo salta para o `_VINT` do mapa como antes (frame de exceção intacto, d0/d1 restaurados).
- `menu.c`: reg1 0x44→0x64 (V-Int ligada), flag `0xFF0034` ligada + `SR=0x2000` após o setup do VDP;
  `launch()` mascara o SR (0x2700), zera a flag e só então desliga o VDP e salta para o mapa.
- Custo: ~100 ciclos por vblank.

## Verificado (MAME, ROM só com o menu)
`stub30` executa 1× por vblank (30 em 30 quadros) e retorna por `rte`. A ROM completa (SSF) não roda no MAME,
e o X7 físico não é validável em emulador: **só marcar como resolvido após Baixo+Start no X7 real**
(menu, Save/Load State, retorno ao jogo).
