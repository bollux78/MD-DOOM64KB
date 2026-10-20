# R40ci — intermissão reparada, sem regressão de FPS

O usuário confirmou visualmente que a intermissão E1M1 agora apresenta corretamente E1M1: Hangar / FINISHED, Kills/Items/Secret, Time/Total/Par e a arte Bayer8. A correção troca VIEWWINDOWWIDTH/HEIGHT por WI_TEXT_WIDTH/HEIGHT 38×22 no layout textual, mas mantém renderer 3D 76×44.

DEMO3 NTSC de 2.134 quadros em `doom-md-r40ci-p4perf`: **3,01 FPS**, tempo **709,67 s**, mínimo 1,8 e máximo 3,9 FPS. Esses valores coincidem com a referência R40c pixel4 anterior. Usuário confirmou que a versão `r44-asm-p4play` com a mesma correção funciona no jogo e na troca de fase.

A R40ci preserva o caminho 4×4 anterior ao ASM como controle. A R44 ASM passa a ser o candidato 4×4 otimizado para a futura R40c dual, após mescla seletiva, testes de coexistência, SRAM e VDP.
