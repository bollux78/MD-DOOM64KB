# DOOM-MD — HANDOFF PARA CLÁUDIO — R117 / PERFORMANCE APÓS R116

**Data:** 2026-11-03  
**Destinatário:** Cláudio  
**Objetivo:** encontrar novas otimizações reais de CPU e, sobretudo, melhorar **FPS mínimo** sem perda visual ou de estabilidade. Não reabrir paletas, Shadow, UI nem decisões gráficas fechadas.  
**Base de código:** `exp-chatgpt-r116-benchmark-accuracy-20261103` (R116, 10 demos, correção de cálculo FPS); esta branch de handoff: `exp-claudio-r117-performance-handoff-20261103`. **Não fazer merge automático.**

## 1. Baseline OFICIAL, imutável para comparações

**Procedimento único:** abrir ROM **PLAY** no BlastEm, **não alterar nenhuma opção**, selecionar **Benchmark > Run All Demos in Sequence**, aguardar as 10 demos e registrar a tela final. Clock **original ~7,67 MHz**, NTSC 60 Hz, **H40**, Crop padrão, **IA Normal**, Shadow OFF, paleta e demais opções no default da ROM. **Não usar overclock, IA Low, H32 ou crop máximo** para medir regressão/ganho oficial. Repetir em console físico após passar no emulador.

| Medida | R116 baseline oficial |
|---|---:|
| FPS médio geral | **4,96** |
| FPS mínimo (janelas 1 s) | **0,3** |
| FPS máximo (janelas 1 s) | **13,8** |
| Quadros totais | **45.706** |
| Tempo mostrado | **9.213,73 s** |
| Demos concluídas | **10/10** |
| FPS CHECK | **OK** |
| Menor zone livre total | **832 bytes** |
| Menor maior bloco contíguo livre | **448 bytes** |

Captura do usuário de 2026-11-03, configuração padrão/clock original. A contagem de quadros e tempo satisfazem 45.706 / 9.213,73 = 4,9606 FPS. O mínimo de 0,3 FPS **ainda pode incluir carga de mapa ou bloqueios**; investigar antes de interpretá-lo como velocidade de renderização isolada.

**Referência secundária, NÃO oficial:** H40/Crop padrão/IA Normal/Shadow OFF a **13 MHz**: **8,67 FPS** médios, mínimo 0,6, máximo 23,0, mesmos 45.706 quadros, 5.271,55 s, 10/10, zone total 832 B / maior bloco 448 B. O aumento acompanha aproximadamente o clock da CPU, sugerindo gargalo majoritariamente no 68000, mas isso é hipótese, não perfil por rotina. **Não misturar esta referência com o baseline.**

**Resultado descartado:** 13,65 FPS em H32/Crop Max/IA Low/overclock. A IA Low altera a reprodução das demos e invalida comparação de carga. Os 10/10 terminarem não demonstra equivalência de trabalho entre modos.

## 2. Contrato de qualidade e estabilidade

- **Imagem idêntica:** nenhuma alteração visível em texturas, dither, paleta, iluminação, recorte default, sprites, flats, HUD ou resolução. Não usar vhalf/farwalls/sky simplificado, que já foram rejeitados. Sem desativar IA normal.
- **Jogabilidade:** preservar o funcionamento de armas, inimigos, portas, colisão, saves, SRAM, som, menu, intermission e fim de mapa. Demos são cargas reproduzíveis; **não exigir sincronia perfeita com Doom PC**.
- **Segurança:** não aceitar travamento, `I_Error`, memória corrompida, acesso indevido a SRAM, falha de carregamento, crash em hardware ou corrupção visual. Não publicar ROMs, WADs nem demos em artifacts públicos.
- **RAM:** limite do projeto BSS de **57.920 B**, margem muito pequena (R116 PL aproximadamente 36 B; conferir novamente no build); não adicionar BSS inadvertidamente. `zone` tem folga crítica: 832 B total / 448 B maior bloco no teste completo. Prefira `.data` ou estruturas temporárias comprovadamente seguras, sem supor que `.data` seja RAM gratuita. Validar stack, heap e zone antes de aprovar.
- **Medição:** manter as 10 demos e a verificação `FPS CHECK OK`. O cálculo de FPS médio usa frames / tempo VBlank; mínimo/máximo em janelas de 1 s, com a correção R116 para evitar janelas parciais atravessando mapas. Se houver divergência, tratar como bug de instrumentação, não ganho.

## 3. Ordem de investigação sugerida (não implementar tudo junto)

### P0 — Identificar a causa do FPS mínimo

1. Instrumentar, **sem custo permanente na ROM final**, tempo/ciclos por etapa: renderer de paredes/colunas, flats de chão/teto, sprites/visplanes, BSP/visibilidade, `G_Ticker`/IA, VDP/DMA, trocas de mapa, descompressão e cópias para buffers. Preferir contadores de host, trace do emulador ou build de perfil separado.
2. Registrar **mapa + tic + janela de FPS + etapa dominante** para as piores janelas, principalmente E1M6 e E1M7. Separar explicitamente: gameplay ativo, carregamento, pausa/benchmark, VBlank/DMA e espera.
3. Avaliar o **1% low e percentil de frametime**, além do mínimo absoluto; não substituir o indicador oficial sem aprovação. Uma única janela de 0,3 FPS pode ser loading, não um frame de gameplay.
4. Verificar se os resets de janela do R116 são suficientes: descartar **somente** janelas parciais de transição; não ocultar engasgos reais nem adulterar o FPS médio.

### P1 — Renderer: gargalos do 68000

**Somente após perfil apontar custo dominante:**

- **Colunas de parede:** analisar loops internos e acesso a textura; reduzir multiplicações/divisões e endereçamento por pixel, hoist de invariantes por coluna/segmento, lookup de offsets, incremento fixo, saturação/clip e branches previsíveis. Candidatos a asm 68000 com A/B de ciclos; atenção a alinhamento, tamanho do código e acessos word/long.
- **Flats/visplanes:** reutilizar cálculos por scanline/span quando equivalentes; avaliar LUTs compactas versus cálculo; otimizar stride e acesso à memória mantendo exatamente os mesmos pixels e tons.
- **BSP/oclusão:** early-out apenas para regiões realmente fora do viewport ou comprovadamente ocultas, sem esconder geometria. Investigar trabalho duplicado de clipping e transformação; nunca voltar a farwalls/sky simplificado.
- **Sprites e composição:** evitar trabalho repetido em objetos totalmente ocultos; ordenar loops/memória, reduzir branch/multiply; manter ordem de desenho e pixels idênticos.
- **Transferência VDP/DMA e double buffer:** medir espera por VBlank e custo de cópia; otimizar batching/alinhamento sem aumentar risco de DMA/VRAM, nem quebrar H32/H40, HUD ou menus.
- **IA Normal:** otimizar o caminho normal sem trocar para IA Low. Verificar custo de varredura de thinkers, colisões e LOS em cenários carregados. Não alterar regras observáveis nem criar novas dessincronizações gratuitas.

### P2 — Memória e robustez

- E1M6 teve **menor maior bloco livre 448 B** no Run All padrão: investigar fragmentação e picos por mapa; inspecionar lifetime de alocações, temporários, cache de lumps e transições. Otimizar memória sem mascarar corrupção.
- Testar guard/canários de stack/zone e SRAM em ROM diagnóstica separada, sem tocar saves reais; testar morte/respawn, E1M1→M2, E1M8, menu durante gameplay e save/load.
- Priorizar **melhorias que aumentem margem de memória e reduzam stalls** mesmo quando o FPS médio for modesto, desde que sem regressão visual.

## 4. Metodologia obrigatória para aceitar ganhos

1. Congelar a base e registrar commit SHA, ROM SHA256, modo, clock e parâmetros do benchmark.
2. **Uma otimização por commit/flag de build**; produzir ROM controle e ROM candidata com condições idênticas. Testar primeiro cena/mapa pesado curto, depois Run All completo **10/10**.
3. Para cada candidato, entregar tabela com: `mudança | rotina | ciclos estimados/medidos | FPS médio | FPS mínimo | FPS máximo | zone total/bloco | BSS | tamanho ROM | resultado de segurança | visual idêntico? | decisão`.
4. Comparar com baseline **4,96 FPS / 0,3 mínimo**. Melhorar FPS médio **sem piorar mínimo**, ou melhorar mínimo com média preservada; quando houver trade-off, apresentar dados para decisão, sem integrar automaticamente.
5. Testar **acumulação A+B** explicitamente: ganhos individuais não são necessariamente aditivos. Manter somente combinações que melhoram os resultados e preservam integridade.
6. Não aceitar resultados apenas de `r116_norender=1`: essa sonda desliga renderização, não valida VDP/DMA. Executar ROM PLAY com vídeo ligado e benchmark completo; testes no console são etapa final.
7. **Nunca finalizar/mesclar** uma versão sem autorização. Documentar reversão rápida, logs e SHA de cada build.

## 5. Infraestrutura e pontos de partida

- Repositório: https://github.com/bollux78/MD-DOOM64KB
- Branch de código-base: `exp-chatgpt-r116-benchmark-accuracy-20261103`
- Handoff Run All anterior: `docs/agent-handoffs/R116-RUNALL-OPTIONS.md` (algumas notas de validação ficaram desatualizadas após os testes manuais completos; usar números deste handoff).
- Plano de segurança: `docs/agent-handoffs/R116-AUTOMATED-REGRESSION-PLAN.md`.
- Aplicação R116: `scripts/lab/apply_r116.py`.
- Benchmark: `src/r22_benchmark.inc` e scripts de build/patch da cadeia R60→R116.
- Workflow do runner: `.github/workflows/r116-claudio-demotest.yml`; sonda `scripts/lab/r116_demo_probe.py`; sonda de transição `scripts/lab/r116_sequence_smoke.py`.
- Exemplo de build anterior com testes por mapa: https://github.com/bollux78/MD-DOOM64KB/actions/runs/41567872714
- Teste de transição: https://github.com/bollux78/MD-DOOM64KB/actions/runs/41568242897
- Correção posterior do FPS/tempo e janelas: https://github.com/bollux78/MD-DOOM64KB/actions/runs/41637745015
- ROMs privadas somente no runner `/home/dan/Projetos/Personal/r116-demotest/run-<runid>-1/`, **não** nos artifacts públicos.

## 6. Entrega solicitada ao Cláudio

**Primeira entrega:** análise de perfil com os **3 maiores gargalos demonstrados**, origem provável do FPS mínimo e **5 propostas ordenadas por ganho esperado / risco / esforço**, com ciclos estimados e critérios de teste.  
**Segunda entrega:** implementar a proposta de menor risco com maior retorno, construir A/B, validar memória, pixel-identidade e 10/10 demos; fornecer SHA e relatórios.  
**Terceira entrega:** tentar acumular somente otimizações aprovadas, comparar contra os 4,96 FPS oficiais e documentar por que ganhos somam ou não somam.

**Pergunta central:** há caminho para elevar o FPS médio e, especialmente, os piores momentos do gameplay **sem mudar um único pixel**, mantendo 10/10 demos e melhorando — ou pelo menos não reduzindo — a segurança de memória?

**Importante:** o usuário decidiu por **um único teste padrão**. Não solicitar matrizes H32/H40, IA Low, crop máximo ou overclock para provar ganho. Se for necessário um diagnóstico pontual, fazê-lo separadamente e deixar claro que **não** substitui o benchmark oficial.
