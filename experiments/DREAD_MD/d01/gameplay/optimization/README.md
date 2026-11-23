# DREAD C7 - rodada de otimização

Base congelada: `c816e6c72a8fc6a3bc989b347ea7166fda835893` (última C7 NORMAL validada no boot). A C7 estável não é alterada. Handoff de referência: DREAD-OTIMIZACAO-HANDOFF.zip (22/11/2026).

Esta rodada foi revisada em 23/11/2026 depois de ler o código de cada variante e de testar a geometria no renderizador de host (WAD Freedoom, mapas E1M1, E1M2, E1M5, 3000 vistas cada). Os números do host são de **trabalho do renderizador** (segs, nós da BSP, colunas) e de **pixels**. Eles não são FPS do Mega Drive.

## 1. Resultado da revisão (o que estava errado, o que não rende)

| Variante original | Veredito | Evidência |
|---|---|---|
| GEO_SAFE | **tinha bug, corrigido**; ganho pequeno | Ver 1.1. |
| GEO_STEPS | **removida da rodada** | Reduz só 0,6–1,7% dos segs e muda os pixels em 3–12% das vistas (até 79% dos bytes de uma vista), além de alterar colisão. |
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

Invariantes conferidos: o `mapdata.c` do CONTROL tem o mesmo SHA-256 de antes das mudanças no conversor (o CONTROL não muda), e a `pvs.c` do GEO_SAFE é idêntica à do CONTROL nos três mapas.

Conclusões:
- GEO_SAFE passa a ser **near_exact**: a imagem muda só em pixels isolados de borda (uma coluna na junção de um portal removido). Bit a bit idêntico não é prometido.
- **Ganho esperado: no máximo ~1,5% do trabalho de colunas, e 0% na BSP.** Provavelmente fica abaixo do ruído do benchmark. Ele fica na rodada porque agora é seguro e é a única redução de geometria que não altera o jogo.
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
| GEO_SAFE | near_exact | Remove segs invisíveis; PVS da geometria completa; folha nunca vazia | nada visível; pixels de borda podem mudar |
| AI6 | gameplay_change | IA a 6 Hz sem correção | monstros mais lentos; metade da velocidade para imp, baron e caco |
| AI6S | gameplay_change_speed_kept | IA a 6 Hz, passo proporcional | mesma velocidade média, movimento mais "em saltos" |
| ALL | multi_change | AI6S + GEO_SAFE | soma das duas |

Só a classe `near_exact` (e `baseline`) pode ser chamada de otimização sem decisão do dono do projeto. As classes de IA são trade-offs de jogo.

## 3. Como ler os números

- **Render (modo 1):** IA desligada. Mesma carga entre variantes que não mudam o renderizador. É a medição mais limpa.
- **Combate (modo 2):** IA ligada. **Não é a mesma carga entre variantes de IA:** os monstros agem diferente, então a rota diverge. `pack_matrix.py` marca `combat_comparable = False` para as classes de IA. Para elas, olhar o custo da IA, não o FPS total (ver regra 1 abaixo).
- **Histograma de VBlanks por quadro** (`vblank_histogram`, `vblanks_per_frame_mean`): o FPS médio (`frames*60/vblanks`) esconde a distribuição. Nas medições do D01, o mesmo trecho variava de 4 a 15 VBlanks por quadro.
- **Hash visual** (`visual_hash`): hash do quadro final de cada modo (amostragem em passo 2). Serve para detectar mudança de imagem. Para GEO_SAFE o gate de verdade é o do host (`geo_gate_pass`).
- **Emuladores:** MAME tem outra temporização de VDP. Antes de promover qualquer variante, repetir em GPGX ou BlastEm e no console.

### Regras de decisão depois da rodada

1. **A IA importa?** Calcule `render_fps / combat_fps − 1` no CONTROL. Se for menor que 5%, nenhuma variante de IA pode render mais que isso: descarte AI6, AI6S e ALL.
2. **Ruído:** rode cada modo duas vezes (o workflow já roda uma vez por modo; rode a matriz duas vezes se o resultado ficar perto do ruído). Diferença menor que a variação entre repetições não é resultado.
3. **GEO_SAFE:** espere ≤1,5%. Só vale mantê-la se o ganho passar do ruído **e** `geo_gate_pass = True`.
4. **Promoção:** classes de IA só por escolha do dono do projeto, depois de jogar. Nada vai ao console antes do teste manual em BlastEm e no console.

## 4. Verificação no host (sem ROM)

`verify_geo_exact.sh WAD "E1M1 E1M2" [VISTAS] [SAIDA] ["control merge"]` converte cada variante, gera a PVS da geometria completa, compila o renderizador de host, renderiza as mesmas vistas (posições dentro do mapa escolhidas pelo CONTROL) e compara os framebuffers. O gate de `near_exact` é: nenhum quadro em branco, no máximo 2% das vistas diferentes, nenhuma vista com mais de 5% dos bytes diferentes. Escreve `summary.json`. O CI roda no job de compilação do GEO_SAFE (WAD do Doom 1 no runner) e grava `geo-verify-GEO_SAFE.{txt,json}` no ZIP.

`host/host.c cmp N [POSFILE [DUMPFILE]]` é o modo usado: imprime hash e contadores de trabalho (`segs`, `nodes`, `subs`, `colvisits`) por vista. Esses contadores mostram, antes de gastar uma build, se uma mudança pode ser mais rápida.

## 5. Propostas próprias (fase seguinte, **não** entram nesta rodada)

Nenhuma foi medida em 68000. Cada uma diz como provar antes de gastar uma build.

1. **Segundo estágio do laço de colunas (maior alvo conhecido).** As bordas da parede em registradores com `add/addx`, registro sequencial por coluna lido com `(a4)+`, partes como casos separados. O D01 mostrou ~60 instruções por coluna, quase todas com leitura/gravação em memória. Teste: pixels idênticos no host e benchmark no D01 (spin de 1500 quadros no início de E1M1, hoje 6,39 FPS).
2. **BSP e projeção ≈ 27% do tempo no D01.** No host (Freedoom E1M1) são ~86 nós e ~50 folhas visitados por vista para ~45 segs desenhados. Ideia: lista de segs pré-ordenada por folha/direção para pular nós sem desenho. Teste: contadores `nodes`/`subs` do `cmp` antes e depois, pixels idênticos.
3. **Ajuste da PVS com oráculo.** A PVS é **amostrada** (`pvsgen.c`: 16 direções por folha + dilatação pelos vizinhos), não um flood conservador. No host a PVS atual já erra em ~6% (E1M1), ~2,6% (E1M2) e 0% (E1M5) das vistas aleatórias, em poucos bytes (`host x sweep 3000` compara PVS ligada e desligada). A dilatação dobra o conjunto visível (117 contra ~63 folhas no E1M1 do D01). Um ajuste da dilatação por distância é só de tempo de build, sem risco no ROM; o preço é medir buracos contra nós visitados.
4. **Custo da IA antes de mexer nela.** Regra 1 da seção 3. Se a IA for maior que ~5%, o alvo é o custo por ação (`look()`/`can_see()`, `try_move`, laço sobre todos os atores), não a frequência.
5. **Pico de quadro.** O histograma mostra se AI6/AI6S trocam FPS médio por quadros longos (a IA só roda a cada 10 VBlanks, mas o trabalho junto cai num quadro).

## 6. Arquivos

- `variant.sh`, `compile_one.sh`: compilação independente por variante (o GEO_SAFE roda a verificação do host no fim).
- `bench_mame.py`, `bench_mame.lua`: benchmark MAME (histograma, hash visual, `ai_active`).
- `verify_geo_exact.sh`, `host_stubs.c`, `../../host/host.c` (modo `cmp`): verificação no host.
- `pack_matrix.py`: ZIP com as ROMs e CSV/JSON com classe, FPS, deltas, `render_pixels_equal_control`, `combat_comparable`, `geo_gate_pass`.
- `geometry/`: números de SEGS por mapa. Não é medida de FPS.

## 7. Workflow e segurança

`.github/workflows/dread-c7-optimization-matrix.yml`: o runner self-hosted compila; os runners hospedados fazem o benchmark e montam o ZIP.

O job de compilação roda em runner self-hosted em repositório público. Restrinja quem pode fazer push no branch, ou use um runner dedicado ao seu repositório, antes de aceitar código de terceiros. O workflow `dread-c7-optimization-bench-smoke.yml` baixa o artefato de uma run fixa; troque o `run-id` antes de reutilizá-lo.

## 8. Limites desta revisão

- Os testes do host usaram o **Freedoom** (o WAD do Doom 1 não está neste ambiente). Os números de redução de segs do Doom 1 podem diferir; o CI repete a verificação com o WAD do Doom 1.
- O host usa os caminhos em C do renderizador e não roda o assembly do 68000. A equivalência de pixels vale para os dados e para a lógica em C; ela não prova a ausência de efeitos no assembly nem no hardware.
- `AI6S` foi compilado no host só para sintaxe (`actors.c`); o comportamento dos monstros não foi jogado.
- Nada foi medido em FPS do Mega Drive.
