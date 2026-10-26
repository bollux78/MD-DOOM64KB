# R70-A — R_RenderSegLoop (sem perda visual)

Branch `exp-claudio-r70a-segloop-20261026`, base R66 `f5a9daa` (imutável). Estado: **código + testes host + proposta de workflow A/B prontos; nada ativado, nenhuma ROM compilada**.

## O que muda (duas etapas, cada uma com sua flag)
- **A1** `DOOM_R70A_LOCALS=1` → liga o `DOOM_R21_SEGLOOP_LOCALS` que já existia no código (R21 N3) e nunca foi medido no R66. Estado do laço
  (`rw_scale`, `topfrac`, `bottomfrac`, `pixhigh`, `pixlow`, seus passos e `rw_stopx`) vive em locais e é gravado de volta após o laço.
  Nenhuma linha de código nova: só a flag no build.
- **A2** `DOOM_R70A_INVARIANTS=1` (+54 linhas em `src/r_draw.c`) → copia para constantes locais o que é invariante no laço:
  `rw_offset`, `rw_distance`, `rw_centerangle`, `rw_*texturemid`, `midtexture/toptexture/bottomtexture/maskedtexture`,
  `maskedtexturecol`, `floorplane_color`, `ceilingplane_color`.

## Por que é exato
- Auditoria por grep: todas as escritas dessas globais estão em `R_StoreWallRange` (antes do laço), `R_Subsector` ou `R_DrawMasked`; nenhum callee
  do laço (`R_DrawColumnFlat`, `R_DrawSky`, `R_DrawSegTextureColumn`, `R_DrawColumnWall`) as altera. `rw_scale` e os `*frac` só são lidos fora do laço
  em `R_StoreWallRange`, e A1 os grava de volta ao sair.
- Nenhuma alteração de aritmética, arredondamento, saturação, clipping, flats, sprites ou política de colunas pares/ímpares (R66 COLPAIR intacto).

## Prova no host (sem ROM)
- `scripts/lab/test_r70a_segloop.py`: compila o **texto real** de `R_RenderSegLoop` quatro vezes (controle, A1, A2, A1+A2) com o conjunto de macros do
  build perf (COLPAIR, TAN_MULS/TAN32, FAST_DIVU, RECIP_LUT, FLAT_SPAN) e roda 20.000 segmentos aleatórios (11,5 M de eventos: flats, céu, parede
  simples/dupla/máscara, colunas pares/ímpares, clips). Compara byte a byte cada chamada de desenho (argumentos e `dcvars` completos), `floorclip`,
  `ceilingclip`, `solidcol`, `maskedtexturecol`, `didsolidcol` e as globais gravadas de volta. Resultado: **A1, A2 e A1+A2 idênticos ao controle**.
- Sensibilidade: 4 mutantes deliberados (offset+1, texturemid trocado, cor do teto trocada, passo do pixlow+1) são todos detectados.
- `scripts/lab/check_r70_inert.py BASE .`: sem `DOOM_R70A_INVARIANTS` o `r_draw.c` é idêntico ao R66 (IDENTICAL).
- `test_r57_viewport.py` e `test_r22_pixel4.py` continuam PASS.

## Limites honestos
- Não há toolchain m68k aqui: o ganho **não foi medido** e o código gerado não foi inspecionado. A estimativa teórica é pequena
  (acesso por deslocamento de 16 bits no lugar de endereço absoluto longo economiza ~4 ciclos por acesso; ~14 acessos por coluna de laço),
  na ordem de 1–2% do frame. O perfil R68 mostra `R_RenderSegLoop` com 15% das amostras e plano no nível de instrução.
- Risco real a medir: GCC pode derramar locais na pilha e ampliar o prólogo; por isso A1 e A2 são flags separadas.

## Proposta (aguarda autorização do mantenedor)
Compilação A/B **não instrumentada**, 4 ROMs a partir deste commit, todas com `DOOM_R57_VIEW_*` do R66 (H40 16/16):
`r66-control`, `r70a1` (LOCALS), `r70a2` (INVARIANTS), `r70a12`. Verificar: controle byte a byte igual ao R66 original, tamanho da ROM e BSS
de cada uma; depois timedemo completo no BlastEm (mesma ordem de captura da R66), e hash de frame para provar pixel idêntico.


## Preparação da A/B (aprovada pelo ChatGPT para preparo; execução aguarda o mantenedor)
- Proposta de workflow (INATIVA, fora de `.github/workflows`): `docs/review-r70/r70a-build.workflow-proposal.yml`.
  Ativação = copiar para `.github/workflows/r70a-build.yml` nesta branch e commitar (único gatilho: push desse arquivo nesta branch; também `workflow_dispatch`).
- `scripts/lab/build_r70.py`: 4 ROMs (`r66-perf` = controle, `r70a1`, `r70a2`, `r70a12`), H40 crop 16/16, sem R68. Cada variante é compilada numa cópia própria do checkout
  (`R70_WORK`), sem resíduos compartilhados. O controle usa o nome de build `r66-perf` porque o nome vira `DOOM_BUILD_ID` na ROM e o `cmp` contra o original exige bytes idênticos.
  Verificações: flags = controle + só as próprias, paletas idênticas, BSS <= 57.920 B, ROM <= 4 MiB, símbolos de captura presentes.
- Workflow: checkout, ancestral `f5a9daa`, testes host (equivalência do laço, ferramentas, inércia), build, manifesto (tamanho, BSS, SHA-256), disassembly comparativo,
  `cmp` do controle com o run 40231459814 (falha o workflow se diferente), 5 capturas de timedemo (controle, A1, A2, A12, repetição do controle),
  comparação, anotações e artifact `doom-md-r70a-ab` (`if: always()`).
- `scripts/lab/r70_capture.py`: BlastEm via RSP, breakpoint em `I_FinishUpdate`, grava tic, vblank e o framebuffer real do renderizador (3344 B, SHA-256 e bytes brutos).
  O teto de 10.000 quadros foi retirado pelo mantenedor: captura a DEMO3 inteira e para ao fim da demo.
- `scripts/lab/r70_compare.py`: casa quadros por tic; compara pixels (lista posição e diferença máxima), tempo por quadro (média, p50, p90, terços da demo, mais rápido/igual/mais lento),
  determinismo do controle repetido; marca regressão em qualquer terço > +0,5% e indica a variante pixel-idêntica mais rápida (não força A12).
- `scripts/lab/r70_disasm_compare.py`: listagem completa e contagem estática (instruções, bytes, acessos à memória absolutos/frame/indiretos, chamadas, mul/div, movem) de
  `R_RenderSegLoop` e `R_StoreWallRange` (o primeiro pode estar inlinado pelo LTO); inclui os sufixos `.lto_priv/.isra/.part`.
- Testes: `test_r70_tools.py` (parser, captura com RSP simulado, relatório de comparação) e `test_r70a_segloop.py`.

## Limites
- A comparação de pixels usa o framebuffer do renderizador (`r22_fb`, 76x44), antes do envio ao VDP; não cobre HUD nem a paleta/VDP.
- A medição é do BlastEm (resolução de um vblank por quadro, agregada em ~2.100 quadros); o Mega Drive real continua sendo a referência final.
