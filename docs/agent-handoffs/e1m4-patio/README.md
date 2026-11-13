# E1M4 patio: evidencia do Claudio (isolada, nao mexe no codigo do jogo)

Reproducao (MAME): jogador no centro do patio (celula 161, setor 70, x=1600 y=816), girando em 8 angulos (0..1023, passo 128).
Triangulo aparece nos angulos diagonais 128/384/640/896; nao aparece em 0/256/512/768.

## Medidas
- Cortes de recursao (profundidade>48 ou pilha) = 0; profundidade maxima = 8 nesse patio. (setor-em-desenho e >5 visitas NAO foram medidos.)
- Celula 161 e um retangulo 736 x 192 (4 paredes), jogador no centro. As paredes sao enviadas ao desenho.
- Angulo 128 (ruim): parede longa lateral vai da frente-esquerda (x=-192, z=326u) a um ponto ATRAS da camera (326,-191u); clip=8; x projetado 13..431.
  Angulo 256 (bom): mesma parede, x 40..339.
- Vertice atras da camera: z vira NEAR_Z_FIX e x original e mantido (sem interseccao geometrica com o plano proximo);
  recorte de frustum esta desligado (`if(0)` em clip_map_vertex_16).

## Hipotese (nao provada)
Span projetado muito alem da borda direita (431 vs 339) perde precisao no rasterizador e a face deixa de ser desenhada.

## Teste proposto
Calcular a interseccao real parede x plano proximo antes de projetar (ou limitar o span a janela mantendo a inclinacao). Se o triangulo sumir, confirmado.

portal_diag.patch grava, para a celula 161 em profundidade 0, vertices transformados, resultado do clip e ramo de saida (manifold_dbgw). yard3.lua le esses valores no MAME. Requer ampliar pinos do md_split.ld (bss 0x1D60, doom_objects 0x9400) so para a build diagnostica.
