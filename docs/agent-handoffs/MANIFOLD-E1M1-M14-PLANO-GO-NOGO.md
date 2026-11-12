# M14: E1M1 jogável no Manifold, com go/no-go

Decisão do usuário (12/11/2026): a ideia original era o Manifold superar o desempenho do Doom original, e isso não aconteceu. Tentamos uma E1M1 inteira funcional; se o resultado for ruim, abandonamos o Manifold.

**Prazo:** 3 dias, até 15/11/2026 (~01h, horário de Brasília), para uma E1M1 jogável e a decisão final.

## Escopo de "funcional"
Começa no jogo (START), percorre o mapa até a saída, com portas, objetos estáticos, pickups, inimigos com IA básica, arma e HUD; sem crash em uma partida completa; sem buracos de render nas áreas já identificadas.

## Critérios de decisão
1. Desempenho: mesma rota fixa (ou DEMO3), mesmo hardware, comparado ao port de Doom atual. FPS abaixo do port nessa rota = abandonar.
2. Checkpoint antes dos inimigos: medir FPS com sprites, portas e pickups. Se já estiver muito abaixo do port, decidir ali.
3. Só correções de defeito no renderer; nada de visão à distância que aumente CPU.

## Referência (não comparável diretamente)
Série R20 do port: ~11 FPS calculados na DEMO3 (2134 frames). Relatos de console do Manifold: ~3 a 5 FPS. Será remedido na mesma rota.

## Fases
0. Linha de base (controle E1M1/E1M9 sem objetos).
1. Porte manual de objetos estáticos (m12_objects.py, raster de sprites, MANIFOLD_OBJECTS), SHA igual com flag desligada.
2. Portas, pickups, crash do botão A.
3. Checkpoint de FPS (go/no-go parcial).
4. Inimigos, grades, ROM final de teste jogável (START entra no jogo).

## Linha de base (Fase 0, MAME headless, 120 s emulados, rota "tour" fixa, controle sem objetos)
Script: `experiments/DOOM_Manifold_E1M1/tools/m14/run_fps.sh` (lê `cur_frame`, incrementado por quadro renderizado).
- E1M1 (tour_ctrl): 6,87 FPS
- E1M9 (e1m9_tourctl): 6,73 FPS
O MAME não reproduz o clock do console (o usuário vê ~3 a 5 FPS), então vale só como comparação relativa entre builds.

## Fase 1 (porte de objetos estáticos), 12/11
- `m12_objects.py` e `m12_pickups.py` trazidos do branch do Werk (`exp-manifold-m12-objects-pickups-approved`); raster de sprites e hook `MANIFOLD_OBJECTS=1` reaplicados à mão em `stage_rom.py`; parâmetro `things` em `emit_portal_map.py`. Pickups ainda não ligados (fase 2).
- E1M9: 82 THINGS inseridos (3 ambíguos descartados). Compila e roda 120 s no MAME sem crash.
- FPS MAME, E1M9 tour: objetos desligados 7,03; ligados 6,92 (~1,6% de custo).
- Não verificado: SHA idêntico ao controle com a flag desligada (as flags de build do controle antigo diferem das desta rodada). Não verificado: aparência dos sprites; os 4 snapshots do tour não mostram um objeto claro.

## Resultado de console, 12/11 (01h)
- `claudio-m14-e1m1-objects-h40.bin` (BSP=1 + objetos): objetos corretos (posição e tamanho), mas paredes azuis (colunas abertas pintadas por `manifold_fill_open`).
- `claudio-m14-e1m1-objects-nobsp-h40.bin` (BSP=0 + objetos): **nenhum azul, objetos presentes; "a melhor até agora"** (usuário).
- FPS MAME, tour 120 s: BSP=1 6,71; BSP=0 6,67. Sem diferença de custo.
- Decisão: a base do M14 passa a ser BSP=0. A ser verificado: se o pisca de paredes ao se aproximar volta sem BSP.
- Hipótese ainda não confirmada: o azul vem do culling lateral do modo BSP (rnx/lnx), não dos objetos.

## Fase 2 (12/11, testes automatizados no MAME headless; usuário ausente)
Base: BSP=0 + `MANIFOLD_OBJECTS=1 MANIFOLD_PICKUPS=1 MANIFOLD_DOORS=1`. ROM: `claudio-m14-e1m1-full-h40.bin` (tag CLAUDIO_M14_FULL). Código portado do branch do Werk à mão: modo `doors` em `emit_portal_map.py` (setores 4, 68, 76, 81), `m12_tune_doors`, hook de pickups. Scripts em `tools/m14/test_*.lua`.

| Teste | Resultado |
|---|---|
| Botão A seguro por 100 quadros (com PCM do shotgun e `wake_enemies`, sem o probe do Werk) | **Sem crash**: `cur_frame` continua subindo (13→40 entre 250 e 700 VBlanks), nas variantes doors e full. Não reproduz o crash relatado pelo Werk; pode depender do console real. |
| Pickup de munição (teleporte ao THING em 2736,-4160) | **OK**: HUD ammo 50 → 60. Health/armor não testados (health já está em 100, a regra recusa). |
| Portas por B perto da parede-portal | **OK nas 4**: setor 4 abre até 2304 (alvo 72·16·2); 81 e 76 sobem; 68 abre por uma das duas paredes (160) e não pela outra (159), que pode estar a mais de MIN_ACTIVATE_DIST. |
| Tour de 180 s emulados | **Estável**: 1336 quadros, 7,51 FPS médios (rota/duração diferentes das medições anteriores, não comparável 1:1). |

Não testado: inimigos (não existem), colisão com objetos, fechamento automático das portas, pisca de parede ao se aproximar (confirmado só pelo usuário no console), crash do A no console real.

## Console 12/11 01h46: `claudio-m14-e1m1-full-h40.bin`
Usuário: "está funcionando; câmera ainda alta, mas tudo acontece corretamente; a arma ainda é a do Manifold, que é até maior". FPS visto no console: 4,1 (screenshot). Tiles pretas no HUD ainda presentes (canto esquerdo da barra, entre os números).
- Câmera: `MANIFOLD_EYE=N` (padrão 64, unidades de altura dobradas) em `stage_rom.py`. Variantes 48 e 36 geradas para escolha no console.
- Pendente: arma do Doom no lugar da do Manifold; tiles pretas do HUD (Werk).

## Texturas horizontalmente comprimidas (12/11, 01h54)
Usuário: eye48 é boa (agora o padrão); texturas "um pouco horizontalmente comprimidas"; a textura da porta deveria ser única, mas repete nas laterais.
- Causa geral medida: 192 de 444 linedefs ficam fragmentadas pela divisão em células (457 paredes). Cada pedaço recebia `reps=max(1,round(comprimento/largura))`, refazendo a textura do zero (comprime/repete). As faces das portas (128 de comprimento, linedefs 151/152) NÃO estão fragmentadas; a repetição lateral da porta tem outra causa ainda não confirmada.
- Correção opt-in `MANIFOLD_TEX_U=1`: o emitter calcula U inicial e final por parede (distância na linedef + xoff, como o Doom); `draw.c` mapeia base + fração·extensão; patch em `draw.c`, `portal.c`, `bunch_render.c`, `texture.h`, `portal_map.h`.
- `MANIFOLD_TEX_HSTRETCH` (padrão 1,0 = 1 texel por unidade do Doom). Com altura dobrada, 2,0 restaura a proporção do Doom. ROMs: `...eye48-u1-h40.bin` e `...eye48-u2-h40.bin`.
- MAME: u1 idêntico ao anterior nas paredes inteiras (esperado); u2 mais largo. Sem crash (botão A, 700 VBlanks). Não verificado no console. Pedido ao usuário: foto do Doom original da mesma cena.

## Todos os objetos não-monstros (12/11, 02h)
Pedido do usuário: converter todos os objetos. `m12_objects.py` agora cobre 21 sprites distintos (candelabro 35, coluna tech 48, poça 24, restos 10/12/15 [10 e 12 compartilham PLAYW0], chaingun, lança-foguetes, cartuchos, armaduras verde/azul, caixas de foguetes/balas/cartuchos), com caixa de exibição = patch × proporção do barril aprovado (largura ×1,39, altura ×1,75). Monstros (9, 3001, 3004) NÃO são convertidos (fase de inimigos). E1M1: 85 THINGS inseridos, 1 ambíguo descartado (2049).
- `m12_pickups.py`: novos pickups (cartuchos, caixas, armaduras 100/200, chaingun, lança-foguetes).
- MAME: caixa de balas 50→100, armadura verde 0→100, azul 100→200, caixa de cartuchos 0→20; candelabro visível; botão A sem crash (700 VBlanks).
- ROM: `claudio-m14-e1m1-allobj-eye48-u1-h40.bin` (TEX_U=1, HSTRETCH=1.0, eye48).

## Decisões do usuário, 12/11 02h04
- Câmera: `MANIFOLD_EYE=48` aprovada.
- Texturas: **u1 aprovada** (`MANIFOLD_TEX_U=1`, `MANIFOLD_TEX_HSTRETCH=1.0`, 1 texel por unidade do Doom). A porta ficou parecida com a referência do Doom (BlastEm: 10 FPS no jogo, emulador a 59,8).
- Base de build do M14: BSP=0, OBJECTS=1, PICKUPS=1, DOORS=1, EYE=48, TEX_U=1.
- Pendentes: arma do Doom no lugar da do Manifold; tiles pretas do HUD (Werk); inimigos; checkpoint de FPS no console.

## Arma do Doom e possível causa do crash do botão A (12/11, 02h)
- Usuário: texturas na resolução atual são aceitáveis ("já é reconhecível"); o letreiro EXIT ilegível é esperado (32 colunas × 64 linhas, 16 cores; subir para 64 colunas exige mexer na asm do desenhador). Não será alterado agora.
- `MANIFOLD_WEAPON=pistol` (`m14_weapon` em `stage_rom.py`): substitui `SHOTGUN.png`/`SHOTGUN_RELOAD.png` pela pistola do Doom (PISGA0 parada; PISGB0 + flash PISFA0 ao atirar), paleta de 9 cores (índices 1..9; 10..15 ficam pretos, pois as margens da tela usam a PAL0 — com 15 cores elas ficaram marrons).
- **Causa provável do crash do A no console:** `anim_table` pede `frame_idx=1` de `shotgun_reload`, mas o recurso compilado tem 1 quadro (`shotgun_reload_animation0_frames` tem uma entrada). `frames[1]` lê um ponteiro inválido (~0x0100xxxx): sem erro no MAME, mas deve gerar bus/address error em hardware real. Corrigido para `frame_idx=0` neste build. NÃO confirmado no console.
- Não verificado: aparência da pistola. O MAME headless não desenha os sprites da arma (nem nos builds antigos) e o BlastEm não renderiza sob Xvfb aqui. ROM: `claudio-m14-e1m1-pistol-allobj-eye48-u1-h40.bin`.

## Botão de fim de fase repetido — causa e correção (12/11, 02h)
- Causa: `true_cells.merge_collinear` funde arestas sólidas colineares de linedefs diferentes. No quarto de saída a aresta x=2912, y -4840..-4672 (168 un.) junta o botão (linedef 330, SW1STRTN, 64 un.) com paredes vizinhas; `assign_wall_textures` escolhe UMA textura (a do botão) para a aresta inteira, que se repete ~2,6 vezes. Existe desde o início das versões.
- Correção: `MANIFOLD_SPLIT_LINES=1` (padrão) em `assign_wall_textures` divide paredes sólidas nos vértices do Doom. 37 divisões, 1025 → 1062 paredes (limite 2048). Verificado: aresta agora (2912,-4800→-4736) com a textura do botão, u 0..256 (uma vez); captura no MAME mostra o botão vermelho uma única vez. FPS no MAME na mesma rota: 3,47 antes e depois.
- Paletas: a imagem 3D usa uma única paleta de 15 cores + preto, compartilhada por paredes, pisos e sprites. Paleta separada para objetos exigiria desenhar os objetos em tiles com outra linha de paleta (não cabe no desenhador atual). Experimento `MANIFOLD_PAL_SPRITES=N` (sprites votam na paleta): erro médio de cor dos sprites 45,2 → 43,7 e das paredes 31,0 → 30,2; ganho desprezível, mantido desligado.

## Grades (12/11, 03h)
- Referência Doom: as grades são as linedefs 298–303 (mid-textures BRNBIGL/C/R, sector 72, flags 0x5 = bloqueante + two-sided): cerca oeste x=2888 e leste x=3128, y -4352..-4160 (192 un. cada), piso -24, teto 104 (128 un. = altura da textura). A aresta tem o mesmo setor dos dois lados, então não entrava como parede nem na colisão. (A linedef 464, BROWNGRN, é outro caso: não tratada.)
- Visual: o desenhador não tem parede com transparência; as grades viram 12 sprites de 32 un. (6 por cerca; BRNBIG L, C0..C3, R), com os vãos diagonais mascarados (texel None), via `m12_objects.py` (tipos 9001..9006; caixa 44×224 = 32×1,39 e 128×1,75). Limitação: sprites são billboards (sempre de frente para a câmera) — de ângulos oblíquos a cerca não fica alinhada ao plano. Comparação original × convertida: `m14-grate-original-vs-convertida.png`.
- Colisão: `emit_portal_map.blocking_segments` inclui essas linedefs (MANIFOLD_GRATES=1). Só isso não bastava: o passo por quadro (~36–47 un.) é maior que a margem (2×16) e o jogador pulava a linha. `stage_rom.py` ganhou teste de passo varrido (`manifold_step_crosses`) em `manifold_radius_blocked`, valendo para todas as paredes sólidas. Testado no MAME: bloqueado nas 4 abordagens (dentro→oeste, dentro→leste, fora-oeste→leste, fora-leste→oeste); controle sem a correção atravessava (x 2990→2713). Portas (test_doors_b) e FPS (3,47) sem regressão.
- Nota de teste: o endereço de `cur_player_pos` muda a cada ROM (nm); angulação: 0=+x, 256=+y, 512=-x, 768=-y.

## Tela quebrando com o tempo — causa provável e correção (12/11, 03h)
- Sintoma (BlastEm, várias ROMs, jogador parado): depois de alguns minutos a VRAM/nametable/HUD viram lixo e não se recuperam. Não era a grade.
- Reproduzido no MAME: ROM sem correção (swfix) quebra entre 12000 e 24000 quadros (≈7 min emulados parada) e permanece quebrada; a mesma ROM com `MANIFOLD_VDP_SAFE=1` ficou limpa até 48000 quadros (≈13 min).
- Causa provável: um comando do VDP são duas palavras na porta de controle; o H-Int (registradores, todo quadro) e o V-Int (fila de DMA) escrevem nessa porta. Se uma interrupção cai entre as duas palavras de uma escrita do laço principal (texto do FPS `manifold_hud_text`, troca do rosto do HUD, barra de status, atualização do céu), o VDP usa endereço errado e grava tiles/nametable no lugar errado. A janela é minúscula, por isso demora minutos. O próprio SGDK avisa (sys.h) que acesso ao VDP fora de interrupção precisa de SYS_disableInts/SYS_enableInts.
- Correção: `m14_vdp_safe` (flag `MANIFOLD_VDP_SAFE=1`) embrulha cada `VDP_setTileMapXY/DataRect`, `VDP_clearTileMapRect`, `VDP_loadTileData` e `SKY_CLEAR_BORDERS` de game.c, doom_statusbar.c e manifold_sky.c em SYS_disableInts/enableInts (16 pontos), instrução a instrução, para mascarar só por algumas centenas de ciclos. O `MANIFOLD_VDP_ATOMIC` do Werk só cobria a inicialização.
- Ainda NÃO coberto: `VDP_loadTileSet` do sprite da arma (DMA_QUEUE, enfileirado), paleta (DMA), `VDP_updateSprites` (fila). Se a quebra voltar, procurar aí.
- Monstros estáticos (sem IA) nas posições do mapa: zumbi (3004), sargento (9), diabrete (3001), sprite frontal A1, caixa pelo mesmo fator da barrica (patch × 1,39 / 1,75); decorações (sem colisão). 29 THINGS (125 de 126 do limite).
- Flags de bisseção das grades: `MANIFOLD_GRATE_SPRITES=0`, `MANIFOLD_SWEPT=0`.

## Regra de identificação das ROMs de teste (12/11, 09h48, pedido do usuário)
- Toda ROM nova leva nome/finalidade no cabeçalho do cartucho (BlastEm mostra na janela) e abre numa tela preta com a fonte padrão do SGDK: nome da ROM, o que ela testa e "PRESS START OR WAIT 15 SECONDS" (contagem regressiva; START ou 15 s entram no jogo).
- Implementação: `m14_identity` em `stage_rom.py`, variáveis `MANIFOLD_ROM_NAME` (≤48 caracteres, cabeçalho e título) e `MANIFOLD_ROM_TEST` (linhas separadas por `|`, ≤38 caracteres, ASCII; `?` e acentos são removidos). Gera `src/rom_header.c` próprio (o makefile só copia o do SGDK se ele não existir) e `m14_splash()` chamada logo após `VDP_init()` em `main.c`. Sem `MANIFOLD_ROM_NAME` nada muda.
- Verificado no MAME: cabeçalho, tela de abertura, START entra no jogo e a espera de 15 s também (tela de 850 quadros = abertura "STARTING IN 02", 1000 quadros = jogo).
- Helper de build local: `tools/m14/build_local.sh NAME env...`.
- Diagnóstico NOHUD: ROMs A (sem vdpsafe) e B (vdpsafe só no céu).
