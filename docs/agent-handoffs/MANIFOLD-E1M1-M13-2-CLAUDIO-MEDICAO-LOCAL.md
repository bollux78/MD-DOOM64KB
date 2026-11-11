# MANIFOLD E1M1 — M13.2 all-leaves: medição local do Cláudio (11/11/2026, tarde)

Responde a `MANIFOLD-E1M1-M13-2-ALL-LEAVES-RESULTADO-CLAUDIO.md` e corrige `MANIFOLD-E1M1-M13-2-CLAUDIO-RESPOSTA-INICIAL.md`.

**Correção:** na resposta inicial eu escrevi que os buracos não vinham da seleção de folhas pelo BSP. A medição abaixo mostra o contrário: o bbox culling em `bsp_box_visible` é a causa principal dos buracos. Remover esse culling elimina quase todos eles.

Ambiente: MAME headless, ROMs H40 locais com as flags do workflow M13 (`MANIFOLD_BSP=1`, `MANIFOLD_BSP_ALL_LEAVES` 0 ou 1), commit `b6fe52a` do upstream, branch `exp-manifold-m12-claudio` em `83ff9c3`. Contadores lidos da RAM a cada quadro por `counters.lua`.

## 1. Resultados

| Medida | Controle (culling) | All-leaves |
|---|---|---|
| Quadros com colunas abertas (buraco azul), passeio de 7191 quadros | 3857 (54 %) | 379 (5 %) |
| Média de linhas abertas por quadro | 984 | 3,1 |
| Máximo de linhas abertas num quadro | 7575 | 207 |
| Média de células BSP visitadas por quadro | 7,0 | 42,6 |
| Máximo de células visitadas por quadro | 52 | 236 |

Câmeras fixas do M11 (`MANIFOLD_CAMERAS=fixed`, 2397 quadros): controle com 1745 quadros de buraco e média de 964 linhas; all-leaves com zero quadros de buraco e 61 células por quadro em média.

Os blocos azul-escuros são exatamente as linhas que `manifold_fill_open` pinta com `0x1111` no fim do quadro, por não terem sido fechadas por nenhuma parede. Como o contador `manifold_filled_rows` zera com all-leaves na maior parte do passeio, o culling é o mecanismo principal.

## 2. Buracos residuais no all-leaves

Os 379 quadros com resíduo ocorrem em um conjunto pequeno de posições, todas em área externa, com y entre cerca de −3150 e −4256 (unidades de mapa):

- (−192, −3336), (408, −3232), (240, −3232), (3008, −4256), (1360, −3152), (288, −3360), (2422, −3697), (3493, −3424)

A posição fixa E0 do M11, (1781, −3691), está nessa mesma faixa. Ou seja, o resíduo está na área externa que o usuário reportou.

## 3. Hipóteses descartadas

- **Guarda de pilha em `visit_graph`** (`manifold_dbg[7]`): zero células descartadas em ambos os builds durante todo o passeio. Não é a causa.
- **Overflow de `s16` na projeção do bbox:** não se confirmou para as coordenadas acima.

## 4. Custo

Visitar todas as folhas multiplica as células por ~6 (7,0 → 42,6). O FPS do console cai na mesma proporção, mas não medi FPS real aqui; a MAME sem limite de velocidade não reproduz o FPS do hardware.

## 5. Próximo passo

1. Nas posições da seção 2, registrar quais paredes foram visitadas e quais colunas elas fecharam, para as colunas que ficaram abertas. Verificar se são paredes que nunca entram no traversal (folha não alcançada pelos portais) ou paredes que entram mas não cobrem a coluna.
2. Medir se o resíduo é de parede longa passando do `BSP_FAR` (paredes de bordas do mapa ficam fora da distância) ou de projeção perto do plano de recorte.
3. Só depois disso propor uma seleção de folhas que mantenha o resultado sem as 42 células por quadro.

Scripts usados em `experiments/DOOM_Manifold_E1M1/tools/m13/` (`build_ab.sh` gera os dois ROMs; `counters.lua` grava `quadro, linhas_abertas, dbg[0], dbg[7], células` por quadro).
