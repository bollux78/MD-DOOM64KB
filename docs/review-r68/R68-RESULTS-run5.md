# R68 — primeiro resultado de profiling (run 40324159678, commit 2ec16cb)

Diagnóstico apenas. FPS do R68 NÃO é comparável ao R66 (instrumentação). Fonte: anotações do run
(report.md truncado em 2 partes); a tabela de PC no report tem bug de formatação (fração impressa
como %, corrigido depois deste run): leia "0.3%" como ~30%.

- Controle R66 reconstruído == artefato original (cmp OK). BSS: R66 57.900 B, R68 57.904 B (teto 57.920).
- Captura: 451 quadros (início do DEMO3, ~21% da demo), 4.932 vblanks, média 10,94 vb/quadro, p50 10, p90 17, p99 19, máx 57.
- Lógica 9,9% / render+vídeo 90,1% dos vblanks. Quadros 10% mais lentos = 16,9% do tempo; 50% mais lentos = 66,9%.
- Carga média por quadro: bspnode 18,3 | addline 28,6 | seg 9,3 | col 160,5 | wall 123,1 | flat 126,2 | pta 93,6 | sprproj 10,7 | sprdraw 3,2.
- Modelo de custo: R²=0,75, custo fixo ~493k ciclos/quadro (~36%); coeficientes instáveis (contadores correlacionados; alguns negativos) — não usar como medida.

## Amostras de PC (top, todos os quadros; total estimado ~19-21k amostras)
| função | amostras | ~% |
|---|---:|---:|
| R_Subsector (LTO, inclui código inlinado) | 5138 | ~25 |
| R_DrawColumnFlat | 2139 | ~11 |
| R42_DrawPackedWall | 2088 | ~10 |
| R60_WallColumn (kernel ASM) | 1659 | ~8 |
| R_DrawSegTextureColumn | 1270 | ~6 |
| R_DrawColumnSprite | 952 | ~5 |
| D_DoomLoop (LTO) | 944 | ~5 |
| R_PointToAngle16 | 735 | ~4 |
| R_DrawVisSprite | 462 | ~2 |
| __mulsi3 + __udivsi3 | 705 | ~3,5 |
| R_ProjectSprite | 349 | ~2 |
| R_ScaleFromGlobalAngle | 298 | ~1,5 |
| P_RecursiveSound/CheckSight/CheckPosition/MobjThinker/G_Ticker/... | ~1000 | ~5 |
| R23/R27 leitura de mapa | ~475 | ~2,5 |

Limitações: o HInt não amostra o VBlank (~15% do tempo de quadro; inclui o upload de vídeo); `R_Subsector`
e `D_DoomLoop` agregam funções inlinadas pelo LTO; só o início da demo foi capturado.
