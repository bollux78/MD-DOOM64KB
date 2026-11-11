# MANIFOLD E1M1 — M13.2 all-leaves: resposta inicial do Cláudio (11/11/2026)

Responde a `MANIFOLD-E1M1-M13-2-ALL-LEAVES-RESULTADO-CLAUDIO.md` (commit `83ff9c3`). Só leitura de código e análise; nenhum renderer alterado e nenhum build disparado.

## 1. O que o código mostra

- **Os blocos azul-escuros são o preenchimento de fundo, não cor de textura.** `manifold_fill_open` (gerado por `bsp_order_renderer` em `stage_rom.py`) pinta com `0x1111` cada coluna cujo intervalo `yclip` continua aberto ao fim do traversal, e então fecha o intervalo. Logo, cada bloco azul marca colunas que nenhuma parede fechou. A causa é "parede não fechou esta coluna", não paleta, textura ou DMA.
- **O diagnóstico all-leaves não remove o problema, e isso restringe a causa.** No `m13_bsp_all_leaves_diagnostic`, o `return 1` entra depois de `bsp_cell_x1 = bsp_open_x1; bsp_cell_x2 = bsp_open_x2;`. Ou seja, cada folha é visitada com a janela cheia de colunas abertas, sem o recorte por bbox. Mesmo assim sobram buracos. Portanto a perda não vem da seleção de folhas pelo BSP (bbox/frustum). Ela acontece dentro de `visit_graph` (travessia de setores/portais e projeção de paredes) ou na forma como `yclip` é fechado.
- **Os 4 FPS → 1 FPS são esperados desse diagnóstico.** Sem bbox, todas as folhas são processadas com janela cheia. A queda mede custo de processar tudo, não a solução. Não é uma regressão de otimização a ser "consertada" sem antes resolver os buracos.

## 2. Candidatos verificados e descartados por ora

- **Overflow de `s16` na projeção do bbox (`bsp_box_visible`).** `FIX16_FRAC_BITS` é 6 (`FIX16_INT_BITS` 10, de `sgdkr/inc/maths.h`). Com `BSP_FAR` = 1600 e coordenadas de mapa dentro de ±2000 em relação ao jogador, `rz` e `rx` cabem em `s16`. Não é a causa, pelo menos nessa faixa. Vale reverificar para as vistas externas, que estão mais longe.
- **Recorte de janela por bbox.** Descartado como causa única, pelo argumento da seção 1.

## 3. Candidatos ainda abertos (ordem sugerida)

1. Paredes visitadas cuja projeção não cobre a coluna (cálculo de `yclip` por coluna em `visit_graph`, com cortes de topo/base que deixam um vão).
2. Setores atravessados com a janela de `visit_graph` (`wmin`/`wmax`) já estreitada por portal anterior, impedindo a parede de ser gerada.
3. Paredes geradas mas com altura/teto que não fecham o intervalo (o caso que o M13.2 corrigiu para alturas, pode ter deixado um vão na face inferior).

## 4. Experimento proposto (A, local, sem runner)

- Instrumentação opt-in (`MANIFOLD_BSP_HOLE_DIAG=1`): ao fim de cada `manifold_fill_open`, contar colunas e linhas preenchidas; registrar, por célula visitada, quantas colunas ela fechou. Gravar o total num volátil lido pelo harness do MAME.
- Para cada vista com buraco, identificar a última célula que deveria ter fechado a coluna e checar se foi visitada, se gerou parede e se essa parede cobriu a coluna.
- Mesma câmera nos dois builds (`MANIFOLD_BSP_ALL_LEAVES=0` e `=1`), H40, ROM jogável.

Pedido: as coordenadas e o ângulo da segunda captura (área externa grande com os blocos azuis). Sem isso, a reprodução usa uma das seis câmeras do handoff M12.

## 5. Plano de medição (B)

Contar folhas visitadas, células, segmentos e colunas fechadas por quadro, com e sem bbox, nas mesmas câmeras. Separar custo por fase (BSP, projeção, paredes, piso/teto, flip/overlay) antes de propor uma seleção de folhas.

## 6. Status

- Causa dos buracos: **aberta**, com o escopo reduzido a `visit_graph` e ao fechamento de `yclip` (seção 3).
- FPS: **não medido por mim**; o número de 4→1 vem do relato do usuário.
- Próximo passo: implementar a instrumentação da seção 4 localmente e reproduzir a câmera da segunda captura, se o usuário passar as coordenadas.
