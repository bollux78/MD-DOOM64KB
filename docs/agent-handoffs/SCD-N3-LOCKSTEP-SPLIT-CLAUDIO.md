# SCD N3: lockstep + tela dividida (Cláudio)

Branch `exp-werk-scd-subport-s1s2`, pasta `experiments/DOOM_SCD_SubPort/n3`, workflow `scd-subport-n3.yml`.

## Ideia
- O MD continua sendo a R128 inteira (input, menus, HUD, som, apresentação).
- O sub do Sega CD roda **a mesma lógica** em lockstep: recebe, a cada troca, os `ticcmd` que o MD acabou de simular (o comando realmente usado, então demos também servem) e um snapshot na carga de cada nível (`player_t`, mapa, skill, `prndindex`, gametic).
- Renderização em **tela dividida, do mesmo estado, em paralelo**:
  - troca A (início do `D_Display`): o MD manda os tics; o sub roda os tics e renderiza as colunas `[split, 76)`;
  - o MD renderiza `[0, split)` ao mesmo tempo;
  - troca B: o MD recebe o frame do sub e junta só as colunas do sub (bytes ímpares do Pair-V).
- Colunas fora da janela viram `solidcol` antes do BSP; sprites são presos à janela.
- O `split` se ajusta sozinho conforme quem espera.
- Os dois renderizadores são o código da R128 (drawers Pair-V em asm, perfil de cor 1, crop R57).
- Desync (x/y/ângulo/gametic diferem): o sub é descartado até o próximo nível e o MD renderiza sozinho.
- Sem Sega CD, erro, timeout ou mapa ≠ E1M1: R128 pura.

## Resultados BlastEm (E1M1, mesmo roteiro de movimento/tiro, ~40 s de jogo)

| ROM | FPS |
|---|---|
| R128 só MD (mesma ROM, N3 desligado) | 3,80 |
| N3 split | **5,68** (+49%) |
| spawn parado: MD vs N3 split | 4,65 → 6,46 |

- 0 desyncs; 100% dos frames com metade do sub.
- Verificação (frame juntado vs render completo do MD do mesmo estado): ~4–13 bytes diferentes de 1672 por frame; 40% idênticos.

## Correções importantes no caminho
- O código de som do MD (Z80/YM) escrevia em endereços que no sub caem na PRG-RAM baixa e destruía os vetores. Correções:
  - som vira no-op no sub;
  - PRG-RAM do código fica protegida (WP 0xFF);
  - vetores autodescritivos (`n2/sub_boot_n2.s`).
- Corrida no servidor MD: o loop chamava `SCD_MdServeOnce` às cegas e respondia um FRAME antes de existir estado. Também passou a aceitar uma requisição mais nova como prova de conclusão (corrida ACK/DONE).
- Cache do WAD no sub:
  - escopo de nível (marca pós-init);
  - sprites e patches de parede num anel de 28 KB;
  - `W_ReadLumpByNum` lê direto, sem cache.

## Limites atuais
- Só E1M1 é acelerado: o subconjunto R84 cabe na PRG-RAM.
  - Próximo passo: subconjunto por mapa, enviado pelo MD na carga do nível.
  - Memória do sub: `_end` ≈ 0x7D200 de 0x7F000.
- A lógica do MD (≈35 ms/frame movendo) ainda não sobrepõe o render do sub. Próximo ganho: reordenar o loop.
- Console real ainda não testado.
