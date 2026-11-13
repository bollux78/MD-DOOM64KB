# Manifold M14: todas as armas da shareware (handoff para o Werk)

Autor: Claude. Destino: Werk. Data: 13/11. Branch `exp-manifold-m14-e1m1`. Estado de partida: ROM de 9 fases unificada (12 MB), monstros inativos de todos os tipos, hoje uma única arma (pistola).

## Decisões do usuário (13/11)
- Efeitos sonoros podem cair para **6 ou 8 kHz** (hoje 14 kHz).
- Motosserra com **apenas 2 sons**: ativa e inativa.
- Foguete como **raio instantâneo** (hitscan) com explosão e dano em área ao redor do ponto de impacto, sem projétil.
- Shotgun com **3 tiros** (pellets) por disparo.
- Quando houver monstros ativos, START vira **pausa + menu dentro do jogo** (RAM preservada; SRAM só depois, se desejado).

## Armas (shareware E1)
Soco, pistola, shotgun, chaingun, lança-foguetes, motosserra. Sem plasma, BFG, super shotgun. Pickups por THING: 2001 shotgun, 2002 chaingun, 2003 lança-foguetes, 2005 motosserra, 2007 clip, 2008 cartuchos, 2010 foguete, 2046 caixa de foguetes, 2048 caixa de balas, 2049 caixa de cartuchos.

## Estado atual (código)
- `manifold-up/src/weapon_sprites.c`: 2 sprites de 64x64 (`SHOTGUN`, `SHOTGUN_RELOAD`), `anim_table` de 3 entradas, DMA dos tiles na troca de quadro. Paleta 0 compartilhada com o HUD: só os índices 1..9 são da arma, 10..15 devem ficar pretos.
- `stage_rom.py: m14_weapon` troca os PNGs pela pistola do WAD (9 cores, índice 0 transparente); `m14_weapon_fix` corrige a tabela de animação e o som do tiro.
- `game.c`: `shooting` (contador), `set_weapon_anim(SHOTGUN_RELOAD_ANIM, DMA_QUEUE)`; botão de tiro A ou C.
- `sfx.c`: 3 canais PCM do XGM (CH2..CH4), prioridade por canal; ids de SFX em `sfx.h`.
- Dano: `m14_monsters` aplica 5/10/15 ao objeto sob a mira.
- HUD: `dhud_state.ammo[0]` único.

## Defeitos abertos que bloqueiam (resolver primeiro)
1. Ruído no primeiro tiro.
2. Animação de tiro invisível (às vezes).
Ambos passam pelo mesmo caminho (`step_weapon_animation` / DMA_QUEUE) que todas as armas vão usar.

## Plano por etapas (cada uma gera uma ROM jogável; testar no BlastEm antes do console)
1. **Corrigir os dois defeitos.** Teste: 20 tiros seguidos na E1M1; nenhum ruído, animação sempre visível.
2. **Infra de várias armas.** `weapon_id` atual, troca no botão B (cicla só entre as armas possuídas), tabela por arma: sprites (idle, quadros de tiro), paleta de 9 cores regravada na troca, cadência, dano, tipo de munição, som. Pickups de armas. Munição em 3 tipos (balas, cartuchos, foguetes) no HUD, mostrador ARMS aceso conforme as armas possuídas.
3. **Shotgun (3 pellets, bombeada) e chaingun** (tiro rápido alternando 2 quadros), soco (melee curto).
4. **Motosserra** (melee, 2 sons: ativa/inativa) e **lança-foguetes** (raio instantâneo + explosão; dano em área = distância ao ponto de impacto sobre os objetos da lista, com atenuação linear; sprite de explosão como DECORATION temporário).
5. **Sons dos monstros** (sight, pain, morte, ataque) quando os monstros forem ativos.

## Orçamento
- Sprites: ~4 KB por quadro de 64x64, ~60 KB para tudo; irrelevante.
- Sons a 8 kHz: armas ~40 KB, monstros ~65 KB (total ~100 KB; a 6 kHz ~75 KB). O bloco comum tem folga de ~94 KB (2.985.984 de 3.080.192). Se estourar, mover `MAP_ORG` de 0x300000 para 0x380000 (custa 1 banco; teto do SSF2 é 15 MB, hoje 12 MB).
- XGM: 3 canais PCM; chaingun e motosserra disputam canais, usar prioridade (tiro do jogador alta).
- RAM: quase toda em heap (~1,5 KB livres de pilha além da margem). Estado das armas deve ser poucos bytes.
- CPU: 7–18 FPS hoje; o foguete (loop de distância sobre ≤126 objetos) é o único custo novo relevante.

## Restrições do layout (lembrete)
O bloco comum precisa ser byte a byte idêntico nas 9 fases (`compose.py` aborta se diferir): tudo o que for comum (sprites de arma, PCM, código) entra no bloco comum, e o que muda por fase fica no `.mapobjs`.
