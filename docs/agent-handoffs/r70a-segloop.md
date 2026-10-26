# R70-A — R_RenderSegLoop (sem perda visual)

Branch `exp-claudio-r70a-segloop-20261026`, base R66 `f5a9daa` (imutável). Estado: **código + testes host prontos; nenhuma ROM compilada**.

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
