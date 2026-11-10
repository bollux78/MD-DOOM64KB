# Manifold E1M1 M11 — benchmark H32 com seis câmeras fixas (10/11/2026)

## Estado e reprodução
- Base unificada e preservada: `32b0b3be263f0a685fc0a902604bfd4f5ffc3ff3` (H32 + HUD Doom).
- Branch experimental: `exp-manifold-m11-visual-perf`; **nenhuma alteração incorporada à branch principal nem à release**.
- [Action #42859877834](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42859877834) — **SUCCESS**: build de variantes e MAME com câmera fixa, sem movimento do jogador. Capturas e `m11-fixed-results.csv/.md` no artefato `manifold-e1m1-screenshots-42859877834` (retenção 3 dias).
- Mecanismo: `MANIFOLD_CAMERAS=fixed` em `stage_rom.py`, trava coordenadas, setor, z e ângulo a cada leitura do joypad; troca a cada **300 VBlanks** depois do frame 60.
- Métrica: diferença do contador `manifold_dbg[6]` (chamadas `portal_rend`) entre os VBlanks **120 e 330**, **420 e 630**, ... (janela de 210 quadros a 60 Hz). FPS estimado = 60×renders/210. Resolução quantitativa: 0,286 FPS por render; não interpretar pequenas diferenças como significativas.
- Três **ROMs H32 com o mesmo HUD do Doom e a mesma câmera**: `m11fixed-h32.bin` (controle), `m11cache-h32.bin` (cache transformado por frame), `m11fogoff-h32.bin` (distante fog removido).
- Câmeras: `E0=(1781,-3691,cell48,angle337)`, `E1=(2093,-3664,cell51,angle907)`, `S0=(192,-3334,cell54,angle0)`, `S1=(-224,-3232,cell70,angle256)`, `S2=(1203,-3232,cell89,angle512)`, `R0=(1056,-3616,cell87,angle0)`. Todas as coordenadas foram validadas na célula BSP. S0/S1/S2 são *candidatas* selecionadas por diferenças de piso e fanout de portais, **não identificações topográficas já confirmadas de escada ou ponte**.

## Resultado do benchmark fixo

| Câmera | Controle | Cache de vértices | Sem fog | Cache vs controle |
|---|---:|---:|---:|---:|
| E0 externa | 2,57 FPS | 2,57 FPS | 2,86 FPS | 0% |
| E1 externa | 7,71 | 7,43 | 7,71 | -3,7% |
| S0 pesada | 2,57 | 3,14 | 2,57 | +22,2% |
| S1 | 6,00 | 5,71 | 6,00 | -4,8% |
| S2 pesada | 2,00 | 2,86 | 2,00 | +42,9% |
| R0 inicial | 7,43 | 7,71 | 7,71 | +3,8% |

**Interpretação:** ganhos concentrados nas vistas S0/S2 mais pesadas, sem vantagem universal. Os números baixos são medidos em câmera fixa por quadros realmente renderizados, e são mais úteis que o texto de FPS da screenshot (que pode estar suavizado e defasado). Repetir testes/bench mais longos antes de concluir ganho definitivo. Diferenças de ±1 render em 210 VBlanks têm alto peso proporcional nas cenas de 2 FPS.

## Comparativo visual e hipóteses

- Capturas sincronizadas nas 6 câmeras, com original, cache e fog desligado. Não há ruptura geométrica nova evidente nas capturas do cache; pixels discrepantes variam cerca de 0–0,45% na região central amostrada e podem incluir HUD/FPS/temporalidade.
- **Fog off:** em todas as câmeras fixas, a região central da imagem aparece **idêntica** ao controle nessas capturas; a grande superfície cinza próxima à segunda câmera externa continua. O corte de neblina não é a causa do artefato nessa vista.
- O caso E1 apresenta **grande plano cinza triangular**, com parede ao redor visível. Para diagnosticar: depurar z, projeção de teto/piso, `clip_map_vertex_16`, janela dos portais e `yclip`. Não simplesmente remover um suposto bloco de fog.
- A variante opt-in `MANIFOLD_VERT_CACHE=1` mantém buffer de recorte por parede, cacheia transformação dos vértices até uma vez/frame e guarda 6 bytes/vertex em WRAM. O build anterior de autowalk divergiu de percurso por timing; não provaria regressão causal. Necessário testar especificamente ROM **autowalk com cache ligado**, não apenas autopilot baseline (a Action #42860868221 foi configurada para isso).


## Validação posterior da ROM jogável com cache (Action #42860868221)

- [Run #42860868221](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42860868221): **SUCCESS**, compilou `m11play-h32.bin` (jogável, H32/HUD Doom, cache de vértices, sem travamento de câmera) e `m11autowalk-h32.bin` (mesmo cache, com entrada automática).
- **Teste estrito específico da variante otimizada** `M11_CACHE_AUTOWALK=PASS_3600_FRAMES` no BlastEm headless, com vetores de exceção fatais. Diferente dos experimentos anteriores, este teste rodou de fato com `MANIFOLD_VERT_CACHE=1` e movimento ativo.
- ROM jogável candidata no runner: `/home/dan/Projetos/Personal/manifold-e1m1/run-42860868221-1/m11play-h32.bin`, 1.835.008 bytes, header `SEGA`, SHA-256 `b04aadeca9606a088181465673a56615ada8cd6f74056eacd5dbb7ac4f2c0816`.
- ROM de controle com câmeras fixas: `m11fixed-h32.bin`, SHA-256 `a75d7e5462830e9e939e019c2c28d956b3ccb0798fcf8405535bb455f421db95`. A ROM de autowalk altera intencionalmente os vetores de exceção e não deve ser entregue como jogável.
- FPS fixo nessa Action repetiu o mesmo relatório da primeira, confirmando reprodutibilidade dos seis pontos no MAME. **Aprovação limitada:** estabilidade automatizada e capturas; ainda requer navegação real no BlastEm gráfico do usuário, especialmente escadas, portas e área externa.
- Não promover ainda à branch principal nem à release; cache permanece opt-in `MANIFOLD_VERT_CACHE=1`.

## Próximas etapas
1. Verificar Action #42860868221, que gera `m11play-h32.bin` (ROM jogável, cache) e `m11autowalk-h32.bin` (cache+autopilot) e executa BlastEm 3600 quadros com exceções fatais. **Só promover cache após aprovação.**
2. Repetir métricas em mais uma execução e testar jogabilidade real no BlastEm gráfico; procurar regressões invisíveis nas câmeras fixas.
3. Investigar triângulo E1 com desenho de portais e limites da janela/planos por cor de depuração.
4. Usar S0/S2 como canários de desempenho para **LOD de geometria** (clusters de degraus, visibilidade conservadora) e não substituir texturas distantes por cores: experiência M09 foi pior.
5. Se a otimização for aceita, combinar com render H32/H40 do Claudio sem alterar a interface HUD.
