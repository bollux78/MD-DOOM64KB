# HANDOFF R74 v2 — Cláudio + Werk: M50 checker fino + flats homogêneos

**Data:** 27/10/2026  
**Estado:** diretrizes aprovadas pelo usuário; R74 ainda não compilada nem medida.  
**Base de engenharia:** R71A12MUL-HUD (referência histórica de DEMO3: 7,32 FPS), HUD original obrigatório, H40 e margens stone preservadas.  
**Referências visuais prioritárias:** `doom-md-r53-n25f-m50` e `doom-md-r53-n25a-m50`.  
**Experiência recente:** R73-M visualmente preferida à R73-F; R73-F rejeitada por quadriculado grosseiro. A R73-M é uma base de integração, **não** substitui as duas referências R53 M50.

## 1. Decisão principal

O trabalho passa a ter **dois eixos independentes**:

1. **MicroDither:** preservar o **mesmo cálculo de escolha/mistura de cores** dos perfis R53 N25F-M50 e N25A-M50, mas avaliar **checker fino 1×1 em pixels físicos**, em vez das linhas diagonais perceptíveis.
2. **Chão e teto sem textura aparente:** minimizar especificamente o contraste visual entre a coluna lógica par (PAL0) e a ímpar (PAL1) que formam uma cor aparentemente sólida. **Não** aplicar o checker de alternância de colunas da R73-F, que gerou blocos/quadriculado grosseiro.

Primeiro comparar o padrão com as **mesmas cores e LUTs**. Depois comparar as LUTs de flats com o **mesmo padrão de tile**. Não misturar mudanças sem controles.

### Padrões espaciais (diferença importante)

Com mistura 50%:

Checker 1×1 físico (desejado para testar):

```text
ABAB
BABA
ABAB
BABA
```

Linhas/diagonais aparecem quando fases de um padrão de amostragem se propagam espacialmente como faixas oblíquas; padrões de densidade 25% podem parecer diagonais ou pontilhados. O checker de 50% **já é alternância em ambas as direções**: a antiga descrição que mostrava “diagonal” e “checker” como desenhos idênticos era imprecisa. Confirmar o padrão efetivo da ROM histórica no tile físico, não só seu rótulo.

**R73-F rejeitada** = troca grosseira de índices/cor de flats entre linhas lógicas (`DOOM_R72_FLAT_2D`). **Checker aprovado para ensaio** = alternância de **pixels físicos dentro do mesmo tile 8×8**, com o mesmo par de cores escolhido pelo algoritmo; são operações distintas.

## 2. Fatos encontrados no código

Branch de referência: `exp-chatgpt-r73-r53-palette-tests-20261027`.

- `src/r22_video.inc` tem `R_DrawColumnFlat(uint8_t c,...)` para superfícies planas. No R64A usa `r52map=cx->flat[x&1u]`. O caminho Pair-V Fast preenche os índices dos pixels de cada coluna/trecho; não é necessário inserir um cálculo de distância de cor por pixel.
- O preenchimento de **paredes** usa mapas próprios `wall_even` / `wall_odd` e LUTs compostas; preservar suas escolhas durante os testes de flats.
- `R47_LoadPairTiles()` escreve o codebook gráfico na VRAM. Os padrões físicos devem ser alterados **offline/na geração ou inicialização de tiles**, não no loop de pixels.
- Na R73, `scripts/lab/gen_r73_r53_fixed.py` atualmente aponta `r73_flat_even=r52_even` e `r73_flat_odd=r52_odd`. Substituir por mapas exclusivos de flats é a primeira intervenção.
- `scripts/lab/gen_r53_micro.py` gera companions. A implementação R53 inclui opção de mistura **50%**; consultar também como N25F (zero proibido) e N25A (zero permitido) foram realmente construídas e **não assumir equivalência** sem hash/relatório das ROMs de origem.
- `src/r_plane.c` distingue `skyflatnum` de flats normais: céu usa `R_DrawSky`. A renderização atual de piso/teto pode ainda consultar um índice proveniente do caminho de flats, embora pareça uniforme; verificar `c`, iluminação e efeitos de PLAYPAL antes de reduzir esse caminho.
- As paletas de PAL0 e PAL1 são CRAMs fisicamente diferentes. **Somente uma LUT não pode criar novas cores CRAM**; medir o limite real de proximidade possível sem alterar paredes.

## 3. Cláudio — cor, CRAM e tabelas estáticas

**Entregas obrigatórias:** gerador reproduzível, LUTs separadas `flat_even[256]` e `flat_odd[256]`, relatório JSON, teste de paridade, prévias numéricas e métricas de mudança.

### Referências

Gerar primeiro **dois conjuntos independentes** de perfis:
- **N25F-M50**, usando a política exata de zeros da ROM histórica.
- **N25A-M50**, idem.

Conservar a seleção de cores das paredes e seus companions; não regenerar uma paleta de “aparência parecida” usando CM6. Se as fontes históricas não forem encontradas, registrar a ausência e não afirmar identidade cromática.

### Otimização exclusiva dos flats

Para cada cor-fonte `c` desenhada como flat, buscar pares `(i,j)` entre as entradas válidas **PAL0[i]** e **PAL1[j]**, com palavras CRAM quantizadas como Mega Drive. Minimizar:

`J = erro_mistura(c,i,j) + λ·distância_perceptual(PAL0[i],PAL1[j]) + μ·diferença_luminância(i,j)`

- Peso de continuidade entre par/ímpar **muito maior para flats** que para paredes.
- Preferir mesma família de matiz para azul, verde, cinza e tons quentes.
- Não sacrificar completamente a cor-alvo: azul “uniforme” que fica cinza ou verde é **reprovado**.
- Respeitar a política de transparência de cada variante; quando índice 0 é permitido, verificar que não cria buracos ou cor de fundo indevida.
- Medir **ΔE**, **ΔL** e erro da média, além de contabilizar as cores/áreas efetivamente usadas como flats.
- Testar índices por todos os níveis de iluminação aplicáveis e efeitos de paleta relevantes; não medir apenas PLAYPAL 0 se o runtime acessa outros bancos.

Gerar três políticas por referência:
- **F1 Near:** privilegia a menor diferença entre PAL0 e PAL1.
- **F2 Balanced:** combina proximidade e fidelidade cromática.
- **F3 Strict:** impõe limiar máximo de contraste, documentando cores sem par aceitável.

**Opção adicional, isolada:** testar remapeamento de CRAM dedicado a flats apenas se F1–F3 não forem suficientes. Como PAL0/PAL1 são compartilhadas com paredes, a mudança de CRAM pode degradá-las; jamais aplicar silenciosamente ao perfil principal.

## 4. Werk — integração do checker físico e renderer

**Entregas:** scripts/flags, fonte, compilação PERF/PLAY, hashes, manifesto e comparativos visuais/performance.

1. Integrar os dois conjuntos históricos **N25F-M50** e **N25A-M50** na R71A12MUL-HUD, mantendo as cores das paredes sem CM6 de substituição.
2. Para cada conjunto, implementar **checker físico 1×1 de 50%** no codebook de tile Pair-V. Exemplo: dentro dos quatro pixels opacos de uma linha, `ABAB` para linhas pares e `BABA` para ímpares; preservar o funcionamento dos dois bancos de tiles, código 0 transparente e deslocamento de 4 pixels.
3. Manter **o mesmo par de cores e percentual M50**, sem recomputar companions por motivos de mudança espacial. A fase deve ser estável entre tiles e não variar com frames (evitar shimmer).
4. Sem alterações de loop por pixel: preferir `R47_LoadPairTiles` / funções de geração de tiles para manter custo por quadro baixo.
5. Integrar `flat_even/odd` de Cláudio apenas no caminho dos flats, inclusive cache `R64A_Fill().flat[0/1]`. Não tocar `wall_even/odd`, `comp_even/odd`, sprites ou HUD.
6. **Não** habilitar `DOOM_R72_FLAT_2D` ou equivalente da R73-F: trocar colunas lógicas por linha cria quadriculado de blocos, distinto do checker 1×1.
7. Preservar R71 MUL ASM, limites de memória, H40 stone margins e HUD-WAD; medir FPS no mesmo benchmark NTSC 60 Hz com clock original. ROM IDs curtos, como nas correções R73.

### Céu — experimento **separado**

Pesquisar `R_DrawSky`, seu relacionamento com `skyflatnum`, quantização angular e scroll. A solicitação é céu sem efeito de perspectiva de chão/teto, com scroll horizontal em passos de **8 pixels físicos (1 tile)** se viável. Verificar se o desenho atual já satisfaz isso; não substituir céu por uma cor plana nem introduzir saltos visuais sem avaliação. Fazer ROM dedicada para sky-scroll, não misturar ao teste de flats.

## 5. Matriz de comparação recomendada

| Grupo | Paleta | Dither no tile | Flats | Finalidade |
|---|---|---|---|---|
| Controle A | N25F | M50 histórico | original | fidelidade à referência |
| Controle B | N25A | M50 histórico | original | fidelidade à referência |
| Checker A | N25F | checker físico 1×1 M50 | original | isolar padrão |
| Checker B | N25A | checker físico 1×1 M50 | original | isolar padrão |
| Flat F1/F2/F3 | perfil vencedor | checker físico M50 | Near/Balanced/Strict | reduzir listras sem mudar paredes |
| Sky opcional | perfil vencedor | checker físico M50 | melhor flat | quantização de scroll |

Fazer PERF e PLAY para os experimentos relevantes. Se o orçamento de builds ficar alto, começar por **dois controles + dois checkers + F2 Balanced**, sempre mantendo controle visual e benchmark correspondente.

## 6. Critérios de aceitação e rejeição

**Aprovar apenas se:**
- Chão e teto parecerem perceptualmente mais homogêneos, com diferença menor entre colunas pares/ímpares e **sem aspecto cinza/lavado**.
- Checker físico fino parecer superior às linhas diagonais na mesma cena e com **as mesmas cores**.
- Paredes, sprites, detalhes, HUD e iluminação permanecerem intactos.
- Ganho visual não vier acompanhado de novo checker grosseiro, costuras ou cintilação.
- Medições registrarem FPS DEMO3, total de frames (até 10.000), memória/BSS, flags e hashes.

**Rejeitar:** R73-F ou seu método de alternância de flats; misturas CM6 apresentadas como R53; descaracterização de paredes; alegações de desempenho sem medição.

## 7. Fluxo de entrega e responsabilidades

**Cláudio:** localizar/validar perfis históricos, produzir LUTs específicas de flats para N25F e N25A, relatório de pares/erros e F1/F2/F3.

**Werk:** integrar checker físico 1×1 M50 e LUTs com baixo custo, produzir ROMs de teste isoladas, conferir compatibilidade com R71-HUD, investigar scroll do céu em ensaio separado.

**Usuário:** comparar em Mega Drive real, nas mesmas cenas. As fotos de FPS instantâneo não substituem o benchmark estável (R71A12MUL-HUD: 7,32 FPS).

## 8. Referências

- Repositório: https://github.com/bollux78/MD-DOOM64KB
- Branch de trabalho R73: https://github.com/bollux78/MD-DOOM64KB/tree/exp-chatgpt-r73-r53-palette-tests-20261027
- Workflow anterior: https://github.com/bollux78/MD-DOOM64KB/actions/workflows/r73-r53-tests.yml
- Antecedente: handoff R74 v1, substituído por este documento; quando houver código R74, criar nova branch experimental independente e manter a R71 estável intocada.
