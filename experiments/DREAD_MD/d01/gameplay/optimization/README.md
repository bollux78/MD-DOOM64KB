# DREAD C7 - rodada de otimização

**Benchmark canônico dos projetos Doom:** [DEMO3 integral em E1M7](../../../../../docs/benchmarks/PADRAO-DOOM-DEMO3-E1M7.md). O trecho automatizado de 312 quadros é somente smoke test e não substitui a demo completa.

> **Benchmark da C7 experimental (atualização):** o menu usa somente a gravação `DEMO3` do WAD; a rota fixa de E1M1 e seu relatório antigo são excluídos da ROM `DREAD_EPISODE`. Os modos 1 e 2, que o MAME solicita via `bench_req`, agora percorrem os primeiros 312 quadros renderizados da mesma `DEMO3` (IA desligada / ligada). O modo 3 do menu percorre a gravação inteira e mostra FPS, tempo em VBlanks, variante e atividade de combate. A física é aproximada na C7; o percurso não é bit a bit equivalente ao Doom original. Revisar os resultados de combate segundo as regras de comparabilidade abaixo.


Base congelada: `c816e6c72a8fc6a3bc989b347ea7166fda835893` (última C7 NORMAL validada no boot). A C7 estável não é alterada. Handoff de referência: DREAD-OTIMIZACAO-HANDOFF.zip (22/11/2026).

Esta rodada foi revisada em 23/11/2026 depois de ler o código de cada variante e de testar a geometria no renderizador de host: WAD do Doom 1 shareware (E1M1 a E1M9, 2000 vistas cada) e, para achar os bugs, Freedoom (3000 vistas). Os números do host são de **trabalho do renderizador** (segs, nós da BSP, colunas) e de **pixels**. Eles não são FPS do Mega Drive.

## 1. Resultado da revisão (o que estava errado, o que não rende)

| Variante original | Veredito | Evidência |
|---|---|---|
| GEO_SAFE | **tinha bug, corrigido; removida da rodada porque não rende no Doom 1** | Ver 1.1: remove 0 segs em 7 dos 9 mapas do Doom 1 e no máximo 7 em E1M8. |
| GEO_STEPS | **removida da rodada** | No Doom 1 reduz no máximo 2,4% dos segs (E1M2) e 0 a 0,8% nos demais; muda os pixels em 5–14% das vistas em 8 dos 9 mapas (até 83% dos bytes de uma vista; E1M8: só 4 vistas, máximo 0,71%) e altera colisão. |
| TEX2, TEX4 | **removidas da rodada** | O blob de texturas tem o mesmo tamanho (`conv.py` grava `W2 × H2` colunas independente do fator; só repete texels). Os escalonadores leem os mesmos bytes e escrevem os mesmos pixels. Não há caminho para reduzir CPU. Só piora a imagem. |
| AI6, AI4 | **AI6 mantida, AI4 removida**; ver 1.2 | O período longo também desacelera os monstros de forma desigual. |

As variantes removidas continuam suportadas em `variant.sh` (`AI4`, `TEX2`, `TEX4`, `GEO_STEPS`) para quem quiser medir; só saíram da rodada padrão.

### 1.1 GEO_SAFE: dois bugs reais

O modo `merge` removia segs "invisíveis" (mesmo setor dos dois lados, sem textura). Dois erros:

1. **A PVS era gerada com a geometria já reduzida.** Esses segs são portais de visibilidade: sem eles a PVS perde ligações entre folhas.
2. **Folhas ficavam sem nenhum seg** (uma folha de um único seg invisível). O `pvsgen` amostra pontos a partir dos segs da folha; sem segs não há o que amostrar. Causa provável (não isolada das duas correções): as vistas de dentro dessas folhas saíam com **o quadro inteiro sem pintar** (a cor 14 de debug).

Medição no host antes da correção (Freedoom E1M1, 3000 vistas dentro do mapa): **275 vistas diferentes (9%)**, **10 quadros totalmente em branco (0,33%)**. Correção:

- `tools/map_reduce.py`: uma folha nunca fica vazia.
- `tools/conv.py`: grava `mapdata_pvs.c` com as tabelas de seg/subsetor **sem redução**; `tools/build_map.sh` gera a PVS a partir dele. O ROM continua com as tabelas reduzidas.

Depois da correção:

| Mapa (Freedoom) | Vistas diferentes | Quadros em branco | Maior diferença | Segs | Nós BSP | Colunas visitadas |
|---|---|---|---|---|---|---|
| E1M1 | 29 / 3000 (0,97%) | 0 | 0,34% dos bytes | -1,53% | 0,00% | -1,53% |
| E1M2 | 2 / 3000 (0,07%) | 0 | 3,0% | -0,46% | 0,00% | -0,46% |
| E1M5 | 0 / 3000 | 0 | 0 | -0,12% | 0,00% | -0,12% |

**Doom 1 shareware (WAD real), `merge` contra CONTROL, 2000 vistas por mapa:**

| Mapa | Segs CONTROL → merge | Vistas diferentes | Quadros em branco | Trabalho de colunas |
|---|---|---|---|---|
| E1M1, E1M2, E1M3, E1M5, E1M6, E1M7, E1M9 | iguais (0 removidos) | 0 | 0 | 0,00% |
| E1M4 | 1172 → 1170 | 0 | 0 | -0,12% |
| E1M8 | 586 → 579 | 0 | 0 | -0,03% |

Em todos os 9 mapas a imagem saiu **idêntica pixel a pixel** e o gate passou. Só que **no Doom 1 o GEO_SAFE praticamente não faz nada**: a ROM de E1M1 (a rota do benchmark) seria idêntica à do CONTROL. Por isso saiu da rodada. As reduções de Freedoom (acima) só servem para mostrar os bugs.

Invariantes conferidos: o `mapdata.c` do CONTROL tem o mesmo SHA-256 de antes das mudanças no conversor (o CONTROL não muda), e a `pvs.c` do GEO_SAFE é idêntica à do CONTROL nos três mapas do Freedoom.

Conclusões:
- No Freedoom o GEO_SAFE mostrou diferenças só em pixels isolados de borda; no Doom 1 não houve diferença nenhuma. A classe continua `near_exact` (bit a bit idêntico não é prometido).
- **Ganho no Doom 1: ≤0,12% do trabalho de colunas e 0% na BSP.** Não vale uma build.
- A fusão colinear (`merged_collinear`) deu **0** nos três mapas: dentro de uma folha convexa quase nunca há dois segs consecutivos na mesma reta. `merge` e `safe` saem iguais.
- O gate é `verify_geo_exact.sh` (ver 4). O CI roda com o WAD do Doom 1 em E1M1, E1M2, E1M5 e E1M8.

### 1.2 IA: período longo desacelera os monstros (e de forma desigual)

`chase` é o número de VBlanks por passo de caminhada (zombie 7, sergeant 6, imp/baron/caco 5, demon 4, soul 8), e cada ação de IA anda um passo fixo. Com período P, um monstro age a cada `ceil(chase/P)*P` VBlanks. Já o CONTROL (P=5) anda o zombie a 8/10 por VBlank (o projeto do Doom seria 8/7). Com AI6 (P=10) todos andam 1 passo por 10 VBlanks: imp, baron e caco ficam a **metade** da velocidade do CONTROL, o demon fica a metade, o zombie e o sergeant não mudam. Isso não é uma otimização neutra.

- **AI6** (mantida): P=10, sem correção. Serve como pior caso de dificuldade mais baixa.
- **AI6S** (nova): P=10 com `-DDREAD_AI_SPEED_COMP`. Cada tipo anda um passo mais longo, `speed × gap(10) / gap(5)`, mantendo a velocidade média do CONTROL. O passo é limitado a 16 unidades, porque `blocked_from()` (main.c) só testa linhas a até R=16 do **destino**; um passo maior poderia atravessar uma parede fina. Por isso o demon (20 → 16) e, com P=15, quase todos ficariam mais lentos. **Por isso AI4 saiu e não existe "AI4S".**
- O movimento fica mais "em saltos" (passos de até 16 unidades a cada 10 VBlanks) e a animação de caminhada avança uma vez por ação. Isso é custo de jogabilidade, não de FPS.

## 2. Variantes da rodada

| Variante | Classe | Mudança | O que muda para o jogador |
|---|---|---|---|
| CONTROL | baseline | C7 original (easy, IA 12 Hz, projéteis 20 Hz) | nada |
| AI6 | gameplay_change | IA a 6 Hz sem correção | monstros mais lentos; metade da velocidade para imp, baron, caco e demon |
| AI6S | gameplay_change_speed_kept | IA a 6 Hz, passo proporcional | mesma velocidade média, movimento mais "em saltos" |

Fora da rodada, ainda suportadas em `variant.sh`: GEO_SAFE, ALL (AI6S + GEO_SAFE), AI4, TEX2, TEX4, GEO_STEPS.

A rodada tem só variantes de IA, e elas são trade-offs de jogo. Antes de olhar o FPS delas, leia a regra 1 da seção 3: se a IA custar pouco no CONTROL, nem as variantes importam.

## 3. Como ler os números

- **Render (modo 1):** IA desligada. Mesma carga entre variantes que não mudam o renderizador. É a medição mais limpa.
- **Combate (modo 2):** IA ligada. **Não é a mesma carga entre variantes de IA:** os monstros agem diferente, então a rota diverge. `pack_matrix.py` marca `combat_comparable = False` para as classes de IA. Para elas, olhar o custo da IA, não o FPS total (ver regra 1 abaixo).
- **Histograma de VBlanks por quadro** (`vblank_histogram`, `vblanks_per_frame_mean`): o FPS médio (`frames*60/vblanks`) esconde a distribuição. Nas medições do D01, o mesmo trecho variava de 4 a 15 VBlanks por quadro.
- **Hash visual** (`visual_hash`): hash do quadro final de cada modo (amostragem em passo 2). Serve para detectar mudança de imagem. Para GEO_SAFE o gate de verdade é o do host (`geo_gate_pass`).
- **Emuladores:** MAME tem outra temporização de VDP. Antes de promover qualquer variante, repetir em GPGX ou BlastEm e no console.

### Regras de decisão depois da rodada

1. **A IA importa?** Calcule `render_fps / combat_fps − 1` no CONTROL. Se for menor que 5%, nenhuma variante de IA pode render mais que isso: descarte AI6 e AI6S.
2. **Ruído:** rode cada modo duas vezes (o workflow já roda uma vez por modo; rode a matriz duas vezes se o resultado ficar perto do ruído). Diferença menor que a variação entre repetições não é resultado.
3. **Promoção:** classes de IA só por escolha do dono do projeto, depois de jogar. Nada vai ao console antes do teste manual em BlastEm e no console.

## 4. Verificação no host (sem ROM)

`verify_geo_exact.sh WAD "E1M1 E1M2" [VISTAS] [SAIDA] ["control merge"]` converte cada variante, gera a PVS da geometria completa, compila o renderizador de host, renderiza as mesmas vistas (posições dentro do mapa escolhidas pelo CONTROL) e compara os framebuffers. O gate de `near_exact` é: nenhum quadro em branco, no máximo 2% das vistas diferentes, nenhuma vista com mais de 5% dos bytes diferentes. Escreve `summary.json`. O job de compilação roda a verificação quando a variante GEO_SAFE é compilada (hoje fora da rodada) e grava `geo-verify-GEO_SAFE.{txt,json}` no ZIP.

`host/host.c cmp N [POSFILE [DUMPFILE]]` é o modo usado: imprime hash e contadores de trabalho (`segs`, `nodes`, `subs`, `colvisits`) por vista. Esses contadores mostram, antes de gastar uma build, se uma mudança pode ser mais rápida.

## 5. Propostas próprias (fase seguinte, **não** entram nesta rodada)

Nenhuma foi medida em 68000. Cada uma diz como provar antes de gastar uma build.

1. **Segundo estágio do laço de colunas (maior alvo conhecido).** As bordas da parede em registradores com `add/addx`, registro sequencial por coluna lido com `(a4)+`, partes como casos separados. O D01 mostrou ~60 instruções por coluna, quase todas com leitura/gravação em memória. Teste: pixels idênticos no host e benchmark no D01 (spin de 1500 quadros no início de E1M1, hoje 6,39 FPS).
2. **BSP e projeção ≈ 27% do tempo no D01.** No host (Freedoom E1M1) são ~86 nós e ~50 folhas visitados por vista para ~45 segs desenhados. Ideia: lista de segs pré-ordenada por folha/direção para pular nós sem desenho. Teste: contadores `nodes`/`subs` do `cmp` antes e depois, pixels idênticos.
3. **Ajuste da PVS com oráculo.** A PVS é **amostrada** (`pvsgen.c`: 16 direções por folha + dilatação pelos vizinhos), não um flood conservador. No host a PVS atual já erra em ~6% (E1M1), ~2,6% (E1M2) e 0% (E1M5) das vistas aleatórias, em poucos bytes (`host x sweep 3000` compara PVS ligada e desligada). A dilatação dobra o conjunto visível (117 contra ~63 folhas no E1M1 do D01). Um ajuste da dilatação por distância é só de tempo de build, sem risco no ROM; o preço é medir buracos contra nós visitados.
4. **Custo da IA antes de mexer nela.** Regra 1 da seção 3. Se a IA for maior que ~5%, o alvo é o custo por ação (`look()`/`can_see()`, `try_move`, laço sobre todos os atores), não a frequência.
5. **Pico de quadro.** O histograma mostra se AI6/AI6S trocam FPS médio por quadros longos (a IA só roda a cada 10 VBlanks, mas o trabalho junto cai num quadro).

## 6. Arquivos

- `variant.sh`, `compile_one.sh`: compilação independente por variante. Publica `DREAD-C7-OPT-<variante>.elf` só quando o WAD é o `doom1.wad` shareware (para perfil por função); com outro WAD o ELF fica privado no runner (o GEO_SAFE roda a verificação do host no fim).
- `bench_mame.py`, `bench_mame.lua`: benchmark MAME (histograma, hash visual, `ai_active`).
- `verify_geo_exact.sh`, `host_stubs.c`, `../../host/host.c` (modo `cmp`): verificação no host.
- `pack_matrix.py`: ZIP com as ROMs e CSV/JSON com classe, FPS, deltas, `render_pixels_equal_control`, `combat_comparable`, `geo_gate_pass`.
- `geometry/`: números de SEGS por mapa. Não é medida de FPS.

## 7. Workflow e segurança

`.github/workflows/dread-c7-optimization-matrix.yml`: o runner self-hosted compila; os runners hospedados fazem o benchmark e montam o ZIP.

O job de compilação roda em runner self-hosted em repositório público. Restrinja quem pode fazer push no branch, ou use um runner dedicado ao seu repositório, antes de aceitar código de terceiros. O workflow `dread-c7-optimization-bench-smoke.yml` baixa o artefato de uma run fixa; troque o `run-id` antes de reutilizá-lo.

## 8. Limites desta revisão

- Os testes do host não desenham atores (só paredes, planos, céu e coisas estáticas).
- O host usa os caminhos em C do renderizador e não roda o assembly do 68000. A equivalência de pixels vale para os dados e para a lógica em C; ela não prova a ausência de efeitos no assembly nem no hardware.
- `AI6S` foi compilado no host só para sintaxe (`actors.c`); o comportamento dos monstros não foi jogado.
- Nada foi medido em FPS do Mega Drive.

## Decisão do dono (2026-11-23): IA vira opção de menu
Depois da otimização de `scenery_blocked`/`World_Shoot` (commit a43bad5), AI6 e AI6S ganharam só 2% e 3% de FPS em combate sobre o CONTROL (antes 4% e 5%). Decisão: AI6/AI6S saem da rodada. No lugar, o menu do jogo (START) ganhou **IA: 100% / 50%** (`Actors_SetAIHalf`): 100% = período 5 (CONTROL); 50% = período 10 com o passo proporcional da AI6S (velocidade mantida, passo limitado a 16). O padrão é 100%. A rodada passa a ter só CONTROL; `variant.sh` continua aceitando AI6/AI6S para teste pontual.

## Perfil medido (2026-11-23, DEMO3 E1M7, ROM CONTROL com ELF, amostragem por PC no GPGX headless)
Ferramenta: amostra o PC a cada linha, mapeia símbolos e linhas DWARF do ELF publicado (shareware). Depois do commit 46ed282:
| Bloco | % do tempo | Observação |
|---|---|---|
| `seg_columns` (contabilidade por coluna) | 11,7 | custo está no número de colunas, não em instruções soltas |
| `render_node` | 9,8 | distribuído: laço de segs 3,2 / vértices 2,1 / caminho dos nós 2,0 / coisas do subsetor 1,3 / muls 0,8 |
| `tex_native` | 8,5 | ~440 ciclos por chamada; já enxuto |
| escalonadores `native_b_N` | 8,3 | escrita de pixel, é o piso |
| `draw_seg_body` + `proj` + `native_anchors` | 15 | preparo por parede |
| sprites (`Actors_Draw`, `draw_sprite`, `R_AddSprite`) | ~8 | `Actors_Draw` caiu 28% com as listas por quadro |
| preenchimento de teto/piso (`span_fill`, núcleos) | ~2,6 | **fundir 4 colunas não compensa** (ganho máximo ~1,5%) |
| jogo (IA, colisão, tiros) | ~8 | antes ~16%; `scenery_blocked`/`World_Shoot` otimizados |
| `__mulsi3` restante | 3,6 | `main` (blocked_from inlinado) 1,6; resto pulverizado |

Resultado acumulado no MAME (E1M1, 312 quadros): render 3,995 → 4,252 FPS (+6,4%); combate 3,485 → 3,931 FPS (+12,8%). Ganhos restantes exigem mudança de arquitetura (menos colunas processadas), não microajuste.

## Medições no console, DEMO3 E1M7 (dono, 2026-11-23, ROM do commit 950271)
Jogo idêntico em todas as telas (11 acordados, 155 ataques recebidos, 2 abatidos), exceto com IA 50% (9 / 36 / 2). A CONTROL de ontem (sem as otimizações de código de hoje) fez 2,90 FPS, 155 ataques.
| Configuração (IA 100%, resolução padrão) | FPS | Ganho sobre o padrão |
|---|---|---|
| H40, recorte 0 (padrão) | 3,29 | |
| H40, recorte −2 | 3,51 | +6,7% |
| H40, recorte −4 | 3,76 | +14,3% |
| H32, recorte 0 | 3,64 | +10,6% |
| H32, recorte −2 | 3,93 | +19,5% |
| H32, recorte −4 | 4,29 | +30,4% |
| H40, IA 50% | 3,62 | +10,0% (ataques recebidos 155 → 36) |
| Tudo no mínimo, IA 50% | 5,37 | +63% |
A resolução mínima isolada ajuda pouco e o modo colunas é sempre mais lento (observação do dono). O ganho das otimizações de código sozinho (padrão, 3,29 contra 2,90 da CONTROL de ontem) é de +13,4% com o jogo idêntico.
