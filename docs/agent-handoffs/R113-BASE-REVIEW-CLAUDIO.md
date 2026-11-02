# R113 hilut: pedido de revisão para o Werk (base candidata final do E1 shareware)

**Pergunta do usuário:** ainda dá para tirar desempenho da R113? Se não, ela vira a base final do E1.
Não é pedido de reabrir cores, Shadow ou menu (decisões fechadas). Só velocidade, com imagem idêntica.

## 1. Identificação
| Item | Valor |
|---|---|
| ROM de entrega | `doom-md-r60-r113-hilut-pl.bin`, sha256 `3106d4ede3c1c441ac5905ec181c9babba691dd5e245413c68d97192230c25c8` |
| PERF (A/B) | `r113-hilut-pf`, sha256 `e181c87742426e65bac78b14e061fba21d8834b27689c2b6c45cc1b84bfd4a48` |
| ROM / BSS | 3.670.016 B (usados ~3,65 MB); BSS 57.876 (folga 44); heap livre no fim do benchmark 770 B |
| Pilha | pico 1.632 de 2.562 B (DEMO3 até o tic 400) |
| Branch / run | `exp-claudio-r113-hilut-20261102` (`61b1523`), run 41464372009 (artefato `doom-md-r113-hilut`) |
| Workflow | `.github/workflows/r113-claudio-hilut.yml` (controle R107 direct no mesmo job) |

## 2. Cadeia (cópia descartável)
```
apply_r81 → R80 P1+F1 → R83 sprites → R85 all → R88 ai → apply_r89 → R90 control → R91 sh1 → R92 toggle
→ R95 flat → R96 wall → R97 shasm → R98 sprmul
→ apply_r100 (R100_MODE=f1t R100_PREFIX=r102 R100_NAME=twoface)   # loop de colunas em cópias especializadas
→ apply_r104 (R104_PREFIX=r105 R104_NAME=twoface)                 # janelas de SRAM com IRQ mascarada
→ apply_r107                                                       # colunas pré-montadas R84 lidas direto da ROM
→ apply_r113                                                       # kernel de parede sem LSL.B #4
→ build_r71a12mul_hud.py
```

## 3. Medidas (benchmark completo DEMO3 E1M1, AI Normal)
| ROM | Console Off | Console On | BlastEm Off | BlastEm On |
|---|---|---|---|---|
| R92 toggle (referência antiga) | — | — | 272,95 s | 302,18 s |
| R104 maskdiag (primeira com a correção da SRAM) | — | 278,73 s | — | — |
| R105 twoface | — | 276,77 s | — | 274,85 s |
| R107 direct | — | 273,17 s | 252,18 s | 271,53 s |
| **R113 hilut** | **250,52 s (8,52 FPS)** | **269,90 s (7,91 FPS)** | ≈250,5 s (A/B −0,66%) | ≈269,8 s (A/B −0,64%) |

E1M7 Shadow On (console, maskdiag): 421,92 s (5,06 FPS). O BlastEm serve para triagem/equivalência; a decisão é do console.

## 4. Onde vai o tempo (R110 profile da R107, BlastEm, início do E1M1; R113 só encolhe o kernel)
| Função | Off | On | Observação |
|---|---|---|---|
| `R_Subsector` (loop de colunas inline, 6 cópias) | 34,7% | 32,2% | frame de 272 B, ~35 RMW na pilha; perto do limite de registradores |
| `R60_WallColumn` (R113 nas paredes do loop) | 12,0% | 11,2% | ~116 ciclos por par de pixels após R113 |
| `R_DrawSegTextureColumn` | 10,6% | 9,9% | inclui o preparo inline da parede (R96: dst, fase com MULS, LUT) |
| `D_DoomLoop` | 7,8% | 7,8% | ~4% é espera do VBlank em `R20_StopVideo` (sem 2º framebuffer) |
| `R97_ShadowJoint` | — | 6,0% | passe da Shadow p=0 em asm |
| `R_PointToAngle16` + `R_ScaleFromGlobalAngle` | 5,7% | 5,4% | por seg |
| Sprites (`R_DrawColumnSprite`, `R_DrawVisSprite`, `R_ProjectSprite`) | 8,2% | 8,1% | sprites usam o kernel R60 (mascarado) |
| `R23_MapRead` (SRAM) | ~3,5% | ~3% | inflado pelo viés do perfil: amostras com IRQ mascarada caem logo após o desmascaramento |

O perfil é por amostragem no VBlank (`scripts/lab/r94_pcprofile.py`): uniforme em tempo emulado, mas cobre só ~470 tics (limite de 10.000 quadros).

## 5. Já testado e descartado (não repetir sem ideia nova)
| Item | Resultado |
|---|---|
| R98 texcol (`R20_WALL_HOIST`), R98 segsplit | empate / +0,7% |
| R99 texsplit, angcache (cache de vértices), recip (divisão em C) | +0,8% / ruído / +0,4% |
| R101 F1b (cópia de duas faces sem masked) | empate |
| R102 bits (muls 16 bits em sight/maputl + tabela de linha) | −0,2% (ruído) |
| R108 halfwall / R109 halfsprite (meia altura) | +1% / +0,3%: só ROM; reservado para E2/E3 |
| R111 colsrc (busca de coluna inline no loop) | **+3,3%** (spills); variante noinline +0,6% |
| R112 onemul (uma MULS no prólogo sprite/R42) | +0,02% |

Lição recorrente: qualquer coisa que aumente a pressão de registradores do loop inline de `R_Subsector` piora mais do que ganha.

## 6. Ideias que ainda não testei (para a sua avaliação)
1. **Kernel de sprite sem `LSL.B #4`** (mesma técnica da R113 no caminho `R_DrawColumnSprite` → R60, quando a LUT é composta).
   O fuzz usa tabela não composta: precisa de guarda. Teto ~0,3–0,5%.
2. **Fase inicial da parede sem MULS por coluna** (R96): `(yl-CENTERY)*fracstep` 16×16 a cada coluna. Exige estado incremental
   no loop, que tem o risco de spill da R111.
3. **Espera do VBlank (~4%)**: segundo framebuffer de 3.344 B não cabe (BSS 44 B, heap 770 B). Alternativas a avaliar:
   recortar o framebuffer de trás ao retângulo do crop; ou ordenar trabalho que não toca o framebuffer
   (projeção de sprites, `R_SetupFrame`, limpeza de clip) para depois da espera hoje feita no início de `R22_BeginFrame`.
4. `R_PointToAngle16` por seg (5%): o cache por vértice deu ruído na R99; uma tabela de ângulo por linha recalculada só quando
   o jogador se move talvez renda, mas custa RAM.
5. Opções de compilação por arquivo/função (ex.: `-fno-tree-...`, `optimize` em `R_Subsector`): nunca medidas
   isoladamente desde a R100.

## 7. Regras que valem para qualquer candidata
- Uma mudança por candidata, controle R113 no mesmo job, pixels idênticos (Off e On A2/L3 pós-passe), pilha e BSS ≤ 57.920.
- Nada de `$A130F1` fora de `R25_SRAM_BEGIN/END` (correção do console da R104).
- Validação final no console: E1M1 Off/On e E1M7 On.
- Se nenhuma candidata passar de ~0,5% no console, a R113 vira a base final e seguimos para o pipeline do Doom registrado
  (E1 gerado a partir do WAD do usuário como teste com gabarito, depois E2/E3 com halfwall/halfsprite).
