# DREAD-MD — estudo do source drop e proposta de portabilidade (Werk)
26/11/2026. Para Cláudio. Escopo revisto pelo usuário: construir nossa evolução da Dread para Mega Drive; Alpha2 é referência, não dependência. Não modificar R13/C7 estáveis nem a branch de Cláudio.

## 0. Resultado novo e decisão imediata

**O modelo matemático dos escaladores do source drop reproduz 147.456/147.456 valores da Alpha2, exatamente.** Fiz o teste preliminar local a partir dos bytes do dump de disassembly privado do usuário, reconstruídos em memória. SHA256 do original confirmado: 47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267. Nenhum byte de ROM ou dump foi publicado.

Configuração: 2048 buckets, altura 72, centro 36, STRETCH_SCALING=1. A distribuição do tamanho por grupo reproduz 159 grupos; 158 mapeamentos distintos (uma duplicação). O modelo independente foi implementado em `dread_source_math.py` e ligado ao exportador de cenas via `--source-scale`, opt-in, sem FSC e sem ROM original. Não copiamos código executável do source drop; implementamos a identidade matemática e o agrupamento numérico, com atribuição.

**Consequência:** eliminar o requisito de `scaler.fsc` extraído da Ferret em novos builds que usem esse modelo. Manter a calibração existente exclusivamente como oráculo de regressão privado até completar os testes.

## 1. Fonte inspecionada e licença

Upstream: [Krzysiek-K/Dread-source-drop, commit d094f08a](https://github.com/Krzysiek-K/Dread-source-drop/tree/d094f08a2faa1ed0d928d6e22404019e447e53a7). Árvore completa consultada, sem truncamento. O código e os geradores estão realmente presentes; não precisamos inferir toda a arquitetura por RE.

- [Licença do SDK](https://github.com/Krzysiek-K/Dread-source-drop/blob/d094f08a2faa1ed0d928d6e22404019e447e53a7/Dread-public/SDK-data/_LICENSE_.txt): autoriza DreadTool/assets em usos especificados no contexto Dread, restringe uso fora desse contexto. Não encontrei licença geral de código na raiz ou no inventário de arquivos. A disponibilidade gratuita do source drop não estabelece automaticamente direito de redistribuir código modificado.
- Cláudio publicou a análise convergente [ANALISE-DREAD-SOURCE-DROP.md](https://github.com/bollux78/MD-DOOM64KB/blob/4729ab38023209385955e814776f9369d11812a8/research/ferret-native/ANALISE-DREAD-SOURCE-DROP.md).
- Caminho A, se o autor autorizar: portar módulos e geradores originais, mantendo atribuição e termos combinados. Caminho B, enquanto isso: estudar algoritmos e formatos e implementar nossas rotinas sem incorporar código ou assets upstream ao repositório. O experimento desta rodada usa B. Não pressupõe autorização concedida.

## 2. Inventário e fronteiras de portabilidade

| Fonte Dread | Responsabilidade observada | Equivalente/ação nossa |
|---|---|---|
| dreadmake/src/dread_asm_lines.s | Transformação lazy de vértices, clipping, projeção, perspectiva adaptativa, chamada de kernel | substituir preparação C por fluxo 68000 próprio e kernels gerados de Cláudio; não duplicar essa frente |
| dreadmake/src/dread_asm_draw.s | Interpretador de visibilidade, listas de paredes e de atores, condições, grupos | novo backend de listas ordenadas por região, ao lado de FRV2 |
| dreadmake/src/dread_codegen.c | Escalas, LineSizeCheat, preenchimento e céu | matemática agora validada; geração offline em ROM; manter gerador próprio |
| dreadmake/gen/line_cheats.s e line_cheat_x*.s | versão 1, dispatch por tipo de parede, com/sem perspectiva | referência de algoritmos e especialização, não copiar assembly |
| dreadmake/gen/render2_linedefs.s; dreadcheat | versão alternativa de renderer, geração de laços e tracers | Cláudio investiga gerador por variante, trabalho independente |
| dreadmake/src/dread_asm_sprites.s | sprite spans, escala e clipping | integrar depois de estabilidade das paredes; comparar com replay de sprites existente |
| dreadmake/src/dread_asm.s, dread_estructs.h | ABI interna, arrays de colunas, offsets de estruturas, BSP | ABI própria, offsets gerados/verificados; não confundir layout C do host com m68k |
| dreadmake/src/dread_mapload.c / dread_data.h | carregador de blocos, relocação e inicialização | dados estáticos ROM, sidecars mutáveis WRAM, exportar ponteiros/índices offline |
| dreadmake/src/dread_physics.c / dread_game.c / dread_asm_scripts.s | física, jogo, execução de atores, máquinas | adaptar ou integrar seletivamente com autorização; avaliar compatibilidade C7 |
| dreadmake/src/dread_soft.c | setup de layout, câmera, render/visibilidade/sprites | camada coordenadora MD, funções de vídeo próprias |
| dreadmake/src/st_main.c, st_c2p.s e Amiga equivalents | vídeo/input/áudio e conversão específica da plataforma | substituir por backend VDP/DMA/controles/áudio C7; não portar C2P |
| dreadtool/src/dread_mapgen.cpp | geometria, regiões de visibilidade, draw order, grupos e exportação | frente Werk: estudar e desenvolver compilador offline independente |
| dreadtool/src/wad_converter.cpp | leitura/conversão de WAD | comparar com exportador atual; manter assets privados |
| dreadmake/doc/mapformat.txt, doc.txt | contratos de mapas/visibilidade/atores | referência de formatos e testes, não tratar documentação antiga como ABI exata |

Fontes fixadas para consulta:
- [dreadmake/src](https://github.com/Krzysiek-K/Dread-source-drop/tree/d094f08a2faa1ed0d928d6e22404019e447e53a7/dreadmake/src)
- [dreadmake/gen](https://github.com/Krzysiek-K/Dread-source-drop/tree/d094f08a2faa1ed0d928d6e22404019e447e53a7/dreadmake/gen)
- [dreadtool/src/dread_mapgen.cpp](https://github.com/Krzysiek-K/Dread-source-drop/blob/d094f08a2faa1ed0d928d6e22404019e447e53a7/dreadtool/src/dread_mapgen.cpp)
- [Makefile.ST](https://github.com/Krzysiek-K/Dread-source-drop/blob/d094f08a2faa1ed0d928d6e22404019e447e53a7/dreadmake/Makefile.ST): vbcc/vasm/vlink, Atari TOS, versão de paredes 1, 160x84 lógico (centro 42), STRETCH_SCALING=1. O Makefile Amiga usa altura 100/centro 50 e grupos de visibilidade. Não equivale às configurações 72/36 da Alpha2.
- [gen_asmstruct_st.i](https://github.com/Krzysiek-K/Dread-source-drop/blob/d094f08a2faa1ed0d928d6e22404019e447e53a7/dreadmake/gen/gen_asmstruct_st.i): tamanhos m68k concretos de vértice 8, parede 32, subsetor 14, ator 104, cheat 62 bytes.

## 3. Escalas: explicação quantitativa e teste

O source drop usa grupos de escala progressivamente mais largos, com acumulador de frações de 8 bits; aproximadamente 1/30 do índice corrente, pelo menos 1 bucket. O representante é o inteiro central do grupo. A expressão de coordenada vertical, após simplificar os dois casos (acima/abaixo do centro) e o deslocamento aritmético, fica:

    tex_y = floor((256*(y-36)+255)/(2*s))

onde s é o representante. A divisão precisa arredondar para menos infinito também nos negativos. Bucket zero segue o primeiro grupo na nossa adaptação (comprovado na Alpha2; gerador original começa em 1).

| Configuração experimental | Linhas inteiras idênticas | Valores idênticos /147456 |
|---|---:|---:|
| centro 35, stretch 0 | 0 | 16542 |
| centro 35, stretch 1 | 0 | 112617 |
| centro 36, stretch 0 | 0 | 16396 |
| centro 36, stretch 1 | **2048** | **147456** |
| centro 37, stretch 0 | 0 | 16414 |
| centro 37, stretch 1 | 0 | 112548 |

Dados acima vêm de teste local exaustivo contra o dump autenticado, não de amostragem. 159 grupos e 158 linhas distintas. A altura 72 é escolha de port demonstrada pelo oráculo, não valor literal da versão ST upstream.

Tabela compacta atual: 158*72*2 + 2048 = 24.800 bytes em ROM. A tabela e os índices podem ser gerados sem qualquer entrada privada. Os extremos das escalas pequenas exigem manter o tratamento de wrap/clip do nosso renderer. Uma tabela idêntica não demonstra ainda que o pipeline inteiro da Dread é idêntico à Ferret.

Próximo teste automatizado no x360: geração source-only, fixture assimétrico sem FSC, comparação exata com FSC privado e com as duas tabelas da cena R04, duas builds R13 com a mesma label e `cmp` de ROM, VRAM GPGX sem SRAM em fixture e cena E1M1. A geração da tabela não usa o oráculo; a comparação privada é somente teste. Relatórios numéricos somente. Status na publicação inicial deste documento: workflow preparado, ainda não concluído.

## 4. Memória: o ponto que impede um port ingênuo

Fonte: `dread_codegen.c`, `dread_estructs.c/.h`, `dread.h`, `gen_asmstruct_st.i`. Dimensões são do source drop, não um perfil da Alpha2 nem previsão de consumo de E1M1.

| Estrutura | Bytes (alocação/limite upstream) |
|---|---:|
| SCALER_BUFFER | 86202 |
| LINE_CHEAT_BUFFER | 9920 |
| FN_SCALERS, SIZE_LINE_CHEAT (estimativa 2048 índices e ponteiros de 4 bytes) | 16384 |
| e_things_buffer (512*104) | 53248 |
| e_vislines (541*6) | 3246 |
| Vértices (limite 1024*8) | 8192 |
| Paredes (limite 1536*32) | 49152 |
| Subsetores (limite 512*14) | 7168 |

Os três últimos são limites estruturais, não necessariamente arrays integralmente alocados em runtime. Só scaler buffer e pool fixo de atores já excedem 64 KiB cada em combinação. O original faz uso de carregamento e regiões de memória adaptadas ao Amiga/ST.

Proposta:
1. ROM: geometria estática, BSP, listas de visibilidade, texturas, tabelas de escala, geradores executáveis, descritores de atores e dados de script.
2. WRAM: câmera, cache de transformação, estado de recorte/profundidade, portas/máquinas, atores ativos, listas curtas de visibilidade, framebuffer e buffers de apresentação. Mapas podem ter linhas/vértices dinâmicos: manter apenas os registros alteráveis em sidecars/overlay. Medir alocação real e picos, não presumir que todos os registros possam ser constantes.
3. Framebuffer lógico atual 160*72=11520 bytes; tiles duplicados 23040 bytes. Apresentação assíncrona precisa análise de vida útil desses buffers, de DMA e de VRAM. Não aumentar staging até demonstrar orçamento com gameplay.
4. Manter 64 KiB obrigatórios, assert no linker, margem de stack e handlers. SRAM16 opcional não pode decidir correção da imagem nem lógica; verificar o caminho utilizado.
5. Avaliar tamanhos reais dos mapas e limites de atores simultâneos. Não reduzir arbitrariamente o número de inimigos só para caber.

## 5. Duas armadilhas específicas de 68000 no cartucho

- Código automodificável: versão 1 grava temporariamente retorno em escalador para interromper o span e restaura a instrução depois. Código na ROM não pode ser alterado como na RAM. Alternativa própria: entrada calculada no trecho desenrolado com DBRA/contador, ou especializações pré-geradas com parada segura. A R10/R11 já implementa abordagem ROM-residente. Não transportar a técnica de escrever na ROM.
- A7 como destino: as rotinas Dread usam pós-incremento de byte em A7 (avança 2, diferente dos demais An). Em supervisor mode, uma interrupção ou exceção enquanto A7 aponta para pixels usaria essa área como stack; um port com VBlank assíncrono deve manter SSP válido. Opção preferencial: registrador An diferente, layout contíguo/stride explícito e apresentação adaptada. Alternativas com user mode/USP ou interrupções mascaradas exigem provas e benchmark; não assumir segurança. Se escolher coluna contígua, preservar bytes lógicos e modificar conversão tiles, sprite e clipping juntos.
- O toolchain usa ABI VBCC com parâmetros em registradores e offsets gerados. Com GCC/marsdev, wrappers explícitos e verificação de clobbers/stack/offsetof. Não usar structs de host como layout binário automaticamente.
- Não confundir versão 1 e versão 2 de kernels: os arquivos e flags upstream indicam caminhos diferentes. Comparar cada um com a versão R13 real, não juntar vantagens teóricas em uma implementação fictícia.

## 6. Frente independente do Werk: visibilidade e compilador

Esta é a parte que pode dar salto estrutural e não duplica o gerador do Cláudio.

`dread_mapgen.cpp`, funções lidas:
- `ComputeVisibility/ComputeAllVisibility` (1356–1478): inicializa regiões/BSP, abre portas para calcular o envelope de visibilidade, processa linhas e inclui visibilidade das máquinas.
- `ComputeVisibility_Rec` (1794–1925): propaga feixes geométricos por portais, recorta polígonos e registra linhas/setores nas regiões alcançadas; carrega condições ao atravessar portais. Limite de recursão 32 no upstream, não adotar sem testar falsos negativos.
- `Vis_PrepareRegion` (2006–2095): calcula restrições de ordenação por pares de linhas, recortando polígono da região; gera dependências que evitam desenhar fundo antes da frente.
- `Vis_ComputeDrawOrder` (2096–2252): agenda entradas desbloqueadas, tenta conservar condição corrente, trata ciclos de ordenação. Não presumir que uma única ordem seja válida em toda região sem prova.
- `Vis_BuildGroup/BuildVisDrawLists` e `ExportRegionProcess/ExportVisGroup`: compartilha sequências entre regiões e exporta grupos/modos/condições. Interpretador de grupos da engine tem comandos compactos, diferentes do formato antigo documentado; a fonte atual é autoridade.

Hipótese de trabalho: a vantagem da Dread/Ferret não é apenas PVS (visibilidade booleana); é a combinação de subdivisão de regiões + ordem front-to-back pré-calculada + modos/condições de parede. O nosso FRV2 ainda usa DAG/travessia BSP; o PVS angular de 349540 bytes economizou só 2–4% após pré-teste R09. Compilar listas completas por região pode também reduzir travessia, pré-testes e dispatches, mas é hipótese a testar.

Proponho experimentos em branches independentes:
- V0: manter referência FRV2; criar fixture sintético com corredor em L, sala visível por dois portais, porta fechada/aberta e interseção de ordens. Verificar visibilidade e ordem com ray oracle independente.
- V1: construir propagação conservadora de visibilidade por portal sobre polígonos convexos/subsetores, com condição dinâmica; não excluir linhas duvidosas. Contar regiões, entradas, bytes e tempo de compilação.
- V2: gerar ordem válida por região (restrições geométricas, topological order); dividir regiões onde a ordem é ambígua; fallback FRV2 para casos não provados. Compartilhar prefixos/sufixos e medir ganho em ROM.
- V3: conectar ao renderer atual e ao gerado de Cláudio por um contrato estável de entradas (id, variante/modo, condições), sem mexer no kernel. Comparar estado completo com baseline e oráculo em milhares de câmeras, incluindo portas em vários estados; 12 poses R04 e 5 câmeras Alpha2 para timing. Se a ordem mudar sem alterar imagem, medir pixels/depth/sprites/clip; não exigir contador candidato idêntico.

O port direto do DreadTool, caso autorizado, seria avaliado separadamente. O módulo C++ depende de tipos geométricos, gerenciamento de regiões e temporização Windows (QueryPerformanceCounter). Extrair núcleo headless/usar exportador existente é mais realista que portar toda a aplicação gráfica.

## 7. Divisão de trabalho solicitada

**Cláudio:** continuar gerador especializado por variante, tracers DDA, registradores e integração do backend de apresentação. O resultado exato de escalas dispensa reconstrução por calibração. Usar `--source-scale` após a validação. Garantir tratamento de span curto, wrap, céu e interrupções, paridade legado com FR_SKY_LEGACY/FR_PAIR_PHASE e imagens padrão.

**Werk:** manter testes e benchmark, substituir a fonte das tabelas por matemática verificável nesta branch, depois atacar o compilador de visibilidade/ordenação independente e orçamento de memória. Não duplicar o gerador de paredes. R13 assíncrona continua tarefa de medição já solicitada no PR45, em branch distinta; não misturar o resultado com o experimento de escalas.

**Usuário:** decidir eventual autorização do KK/Altair para adaptação direta do código; teste físico e decisões visuais. Não precisamos esperar autorização para medir matemática e técnicas implementadas independentemente. Assets originais e ROMs continuam privados.

## 8. Critérios de aceite e sequência

1. Source math: 147456/147456 valores e as duas tabelas compactadas iguais, ROM byte-idêntica quando demais entradas iguais, GPGX VRAM zero mismatches, ISA 68000. Fixture sem FSC para provar independência do gerador.
2. Kernels gerados: benchmark mesmo mapa/câmera/flags e estabilidade; separar preparação, projeção, rasterização e apresentação. Não trocar qualidade ou resolução sem decisão do usuário.
3. Visibilidade: provas conservadoras e oracle de pixels/clip, não só redução de candidatas. Medir frame time e ROM/WRAM. Comparar com Alpha2 WRAM em GPGX (4,83 FPS / cinco câmeras do teste anterior) com ressalva de gameplay e conteúdo diferentes.
4. Gameplay: integração de sprites, máquinas, colisões, física e scripts; repetir testes depois de cada integração. C7 segue fonte de soluções de plataforma.
5. Hardware: comparar padrão/async, sem SRAM e SRAM16, verificar tearing, faixa preta e controles. Emuladores não substituem console.

**Não considero concluído um port da engine.** O que ficou comprovado nesta primeira rodada é a origem matemática dos escaladores e o caminho arquitetural. As demais propostas são experimentos planejados. O novo objetivo é usar o conhecimento do source drop para chegar a uma engine própria e evitar engenharia reversa redundante.
