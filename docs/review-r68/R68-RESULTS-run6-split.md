# R68 SPLIT — profiling com funções separadas (run 40330475299, commit 08a1c88)

Diagnóstico apenas (R66 segue baseline, 7,21 FPS). `-DDOOM_R68_SPLIT` força noinline nas funções do BSP/seg/
sprites/planos; os tempos por função são indicativos (layout de código ligeiramente diferente).
Captura: 433 quadros do início do DEMO3, 4.932 vblanks, média 11,39 vb/quadro. Controle R66 reconstruído == original. ~19,6k amostras.

## Amostras de PC, todos os quadros (% das amostras; o HInt não vê o VBlank)
| grupo | funções | % |
|---|---|---:|
| laço por coluna/segmento (C) | R_RenderSegLoop 16,9 | 16,9 |
| desenho de parede | R42_DrawPackedWall 10,2 + R60_WallColumn (ASM) 8,0 + R_DrawSegTextureColumn 6,3 | 24,5 |
| desenho de chão/teto | R_DrawColumnFlat 11,1 | 11,1 |
| sprites (desenho) | R_DrawColumnSprite 4,5 + R_DrawMaskedColumn 2,2 + R_DrawVisSprite 1,0 | 7,7 |
| setup por segmento + geometria | R_StoreWallRange 4,9 + R_PointToAngle16 3,5 + R_ScaleFromGlobalAngle 1,8 + __mulsi3 2,4 + __udivsi3 1,2 | 13,8 |
| BSP | R_AddLine 2,3 + R_CheckBBox 1,5 + R_RenderBSPNode 1,1 + R_ClipWallSegment 1,0 + R_Subsector 1,2 | 7,1 |
| sprites (projeção/ordem) | R_ProjectSprite 2,0 + R_AddSprites 0,3 + R_DrawMasked 0,9 + R_GetColumn 0,9 | 4,1 |
| lógica | P_RecursiveSound, P_CheckSight, P_MobjThinker, P_CheckPosition, G_Ticker, ... | ~5,5 |
| streaming de mapa | R23_MapRead/Write, R27_ReadBlock, node_read | ~2,9 |

## Leitura
- O kernel ASM da parede (R60_WallColumn) é só 8% das amostras; o C ao redor (R_RenderSegLoop + R42_DrawPackedWall +
  R_DrawSegTextureColumn) soma 33,4%. O custo por coluna está no código de preparação, não no kernel.
- Slowest 20% vs fastest 50%: nos lentos, R_DrawColumnFlat (11,9% vs 8,2%) e R_StoreWallRange (7,3% vs 3,0%) pesam mais;
  nos rápidos, R60_WallColumn e sprites.
- Cargas médias/quadro: col 164, flat 131, wall 126, pta 96, addline 29, seg 9,6 (contadores correlacionados; modelo R²=0,76 só ilustrativo).
