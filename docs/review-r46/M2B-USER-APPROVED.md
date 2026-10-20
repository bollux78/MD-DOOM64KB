# R46 M2B — validação do usuário, 20/10/2026

O usuário confirmou: **"tres roms aceitas e funcionando corretamente"**. O conjunto `doom-md-r46-primary-perf.bin`, `doom-md-r46-m2b-perf.bin`, `doom-md-r46-m2b-play.bin` foi aprovado para continuar o desenvolvimento.

A captura de benchmark não foi fornecida nesta etapa; portanto, a aceitação **não** comprova numericamente 11,80 FPS nem 180,82 segundos para a M2B. Esses são os benchmarks anteriores da M2A usados como referência, não resultados medidos nesta mensagem. O usuário confirmou funcionamento das três ROMs.

A M2B foi validada na CI [#39413007853](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39413007853): oracle de clipping 76×44, três ROMs compiladas e inicializadas no BlastEm, BSS 57.692 B comparada com 57.724 B no controle, sem arrays de clipping duplicados. Artefato [#12259982916](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39413007853/artifacts/12259982916).

A próxima etapa inicia na branch derivada M2C, com visplanes/BSP/sprites independentes da geometria 8×8 ativa. **Não** habilitar a alternância real 8×8/4×4 até M2, M3 e M4 terminarem.

A preferência do usuário é deixar flexível a composição visual: céu pode ser plano B ou software; arma/HUD podem aproveitar plano B se mais adequado, ou arma em sprites de hardware; não predeterminar decisão sem medir consumo de VRAM/paletas.
