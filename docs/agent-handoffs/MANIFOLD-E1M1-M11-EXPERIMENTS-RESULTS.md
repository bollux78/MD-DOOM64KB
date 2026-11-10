# Manifold E1M1 M11 — primeiro ciclo experimental (10/11/2026)

**Base preservada:** commit `32b0b3be263f0a685fc0a902604bfd4f5ffc3ff3` (H32 + HUD Doom, principal). Testes isolados na branch `exp-manifold-m11-visual-perf` sem merge na branch principal `exp-manifold-e1m1-m01`. Release fixa intocada.

## Evidências

### Experimento A — cache de vértices por quadro
- Código opt-in: `cache_transformed_vertices` em `experiments/DOOM_Manifold_E1M1/m01/stage_rom.py`, `MANIFOLD_VERT_CACHE=1`. Recalcula uma vez por vértice/por quadro; armazena em WRAM 6 bytes/vertex (coordenadas projetadas e etiqueta), mantendo recorte independente por portal; usa saturação do E1M1.
- [Action #42848607413](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42848607413): **build success**, variantes H32 controle `doom-md-manifold-e1m1-m02-hintfix.bin` (SHA-256 `9d432ea4e41313424b47ec657c528b19bbd6d34b190b64bf6e744f0687f45737`) e `m11-vertexcache-h32.bin` (SHA-256 `b04aadeca9606a088181465673a56615ada8cd6f74056eacd5dbb7ac4f2c0816`).
- Teste MAME de 900 frames: o percurso do jogador divergiu, mantendo o cache perto do ponto inicial enquanto o controle avançou; FPS 3,9 vs cerca de 4,0 na sala inicial. Pode ser efeito de timing/input/collision e não prova de crash ou falha lógica. **Não aprovado como otimização, nem comprovado ganho**.
- BlastEm autowalk 3600 frames no workflow testa a **ROM autopilot baseline**, não a ROM opt-in com cache; **não afirmar que cache passou autowalk**.

### Experimento B — janela de portal totalmente ocluída
- Código opt-in: `skip_fully_occluded_portals`, `MANIFOLD_OCCLUSION=1`, que tenta dispensar chamadas de `visit_graph` se todas as colunas de `yclip` já estão fechadas. Nenhum dado persistente em WRAM.
- [Action #42849779952](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42849779952): compilou com sucesso; H32 principal + `m11-occlusion-h32.bin` (SHA256 `4e97ca34e8a9dd22583d2906c92ad0e09ba5aaba2eb4ddc16a86fc770afc7704`).
- MAME 900 frames: FPS na vista inicial ~3,9 em ambas; depois, percurso automático diverge (ROM com oclusão permanece nas primeiras vistas enquanto controle sai), impedindo A/B crível nas vistas seguintes. **Nenhum ganho demonstrado; não promover**. Necessário verificar se yclip global pode indicar falso bloqueio em visitas através de outro portal e se loop de checagem tem custo.
- BlastEm 3600 no workflow não exercita essa variante; ROM principal continua baseline.

### Experimento C — retirar fog distante para localizar diagonal
- O código corrente desliga apenas a função `far_portal_fog` via `MANIFOLD_SKIP=far_portal_fog`; a variante é uma **ROM tour automática** (`MANIFOLD_TOUR_SKY=1 MANIFOLD_TOUR=tour_input`), não jogável manualmente.
- [Action #42850641871](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42850641871): **build success**; `m11-fogoff-h32.bin` (SHA256 `7c5a86bdbaa73ccf81531933f9e76b01dda287bb72b6f22f8c002b29f8f9fd1a`). Comparada com `doom-md-manifold-e1m1-tour-m03.bin` normal, mesmo commit e mapa.
- Capturas (artefato screenshots da Action): grande forma **triangular cinza** na vista de tour ~F420 aparece em ambas as variantes; o fog está desligado só na variante B, portanto **fog não é causa suficiente** para esse artefato. Não implica que todos os blocos azuis da captura do usuário tenham a mesma origem.
- A distância/custo de render pode afetar ângulo percorrido durante tour, então pares em frames tardios não são câmera 100% idêntica; implementar snapshot de câmera fixa antes de concluir qual correção remove a diagonal.

## Diagnóstico consolidado

1. As 112 arestas sem par citadas na M02 são história; o atual `true_cells.py` reporta **0** edges internas não pareadas. Não insistir nessa hipótese sem novos dados.
2. O possível bug em `bunch_render.c` (`w1y2=bunch2_wall->z2`) não participa do renderer atual segundo o Claudio: linker remove `bunch_render`, que não é chamado por `visit_graph`.
3. `visit_graph` consome cerca de **37% CPU numa amostra de cena lenta** segundo relatório do Claudio. Tratar como foco de profiling, não como diagnóstico universal.
4. `MANIFOLD_FAR=1600` e portais ligados ao teto transparente (`F_SKY1`) não devem virar parede de fog. A triangular persistente sem fog exige investigação de **ordem de desenho, janela de portal, clipping near-z, limites de teto/piso e saturação**.
5. Tanto A quanto B devem permanecer **opt-in desativados**; custos de 6 bytes/vertex em A, de loop por coluna em B, ainda não justificados por resultados. Os arquivos de trabalho permanecem na branch experimental para eventual refatoração, não no branch principal.

## Próxima execução recomendada

- Instrumentar MAME Lua com **câmera fixa** em pontos da área externa e escada: x/y/z/sector/ângulo registrados na Action #42850641871, por exemplo tour F300 x=`0x001BD400` y=`0xFFC65400` z=`0xFFFF4198` sector+angle=`0x00300151`; F420 x=`0x0020B400` y=`0xFFC6C000` z=`0xFFFF3F34` sector+angle=`0x0033038B`. Usar mesma posição/ângulo realmente fixos em ROM comparadas, não mesmo índice de frame.
- MAME dumps: `playerXInt`, `angleSin16`, `angleCos16`, `window_min/max`, `yclip`, índices, alturas projetadas e retornos de `clip_map_vertex_16`; contar portais pulados por near-z e limite de profundidade.
- Separar `visit_graph` render de entrada e uso de `yclip`; perfis por 3D frame e benchmark mediana/p10 do FPS por 100 frames com câmera congelada.
- Testar LOD de **visibilidade/topologia** antes de "cor sólida distante" (M09 anterior teve regressão de desempenho). Para simplificação de degraus/ponte, manter colisão da M10 e gerar render groups offline sem criar falsos portais.
- Fazer A/B com ROMs H32 HUD Doom e testes gráficos/console somente após validar oclusão e FPS. **Não publicar release**.
