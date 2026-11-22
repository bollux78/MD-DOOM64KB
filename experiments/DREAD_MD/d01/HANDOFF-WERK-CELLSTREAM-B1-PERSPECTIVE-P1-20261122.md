# HANDOFF — DOOM MD / Ferret CellStream B1 + perspectiva P1
Data: 22/11/2026. Destinatário: ChatGPT Work (Werk). Repositório: https://github.com/bollux78/MD-DOOM64KB

## 1. Missão e prioridades
Continuar a DREAD D01 **completa** (E1M1–E1M9) sem tocar na branch `main`, versões estáveis ou branch do Cláudio. Prioridades:
1. **P1 — perspectiva / continuidade visual das paredes:** usuário mostrou Ferret Alpha 2 com paredes contínuas e D01 com paredes visualmente segmentadas. Diagnosticar e corrigir perspectiva preservando cores, texturas e jogabilidade. Esta é a mais recente solicitação técnica, deve ter prioridade.
2. **B1 — stream de visibilidade inspirado na Ferret:** concluir/validar primeira implementação existente, medir FPS e demonstrar igualdade visual. NÃO misturar código P1 e B1 antes de validar ambos isoladamente.
3. **Benchmark e relatório de tela inteira:** produzir uma tela de benchmark útil dentro da ROM e um relatório HTML fullscreen no artefato CI, com métricas por etapa, custo relativo, regressões e verificações visuais; nunca chamar uma otimização de aprovada sem FPS e pixels.

## 2. Estado real das branches
- **Experimentação B1:** `exp-werk-ferret-cellstream-b1-20261122`.
- Último commit *verificado dos arquivos B1* nesta passagem: `2caecf165963d6964ff9b4aaded86091f3a870a1` (guardas de bounding box no stream). A branch também contém commits anteriores `22d365fa` (relatório com custos), `8897d8ca` (leitura de durações), `5375b68d` (stats), `0899beb5` (temporização), `68e2aa5f` (tela dentro da ROM), `76cb245b` (artefatos), `8bc509d` (gerador HTML). Verifique `HEAD` antes de trabalhar; não confundir o HEAD da branch com o SHA de um workflow antigo.
- **A1 anterior:** `exp-werk-ferret-a1-20261121`, commit de correção `2e636ccd`; não aprovada como otimização.
- **Controle historicamente exato:** `exp-werk-dread-exato-input-vblank` / `42f17f26b1e3187ad7995799891cb50bd090e66c`.
- **Variantes CONTROL/PATH/RAW/ALL/LEGACYSEG:** `exp-werk-dread-precalc-20261121`, commit `a06104e4aa54af0e0d27c6853c8c16a51d5d761f`.
- Referência geral: `experiments/DREAD_MD/d01/HANDOFF-FERRET-A1-CONTINUIDADE.md` na branch A1; pesquisas `research/ferret-alpha2/README.md`, `PHASE2.md`, `PHASE3-NAVEGAVEL.md` no commit `56813b088369cee0ccc23257abd04e704c0a277f`.

### Status CI na última consulta
O workflow **DREAD Ferret B1 - cell-stream spawn and fullscreen report** foi acionado muitas vezes por commits sucessivos. O run mais recente associado à versão com guardas é:
https://github.com/bollux78/MD-DOOM64KB/actions/runs/45017272478 (job `137192177717`).
Na última consulta estava **in_progress**, em **Bootstrap Marsdev on cache miss**. NÃO havia métricas B1 nem ROM validada. Reconsulte imediatamente workflow, logs e artefatos; se compilação falhar, corrija **somente** na branch experimental.
Há runs anteriores ainda ativos `45016865301`, `45016874895`, `45017019336`, `45017173115` etc.; NÃO use seus resultados como representativos do último commit.
Observação: o runner hospedado usa `ubuntu-24.04`, pacote `doom-wad-shareware` (`/usr/share/games/doom/doom1.wad`), Marsdev/SGDK via `scripts/lab/bootstrap_marsdev.sh`. Cache do compilador pode faltar. NÃO precisa ligar o PC do usuário. Evitar nova rodada de commits que crie dez runs paralelos antes de resolver o compilador.

## 3. Resultados efetivamente medidos até agora
### A1
Em MAME, 1.200 VBlanks NTSC depois de aquecimento:
- CONTROL 87 frames publicados / 1200 VBlanks = **4,3444 FPS**.
- A1 original 114 / 1200 = **5,6927 FPS**, mas **REPROVADA:** o usuário testou e observou telas pretas e tiles corrompidos. O salto rápido em `src/colasm.s` pulava recarga de clipping `d0/d1` e índice `d6`; ganho inválido.
- A1 após correção (`2e636cc`): 87 / 1200 = **4,3444 FPS**, 0% ganho. Mesma contagem NÃO prova equivalência de framebuffer.
Runs: https://github.com/bollux78/MD-DOOM64KB/actions/runs/44976266137 e https://github.com/bollux78/MD-DOOM64KB/actions/runs/44977536557.

### Variantes pré-cálculo (captura enviada pelo usuário)
BlastEm, benchmark de percurso **312 quadros**, não spawn parado:
- ALL 3,61 FPS; LEGACYSEG 3,61; PATH 3,61; CONTROL 3,62; RAW 3,62.
- Todas exibem 3,4 FPS instantâneo, 40 segmentos na captura.
- Variação 0,01 FPS sem significância prática. LEGACYSEG **não** demonstrou ser mais rápida.
- Os 250–273 fps na barra de título do BlastEm indicam velocidade do emulador, NÃO FPS do jogo.
Não comparar diretamente benchmark de rota BlastEm 312 quadros com spawn MAME publicado.

### Ferret Alpha 2 de referência
- Original Ferret no spawn via Genesis Plus GX: **5,9107 FPS sem SRAM**, **8,2554 FPS com SRAM16**. SRAM opcional, NÃO presumir no Everdrive.
- Perfil sem SRAM: lista/candidatos 7,706 ms, paredes 64,281 ms, sprites 3,413 ms, cena 3D 75,423 ms, conversão/escrita CPU→VDP 59,748 ms; etapas são inclusivas/stalls e NÃO devem ser somadas indiscriminadamente.
- A reconstrução Ferret v03 feita por agentes era incompleta e lenta (~2,069 FPS); NÃO substituir o D01 por ela.
- Ferret original usa BSP para célula/posição e stream pré-processado de tokens para ordem/visibilidade de paredes e atores. A D01 já tem PVS e BSP, ColRec sequencial, assembly otimizado e origem vertical exata 16.16; não confundir engenharia existente com novidade.

## 4. Implementação B1 — o que está no repositório
Arquivos relevantes na branch B1:
- `experiments/DREAD_MD/d01/src/render.c`: `DREAD_CELL_STREAM`. Gera lista de tokens BSP/PVS por posição inteira, guarda de bbox de ramo distante, replay da lista e fallback para BSP se overflow. Contadores `cell_stream_rebuilds`, `cell_stream_hits`, `cell_stream_fallbacks`, `cell_stream_last_len`. A ordem depende de posição, enquanto o recorte de bbox depende de ângulo e colunas fechadas; **verificar cuidadosamente a semântica exata**.
- `src/main.c`: flag `DREAD_CELLSTREAM_REPORT`; tela de relatório ao terminar benchmark interno de rota, com START para reiniciar.
- `tools/cellstream_report.py`: HTML responsivo de tela inteira + `benchmark.json` e diagnóstico. Prevê medição de visibilidade, geometria, sprites e renderer.
- `.github/workflows/dread-ferret-cellstream-b1-20261122.yml`: compila CONTROL e CELLSTREAM sobre WAD shareware e mede publicações NTSC MAME via Lua, prepara relatório/artifacts.

**Atenção técnica B1:** protótipo conservador, inspirado no princípio Ferret, **não** uma transcrição bit a bit dos tokens da ROM Ferret. Checar: compile sem símbolos/declarações anteriores ao uso; semântica dos guardas e saltos; preservação de portas, atores e recolhimento de sprites antes das paredes; overflow e fallback; mudança de mapa (R_Init), mudança de modo gráfico e rotação sem deslocar a câmera; RAM total e pilha 68000; contagem de stream quando câmera permanece na mesma posição inteira. Em particular, o percurso original evita ramos inteiros por PVS e bbox e acumula `closed`; a versão de stream deve produzir **ordem de folhas e pixels equivalentes** nos ângulos extremos, não apenas FPS alto.
**Tempo por etapa** atualmente usa HV/linhas de vídeo (`now_lines`), de resolução grosseira e que inclui stalls/interrupções. Validar comportamento com rollover, intervalos e contadores de 32 bits, e não declarar estimativas como cycles exatos. Isolar também DMA/transferência se viável. Se benchmark interno fullscreen tiver incompatibilidade com SDK/HBlank/JOY, corrigir, compilar e testar, sem comprometer versão jogável.

## 5. PRIORIDADE NOVA — perspectiva das paredes (P1)
O usuário enviou duas capturas: Ferret Alpha 2 com corredores e paredes visualmente contínuos; D01 com superfícies que parecem segmentadas, contornos/tetos e linhas de textura com mudanças abruptas entre segmentos. **As câmeras não estão no mesmo ponto/direção**, logo o defeito ainda precisa de diagnóstico quantitativo, e não se pode presumir uma causa só pela imagem. Há evidência visual do problema percebido, mas ainda não há prova de qual equação falha.

Pontos do código a estudar em `src/render.c` da D01:
- `cam` (transformação), `xform` cache, `proj` (RCPF e arredondamentos), `inv_z`, `yrow/yrows/ydelta`, `draw_seg` (near plane), `draw_seg_body` (invZ e u/z, `lstep`, `advance`, `seg_rows2/seg_rows1`, `seg_anchors`).
- `src/segasm.s`: geração por coluna; `src/colasm.s`: clipping/scalers e origem vertical 16.16 exata. `r_ash` controla intervalo de âncoras para textura; confirmar se erro de perspectiva é geométrico, interpolação de U, projeção Y, quantização de alturas ou conteúdo/segmentação do WAD.
- `R_SetMode`: 160x72 logical no row-doubled H40 e 144 linhas no column-doubled; não atribuir automaticamente toda a aparência à baixa resolução.
- Segs adjacentes de uma mesma linha devem manter coerência de coordenadas 16.16, alturas de teto/piso e fase de textura em cada borda comum, inclusive com near clipping. Considerar tabelas de teste que comparem extremos compartilhados em 16.16 antes e depois do rounding.
- Antes de editar, produzir um **diagnóstico visual + numérico** por posição/ângulo reproduzível: segmentos visíveis, vértices, z, screen X, Yc/Yf, deltas, u/z, âncoras, diferenças nos limites, pixels/tiles. Testar se junções estão realmente descontínuas ou se a textura do DOOM dá essa impressão.
- Fazer variante **PERSPECTIVE P1 em branch própria** derivada de um controle estável/exato, **não** da B1 ainda não aprovada. Comparar viewport em poses idênticas via scripts emulador/host. Preferência por pequenas correções geométricas e testes antes de trocar arquitetura. Pixel equality com controle não é exigível se a finalidade explícita for corrigir imagem; mas todas as diferenças devem ser explicadas e aprovadas visualmente, sem corrupção ou transparências involuntárias.

## 6. Benchmark obrigatório e relatório fullscreen
O usuário pediu explicitamente relatório em tela inteira **com todas as informações relevantes para orientar próximas otimizações**. Entregar:
- Identificação de versão, branch, commit, flags, compilador, WAD/mapa e modo gráfico.
- Duas séries separadas: **spawn parado** (FPS de publicações reais, 1.200 VBlanks NTSC após aquecimento) e **rota fixa** (312 imagens, mesmos inputs/cenas); média e variação em >=3 repetições quando possível. MAME vs BlastEm não devem ser misturados.
- Estatísticas por quadro de nós, subsectors, segs, colunas e âncoras; stream rebuild/hits/fallback; atores e sprites.
- Breakdown de CPU: seleção BSP/PVS, projeção/setup, desenho e amostragem de textura, sprites, framebuffer/conversão, VRAM/DMA e interrupções — indicar claramente o que está **medido**, **estimado** ou **ainda indisponível**.
- Comparação de screenshots/framebuffer CONTROL × variante nos mesmos ângulos/posições (spawn, extremos, portas/portais, corredores, mapas diferentes). Diferenças por pixel, hashes e imagens de diff; registradores e modos H32/H40, row/column-doubled. Sem prova de pixels, declarar **não validado**.
- Metadados de artefatos (.bin jogáveis, hashes SHA-256, logs, JSON/CSV, HTML fullscreen), mensagem de aprovação/rejeição. Guardar logs de falha mesmo com status CI verde.
- Dentro da ROM, manter START funcional durante jogo normal; fullscreen de benchmark somente ao fim do modo benchmark, oferecendo retorno/reset. Não bloquear controle usual nem mascarar renderer.

## 7. Ordem operacional para Work
1. Buscar HEAD da B1 e status do run `45017272478`; verificar se Marsdev compilou, ler logs, corrigir erros na B1 se existirem. Não tratar runner `in_progress` como resultado.
2. Executar CONTROL vs B1 e validar saída `SPAWN_RESULT`, `STREAM_RESULT`, `PROFILE_RESULT`; corrigir gerador HTML e reportar FPS reais; validar visual e gameplay antes de afirmar ganho.
3. Em paralelo **sem misturar alterações**, criar branch P1 a partir do controle exato e investigar geometricamente os defeitos de continuidade das paredes. Criar ferramenta de diagnóstico por coluna/segmento e testes host determinísticos.
4. Corrigir perspectiva aos poucos, compilar ROM P1 e comparar capturas com posições sincronizadas. Priorizar integridade visual, aceitar custos se justificáveis, mas quantificar cada um.
5. Produzir dois relatórios finais separados (B1 e P1) com links para GitHub Actions/artefatos e resumo do que melhorar em seguida. Opcionalmente só depois comparar combinação B1+P1.
6. Nunca editar `main` ou branch do Cláudio, nunca distribuir ROM Ferret original/WAD/ELF proprietário, jamais promover variante defeituosa.

## 8. Critérios de sucesso
- B1: idêntica à referência nas cenas onde visibilidade não deve alterar pixels; fallback seguro; FPS repetível, e relatório claro.
- P1: paredes geometricamente contínuas em posições idênticas, sem falhas de tiles, faixa preta ou textura; diferença visual intencional demonstrada e sem perda de features.
- Benchmark: relatório fullscreen confiável e autoexplicativo, dados reproduzíveis, não apenas o FPS do emulador.
- Se as hipóteses não gerarem ganhos ou quebrarem imagem: registrar e descartar, voltar ao controle.

**Mensagem ao Werk:** execute as investigações e commits diretamente no repositório. Não peça para o usuário atuar como mensageiro entre agentes. O usuário pode testar ROMs em hardware e enviar VRAM/CRAM/mapa de tiles no BlastEm quando estritamente necessário. Sempre fornecer um ZIP/artefato claro e indicar explicitamente o que foi verificado e o que permanece pendente.
