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
