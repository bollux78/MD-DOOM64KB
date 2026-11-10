# Manifold E1M1 — Plano M11/M12: correção visual, profiling e LOD geométrico

**Data:** 10/11/2026 · **Autor:** Werk/GPT (planejamento; nenhum patch de render aqui)  
**Repositório:** `bollux78/MD-DOOM64KB` · branch de integração `exp-manifold-e1m1-m01`  
**Marco paralelo:** Claudio desenvolvendo M10 **HUD-WAD H32**, com compartilhamento de tiles; não modificar seu trabalho, os scripts M10, o HUD da R128 ou Sega CD. Ao iniciar a implementação, criar branch específica M11/M12 baseada no commit aprovado da M10 (ou em baseline congelada) e fazer merge/cherry-pick controlado.

## 0. Objetivo, evidência e prioridades

O usuário relata que a E1M1 já é jogável, a área externa do ácido continua com grandes superfícies triangulares/azuis substituindo o cenário em alguns ângulos, e escadas/pontes/vistas longas derrubam muito o FPS. A hipótese do usuário: a quantidade de faces/células/portais visíveis pesa mais que a textura isolada. Ele quer um **LOD/low-poly verdadeiro em distância**, sem perder geometria próxima, aparência reconhecível de DOOM e passagens transitáveis.

**Resultados já medidos, não confundir com novas metas:**
- M08 escada ~**3,8–4,4 FPS** em capturas MAME, movimento/câmeras não inteiramente equivalentes; sem ganho material ao limitar repetição de visitas (`sector_rendered_cache >=14` para `>=10`).
- M09 experimental: paredes sólidas distantes (>768) trocadas por cor média. Escada **3,8→3,9 FPS** num dos pontos, e exterior **4,0→2,9 FPS** em outra captura, com perda de detalhe; **revertido**. Isso demonstra que substituir amostragem de textura por cor **não é redução de geometria/visitas** e pode piorar.
- M08 geometrias `true_cells.py`: `nonmatching_internal_edges=0`; as antigas **112 arestas não pareadas da M02 foram resolvidas** e não devem ser reapresentadas como causa comprovada dos novos artefatos.
- Claudio M10: [resultado de implementação](MANIFOLD-E1M1-M10-HUD-RESULT-CLAUDIO.md) confirma modo H32 e assets reduzidos de **389→132 tiles**, uma paleta PAL2. Controle M10 vs HUD: média 6,86 vs 6,76 FPS (tour de 86 setores), diferenças pequenas. **Não usar o espaço/tiles economizados para duplicar cenas sem auditoria de VRAM**.

## 1. M11A — reproduzir e isolar cada quebra externa (antes de otimização)

**Criar dois pontos fixos**, no mesmo setor e câmera:
- E0: vista da área do ácido mostrada pelo usuário, com faixa azul-escura diagonal; capturar `player(x,y,z)`, direção angular, sector/cell, `sky` e níveis de piso/teto. Nunca usar só `frame 300` do autowalk (posição não fixa se FPS/comportamento mudar).
- E1: mesmo local com pequena rotação (+/- alguns ângulos) e movimento +/− 1 unidade para separar erro de recorte de erro de topologia.
- Controles S0 (escada olhando para muitos degraus), S1 (escada olhando de volta para corredor), B0 (ponte), C0 (corredor longo), R0 (sala inicial).
- Fixar H32, resolução, paleta, céu, render e entrada. Capturar screenshots PNG de MAME e BlastEm gráfico e um mapa com posição, ângulo, células visitadas.

**Instrumentação de baixo custo (ativação `MANIFOLD_PROFILE=1`):**
- contadores `cells_visited`, `portal_edges_tested`, `portal_recursions`, `sectors_revisited`, `edges_frustum_culled`, `edges_z_clipped`, `edges_projected`, `columns_drawn`, `columns_textured`, `ceil_spans`, `floor_spans`, `clip_window_empty`, `portal_fog_cut`, `stack_depth_max`.
- Medir tempo/intervalo por fase com contador de ciclos do emulador ou marcas H/V do VDP (cuidado: HV tem wrap, interrupções, custo de leitura). Reportar **CPU por etapa**, raster, DMA/VBlank e total, sem confundir quantidade de quadros com FPS instantâneo.
- Gerar modo de diagnóstico **sem escrita de logs por parede** em build normal; acumular contadores e descarregar snapshot por pausa ou log de emulador em frequência baixa, pois `KLog` antigo abriu depurador no BlastEm.
- Invariantes/guardas: `0<=x1<=x2<=RENDER_WIDTH`, `0<=clip_top<=clip_bottom<=SCREEN_HEIGHT`, profundidade positiva, `window_min<window_max`, índices de célula/portal válidos, `portal_group` dentro de limites, ausência de escrita fora de framebuffer.

**Teste de isolamento, uma mudança por variante (M11A):**
1. Fundo céu com cor sólida, geometria igual; se a diagonal persiste, problema não está na imagem SKY1.
2. Desligar **apenas** o corte de fog para os portais no ponto E0 (já existe exceção para teto céu); se desaparecer, revisar corte/visibilidade, mas manter limite global como proteção de FPS.
3. Pintar cada célula visitada com ID/cor de debug e desenhar separadamente janela x do portal, limite superior/inferior e z. Capturar no mesmo frame (sem vazar no modo normal).
4. Renderizar portais em ordem inversa/ordenada em variante controlada e comparar: se o triângulo muda com ordenação, problema provável em clipping/oclusão e não na geometria carregada.
5. Exportar das células reais as bordas externas/adjacências e verificar visualmente sua projeção 2D/3D no ponto E0. **Não abrir paredes sólidas arbitrariamente.**

**Pontos concretos para auditar:**
- `src/portal.c`: `visit_graph`, `sector_rendered_cache` e janela de recursão, comportamento de `FRUSTUM_CULLED`, `NEAR_Z_CULLED`, `x1>=x2`, clip top/bottom por coluna; inserções de `far_portal_fog`, `textured_portal_steps` e `guard_zero_reciprocal_in_texture_columns` em `stage_rom.py`.
- `src/bunch_render.c`: `first_wall_is_behind_second` contém em upstream um indício de erro: `s16 w1y2 = bunch2_wall->z2;` quando se esperaria `bunch1_wall->z2`. **Antes de alterar, verificar se este código é realmente chamado na build Manifold E1M1 e se contribui para o ponto E0.** Há também condição `b1->min_x >= b2->max_x` usada antes e dentro de `bunch_needs_to_move_right`; investigar se ramo é inalcançável ou intenção.
- `true_cells.py`: união convexa, orientação horária, `weld_and_pair`, T-junctions e `merge_collinear`; validar comprimento e convexidade das faces no lado externo.
- `emit_portal_map.py`: a função `assign_wall_textures`, `ceil_color` especial para F_SKY1, grupos de setores, portas provisórias e bounds de visibilidade. Não tratar os 112 erros históricos como pendência atual.

**Saída/aceite M11:** pares de screenshots, reprodução determinística e uma **correção isolada que remova a diagonal em E0/E1** sem criar buracos em S0/B0/C0; testes BlastEm 3600 frames sem exceções; custo em FPS no mesmo ponto não regredir >~5% (margem provisória; repetir medições).

## 2. M11B — medir o gargalo das escadas/pontes antes de LOD

Executar S0, S1, B0, C0, R0 fixos com 5–10 repetições (mesmo commit/mesmo estado/mesma imagem). Medir **mediana** e p10 FPS, além de ciclos/fase e contadores acima. Comparar perfis:
- `geometry-only`: projeção e portais, nenhum preenchimento de pixels;
- `flat`: mesmas faces, preenchimento simples;
- `full texture`: render normal;
- `no-floor/no-ceiling`: identificar custo dos spans;
- `single-depth`: apenas diagnóstico, custo da recursão.
Essas opções são variantes diagnósticas; não classificar uma como ROM jogável.

Se geometria+portais representarem parte dominante dos ciclos, priorizar LOD de **faces e portas/recursão**, caso contrário otimizar colunas/spans/DMA. **Não assumir que a GPU é o gargalo; o 68000 faz projeção e raster via CPU.**

## 3. M12 — LOD geométrico genuíno sem quebrar colisão

**Princípio:** manter sempre o mapa físico de colisão e portais da M10/M11 íntegro; simplificar somente a **representação renderizável em distância**, com topologia de travessia compatível. Se for necessário construir um grafo de portais de render separado, gerá-lo offline.

**LOD0 (perto):** geometria original; cada degrau, detalhe de parede, textura próxima, teto/piso.

**LOD1 (médio):** pré-mesclar offline **arestas coplanares ou colineares contíguas**, contanto que tenham mesmo `doom_sector`, alturas de piso/teto, material, luz, UV/offset e classificação sólido/portal. Para escadas: agrupar degraus contíguos num número menor de faixas de altura visíveis, sem alterar colisão. Portais internos só são colapsáveis se o novo volume e as janelas de visibilidade permanecerem conservadores (nenhuma parede visível falsamente ocluída). Mapa de correspondência `render_group -> original_cells`.

**LOD2 (longe):** para conjuntos de degraus/pontes pré-marcados, substituir 8–20 perfis pequenos (exemplo hipotético, não contagem medida do mapa) por 1–3 perfis/rampas **somente no render**. Preservar silhueta, limites externos, silhueta de ponte e recorte do céu, entradas/saídas e grandes descontinuidades. Não permitir que um polígono simplificado apague o portal necessário a uma passagem visível; alternativamente renderizar o vão como uma única abertura agregada.

**Critério de troca:** usar *tamanho projetado*, não só distância absoluta:
- Testar `screen_span_px < 1` e `< 2` nos modos de diagnóstico, depois escolher por qualidade/performance. A largura da Manifold é 64 colunas lógicas no renderer, então pequenas feições muitas vezes caem em subpixel. Introduzir histerese no limiar para evitar *popping* ao girar/mover.
- Se a troca de LOD for escolhida para um grupo, usar representação coerente para **todas** suas faces naquela vista, não cada degrau de modo independente.
- Não duplicar mapas completos na RAM/VRAM. Preferir tabelas compactas em ROM, indexadas por célula/cluster e distância, e escolher um emissor por cluster; orçamento de ROM medido no build.
- Fazer duas versões: `m12-lod-off` (controle) e `m12-lod-on`. **Nenhuma alteração em DOOM R128/SCD ou M10 HUD**.

**LOD de visibilidade (mais seguro como primeira tentativa de FPS):**
1. Pré-calcular PVS regional/portais reais a partir do `true_cells` ao invés do atual all-visible provisório, mantendo falso-negativo = 0 (aceitar falsos positivos).
2. Usar máscaras de coluna ou intervalos já ocluídos antes de transformar paredes distantes; a coluna totalmente coberta não deve disparar recursão.
3. Caches por frame de projeção por vértice/célula quando a câmera/transform for idêntica; custo de invalidação e memória precisam ser medidos.
4. Pré-agregar escadas como *clusters de render* sem perder setores originais de colisão.
5. Somente depois avaliar versões low-poly agressivas com silhuetas alternativas. Evitar fog falso em portais com céu (falha M06).

## 4. Matriz de experiência — não misturar efeitos

| Experiência | Modificação | Pergunta e decisão |
|---|---|---|
| M11-C0 | Sem mudança, posições fixas | Referência determinística |
| M11-F1 | Fog desligado só no setor E0 | A diagonal é parede de fog? |
| M11-P1 | Janelas/limites de portal por coluna em debug | Falha recorte/oclusão? |
| M11-O1 | Ordenação de paredes comparada; validação de bug em bunch | Afeta imagem e execução real? |
| M12-V1 | PVS conservador por cluster | Reduz células visitadas sem buracos? |
| M12-G1 | Mescla de faces contíguas compatíveis | Reduz custo de geometria sem deformar paredes? |
| M12-S1 | Escadas distantes simplificadas visualmente | Ganho FPS e silhueta tolerável? |
| M12-H1 | Histerese e transição de LOD | Sem flicker/popping perceptível? |

**Targets de aceitação (metas, NÃO resultados já obtidos):**
- **Correção:** nenhuma região azul ou diagonal espúria em E0/E1 e ausência de `ZERO DIVIDE` nos tours.
- **FPS escada/pontes:** buscar pelo menos +20% de mediana com LOD ON vs OFF nos pontos equivalentes, sem retrocesso grave no p10. Se não alcançar, medir e rejeitar hipótese; não alegar ganho especulativo.
- **Visual:** contornos e portas corretos a curta distância; sem degraus que desaparecem no primeiro plano; céu contínuo.
- **Gameplay:** caminhar/rotacionar/transpor portas da M08/M10; colisão e z do personagem **não podem** depender da malha LOD.
- **Validação:** 3600+ quadros BlastEm autowalk, tour MAME, screenshots A/B em E0/S0/B0 e jogo gráfico pelo usuário antes de release.

## 5. Dependências e execução após Claudio concluir M10

1. Obter commit e ROM do M10 **aprovados pelo usuário**. Verificar `docs/agent-handoffs/MANIFOLD-E1M1-M10-HUD-RESULT-CLAUDIO.md`, resolver integrações caso o upstream tenha mudado.
2. Registrar coordenadas exatas E0/S0/B0 (do usuário, via debug HUD ou telemetria) e salvar scripts de câmera fixa e métricas em `experiments/DOOM_Manifold_E1M1/tools/`.
3. Implementar e testar M11 (visual) com uma alteração por variante e uma ROM de controle. Não mexer em HUD, fontes, paletas, céu, buffers da arma ou portas que já funcionam.
4. Medir e decidir hipóteses de desempenho. Implementar M12 em sub-branches com canários e métricas. Rejeitar LOD se houver queda de FPS, artefatos ou mudança de colisão.
5. Manter release fixa `manifold-e1m1-latest` e branch M10 intactas até aprovação gráfica explícita. Assets/WAD do shareware continuam exclusivamente no runner.
6. Documentar `fps median/p10`, `render_cells`, `wall_edges`, `portal_visits`, ciclos/fase, CRC de ROM, screenshots comparativas e custo em bytes de ROM/WRAM por configuração.

**Resultado deste documento:** plano técnico e hipóteses auditáveis. **Nenhuma correção visual ou ganho de FPS implementado/validado por este plano.**
