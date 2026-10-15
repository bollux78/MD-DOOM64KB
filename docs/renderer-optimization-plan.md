# DOOM MD — plano de otimização do renderizador (rodada 1)

## Referência e restrições

- Hardware-alvo: Mega Drive original, Motorola 68000 ~7,67 MHz (BlastEm clock divider **7**).
- ROM de referência: modo **NO VSync**, resolução lógica **38 × 28**, sem mudar cores, texturas nem algoritmos visuais.
- DEMO3: **2.134 quadros**, **245,12 s**, **8,71 FPS médios** (mínimo **3,9**, máximo **14,1**), obtidos manualmente no TIMEDEMO 4.
- A referência é uma medição do usuário no emulador, **não** resultado de CI.
- O profiler de VBlank a divisor 7 e NO VSync atribuiu ~**43,1%** das amostras a WALL COLUMNS, **29,2%** a BSP TRAVERSE (inclui processamento de linhas, não apenas caminhada na árvore), **13,0%** a OTHER/LOGIC e **9,8%** a VDP. Não são medições precisas de ciclos.

## Experimentos preparados

| Variante | Macro | Alteração | Risco |
|---|---|---|---|
| baseline | nenhuma | Sem mudanças no motor, NO VSync | Controle |
| fast-divu | DOOM_FAST_DIVU | Divide 0x01ffffff por escala usando DIVU.W quando 512 <= escala <= 65535; expressão matemática idêntica à divisão anterior, fallback original | Baixo, requer validação no hardware/emulador |
| unroll-columns | DOOM_UNROLL_COLUMNS | Desenrola em 2 as colunas texturizadas e em 4 as colunas sólidas | Baixo, possível regressão por tamanho de código/cache |
| combined | ambas | Investiga interação entre as duas | Validar só se alternativas individuais forem promissoras |

O caminho DIVU.W usa a identidade exata `(0xffffffff / scale) >> 7 == 0x01ffffff / scale` para inteiros positivos. O montador precisa aceitar o inline assembly; o código novo ainda **não foi compilado/validado** na toolchain do CachyOS.

## Amanhã cedo: uma compilação, quatro ROMs

1. Deixe o runner `x360-linux` ligado (`./run.sh`), se usar o CachyOS.
2. No GitHub, **Actions → Renderer optimization suite → Run workflow**. O workflow existe em `main`, mas faz checkout fixo da branch `exp/68k-renderer-first-pass`.
3. Aguarde os quatro jobs (um por vez). Se algum falhar, compartilhe o link para análise dos logs antes de testar.
4. Baixe os artefatos: `doom-md-baseline`, `doom-md-fast-divu`, `doom-md-unroll-columns`, `doom-md-combined`.
5. Comece pelos testes visuais **baseline** e **fast-divu** no BlastEm com divisor **7** e velocidade normal. A DEMO3 termina numa tela com FPS médio, mínimo, máximo e tempo total.
6. Só compare FPS de ROMs compiladas na mesma rodada e com o mesmo modo. Preferencialmente anote também `rom.sha256`, tela de resultados e quaisquer artefatos de imagem.
7. Se a DIVU.W ganhar desempenho com visual correto, teste `unroll-columns` e depois `combined`. Se não ganhar, evite complicar o código com ela.

**Critérios de aprovação:** DEMO3 conclui, nenhum artefato novo visível, contagem esperada de quadros e ganho médio reproduzível. Uma pequena diferença de FPS pode ser ruído do emulador; repetir os melhores candidatos.

## Rodadas seguintes — somente após as medições

1. **Custo de reciprócos e divisões** — instrumentar contagem de casos `rw_scale` e das chamadas de `FixedReciprocal` para localizar outros DIVU.W possíveis.
2. **Cache de colunas de textura** — instrumentar acertos/falhas de `R_ComposeColumn`, tamanho de cache e custo de cópia; ajustar só com dados.
3. **BSP e clipping** — separar `R_CheckBBox`, `R_AddLine`, `R_StoreWallRange` da caminhada pela árvore; o contador atual `BSP TRAVERSE` abrange mais que uma rotina.
4. **VDP e imagem** — só depois do motor, experimentar tiles com dithering Bayer e comparar qualidade/desempenho.
5. **Mega Drive com 13 MHz** — deixar overclock para validação final, como combinado.

## Segurança do ambiente

As ROMs experimentais são compiladas na branch separada, usando o SGDK já presente em `~/mars/m68k-elf`; a rotina de build não modifica a toolchain compartilhada. O workflow é acionado **manualmente** e não executa código de pull requests públicos automaticamente.

Não fazer merge de `exp/68k-renderer-first-pass` antes da compilação, teste visual e comparação numérica.
