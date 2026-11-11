# Auditoria sistêmica do Manifold H40 — M13.2 Werk (11/11/2026)

**Base:** `exp-manifold-m12-claudio`, H40 com BSP, colisão de raio 16, câmera estabilizada, SKY1, HUD-WAD e música. WAD local do runner, jamais commitado. Esta auditoria distingue prova por inspeção de hipótese visual.

## Reprodução relatada pelo usuário

- Todas as ROMs H40 exibem, em alguns ângulos da área externa e da ponte da terceira sala, parede superior que **não acompanha** a parte inferior escura; perspectivas divergem e existem cortes/faltas de cenário.
- A `werk-m13-vram-oneshot-h40.bin` recupera boa parte do HUD e céu, mas não resolve tudo; foto externa marca **3,1 FPS** (não equivale a benchmark padronizado).
- A variante com `SYS_disableInts()` durante alterações contínuas de BG_B piorou FPS e passou a exibir blocos de colunas alternados entre direita/esquerda; **rejeitada**.
- A validação visual reportada no momento é BlastEm/console conforme cada registro; não inferir equivalência entre teste headless e hardware.

## Achados de código por prioridade

### G-01 — clipping direito altera a profundidade esquerda (CONFIRMADO no upstream, não corrigido nas H40 de console)

**Local:** Manifold original `src/math3d.c`, função `clip_map_vertex_16`, ramo `// right clipped`: após ajustar `rx2`, o código escreve `rz1_12_4 = NEAR_Z_FIX`, depois `trans_v2->y = rz1_12_4`. O correto é atualizar `rz2_12_4`; o ramo da esquerda já altera `rz1_12_4`. O mesmo bloco usa `dx`/razões com precisão de 16 bits no original. Isso torna assimétrico o tratamento dos vértices e pode gerar projeções discrepantes em ângulos de quase plano próximo. **Não é prova de que explica toda a distorção externa.**

**Estado:** existe função opt-in `m11_safe_near_clipping(out)` em `stage_rom.py`, que faz as duas interpolações em `s32`, corrige `rz2` e protege o lookup recíproco antecipado em `portal.c`. As ROMs H40 M12/M13 anteriores não tinham `MANIFOLD_NEAR_SAFE=1`. Próximo teste controlado: H40 `MANIFOLD_NEAR_SAFE=0` versus `1`, mantendo todas as demais flags constantes.

### G-02 — teste BSP usa normais de 16 bits após produtos grandes (CONFIRMADO no código, impacto visual ainda não demonstrado)

**Local:** função `bsp_order_renderer(out)`, `portal.c` gerado: `static s16 bsp_rnx, bsp_rny, bsp_lnx, bsp_lny;`; cada normal inclui produto como `(RENDER_WIDTH/2) * angleSin16` e `hi * angleCos16`. A expressão intermediária pode exceder o intervalo `[-32768,32767]`, sendo truncada ao atribuir a `s16`, potencialmente invertendo o sinal do semiplano. A culling BSP também usa produtos de coordenadas do mapa no teste de caixas. O Werk implementou um patch experimental para escalar as normais em `s32` na branch antiga `exp-manifold-m12-h40-stability`, mas **não foi isoladamente validado**. Não portar em conjunto com G-01: fazer teste A/B separado.

### G-03 — coerência entre recorte de portal, upper/lower step e textura (A AUDITAR)

**Local:** `src/portal.c`: `visit_graph` calcula extremos de chão/teto da parede atual com `project_and_adjust_y_fix`; para os portais, computa teto/chão do vizinho com o **mesmo** recíproco de profundidade por extremo e usa `draw_upper_step`/`draw_lower_step` ou versões texturizadas. Há lógica de janela (open interval), stepping BSP e passagens de `tmap_info`. O problema visual pode resultar de recorte horizontal que não interpola consistentemente profundidade, U e Y nas duas bordas; **ainda não demonstrado**. Necessário instrumentar uma aresta física (IDs de parede/sector, `x1,x2,z1,z2,ytop,ybot,nx1,nx2`) e comparar com projeção de referência em precisão `s32/s64`.

### G-04 — multiplicações, divisões e lookup de profundidade (RISCO IDENTIFICADO)

- `src/math3d.c`: `project_and_adjust_x` usa `lsl.w #5` antes de multiplicação `muls.w`; verificar limites e saturações de X, sobretudo após recorte de frustum.
- `src/math3d.c`: `project_and_adjust_y_fix` computa `s16 yMinusPosZ`, produto com recíproco em `s32`, shifts via assembly e redução a `s16`; comparar com modelo de referência para altura de câmera, tetos e grandes distâncias.
- `src/draw.c`: interpolação de U/z realiza divisão por `u16 one_over_z_16` e pelo valor ao fim de spans de quatro colunas; já existe patch de segurança para denominadores nulos. Verificar overflow/arredondamento e assimetria upper/lower.
- `src/portal.c`: `z_recip_table_16[]` originalmente acessado antes de verificar retorno de clipping; `m11_safe_near_clipping` também contém guarda para isso.

### G-05 — lógica de dados WAD e células BSP (RISCO DE INTEGRAÇÃO)

Auditar `emit_portal_map.py` e gerador de folhas: coordenadas, winding, arestas compartilhadas, alturas em unidades corretas, flags DOOM BLOCKING e correspondência `LINEDEF/SIDEDEF/SECTOR`. Testes determinísticos devem exigir que cada portal `A→B` tenha aresta reversa geométrica no destino, e que upper/lower use a mesma aresta recortada. Reportar lacunas `allow_gaps=True`, não tratá-las como portais válidos.

### G-06 — framebuffer H-Int/V-Int, VRAM, céu e HUD (PROBLEMA REAL, causa completa em aberto)

A M13 HUD *oneshot* melhora inicialização, indicando dados estáticos transferíveis; `SYS_disableInts` em chamadas prolongadas do BG_B fez os blocos de colunas piscarem. Esse resultado reforça a importância da temporização H-Int/V-Int do `my_bmp.c`. **Não** bloquear interrupções durante o framebuffer. Auditar intervalos VRAM das telas e de HUD/céu/arma, fila DMA e resets de tilemap sem misturar isso com projeção geométrica.

## Plano de execução e aprovação

1. **A/B G-01:** duas ROMs *playable* H40, mesma geometria e HUD *oneshot*, diferença exclusivamente `MANIFOLD_NEAR_SAFE=1`; executar smoke do BlastEm sem overclock e verificação de geração. Fotos em área externa, ponte, perto de paredes/portas. Sem benchmark comparável ainda.
2. **A/B G-02:** portar só o conserto BSP de precisão para nova rodada mantendo G-01 fixa conforme teste; registrar quadros/câmeras e FPS.
3. **Testes geométricos fora do renderer:** validar orientações e adjacências de todas as arestas de E1M1, e comparar projeção numericamente com referência de 64 bits. Resultados reproduzíveis no runner.
4. **Instrumentação de uma parede específica:** IDs, extremos 3D, extremos após clip, coordenadas projetadas, intervalo de pixels rasterizado; distinguir geometria de erro de transferência VDP.
5. **Separar VDP do renderer:** somente quando geometria consistente, investigar HUD/céu, perdas por tile e custo DMA.
6. Auditar desempenho depois da correção matemática, sempre H40; ganho não pode comprometer correção.

**Política:** branch única `exp-manifold-m12-claudio`; evitar cherrypicks cegos, sem WAD nos commits/artifacts. ROM compilada ≠ imagem correta em BlastEm ≠ hardware aprovado.
