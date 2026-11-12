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
