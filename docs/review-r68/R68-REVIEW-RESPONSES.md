# R68/R69 — resposta às 7 observações da revisão do ChatGPT (R68-R69-REVIEW-CHATGPT-20261026)

Dados: run 9 (`40345181424`, 912 quadros, tics 0..912). Conclusões separadas do trabalho da R70-A.

1. **"wall column C glue" desagregado** (% das amostras de PC, todos os quadros): `R_RenderSegLoop` 15,0; `R42_DrawPackedWall` 9,4;
   `R_DrawSegTextureColumn` 5,0; `R_GetColumn` 1,0. Soma 30,4%. O laço `R_RenderSegLoop` sozinho é metade do grupo; o kernel ASM
   (`R60_WallColumn`) é 9,3% à parte. O agrupamento no `GROUPS` continua útil para tendência, mas as conclusões devem citar estes valores por função.
2. **"segment setup + geometry" (15,0%) não é só `R_StoreWallRange`:** `R_StoreWallRange` 5,3; `R_PointToAngle16` 4,0; `__mulsi3_internal` 2,2;
   `R_ScaleFromGlobalAngle` 2,1; `__udivsi3_internal` 1,2 (+0,2 outros). Só 35% do grupo é `R_StoreWallRange`; ~64% é matemática compartilhada
   (ângulos, multiplicação, divisão) cujos chamadores o amostrador de PC não identifica. O teto realista de uma otimização só em `R_StoreWallRange`
   (R70-C) é ~5% das amostras; para atacar `__mulsi3`/`__udivsi3` é preciso atribuir chamadores (próximo passo: amostrar também o endereço de retorno).
3. **Resolução de 8 bytes / disassembly:** a primeira versão do `hotspots()` mandava o objdump começar no meio de uma instrução (`.short`, `Address ... out of
   bounds` nos hot spots da run 9), então os trechos de instrução daquela run NÃO são confiáveis. Corrigido: a função é desassemblada inteira a partir do início e cada
   bucket mostra a instrução que o contém (teste `test_hotspot_listing`). Vale a partir da run 10. A R70-A gera, além disso, a listagem completa das rotinas por variante.
4. **Cobertura de ~43% da DEMO3:** correto e não generalizável. O teto de 10.000 quadros emulados foi retirado pelo mantenedor em 26/10; a captura agora para sozinha ao fim da demo
   (tic reinicia ou para de avançar por 300 quadros). A run 10 refaz o perfil R68 sobre a DEMO3 inteira; os percentuais da run 9 valem só para os tics 0-912.
5. **Ambiguidade de 6 linhas do contador V:** os valores 0xE5-0xEA aparecem duas vezes por quadro (linhas 229-234 e 235-240, ambas no vblank). Só carimbos tirados nessas linhas são afetados;
   o erro máximo é 6 linhas (~2.900 ciclos, 0,23% de um quadro de 10 vblanks), mas pode distorcer as fases curtas (setup ~50 linhas, flip ~15). As fases grandes (BSP+planos 77%, lógica 11%) são
   imunes na prática. Quadros com algum delta negativo são descartados: 6 de 450 na run 8 (1,3%) e 6 de 912 na run 9 (0,7%), o que limita o viés. A soma das fases é telescópica, então não serve de prova de ausência de erro.
6. **Quadros emulados vs vblanks:** na run 9, 18.000 quadros emulados ≈ 8.927 vblanks contados pelo jogo; na run 8, 10.000 ≈ 4.930 (razão ~0,49 nas duas). Hipótese: o parâmetro `-b` do BlastEm conta
   cerca de 2 unidades por vblank do jogo. Não confirmei no código-fonte do BlastEm. A razão é estável, então os resultados relativos não são afetados; o novo workflow R70-A registra `last_vb` por captura para confirmar.
   **R69, "sétima ROM":** eram 7 ROMs no build: 1 controle R66 não instrumentado (usado só no `cmp` byte a byte contra o original) + 6 instrumentadas (w32, w24, w16, w08, w00, h32).
   A tabela resumida mostra as 6 instrumentadas; w16 faz o papel de controle instrumentado.
7. **Inércia por fonte vs binário:** concordo que `check_r68_inert.py` prova só equivalência de fonte normalizada. A garantia binária é o `cmp` do controle reconstruído contra o artefato original (run 40231459814):
   passou nas runs R68 (incluindo a 9) e R69, e a R70-A mantém a mesma exigência (o workflow falha se o `cmp` falhar).
