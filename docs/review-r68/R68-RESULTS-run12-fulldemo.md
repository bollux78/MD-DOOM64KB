# R68 run 12: DEMO3 inteira (run 40354948540, head do workflow após 'run 12')

Teto de quadros removido pelo mantenedor; a captura termina ao fim da demo. 2134 quadros (DEMO3 completa), 18.898 vblanks, média 8,86 vb/quadro (instrumentado, não é benchmark), p50 7, p90 16, p99 20, máx 58.
Os 20% de quadros mais lentos consomem 37,1% do tempo; os 50% mais lentos, 68,7%.

Fases (2116 quadros válidos): lógica 13,2%, setup 1,9%, BSP+paredes+planos 74,6%, masked+sprites 9,6%, HUD 0,1%, flip/vídeo 0,6%.

Amostras de PC por grupo (demo inteira): C em volta da coluna de parede 30,3%; setup por segmento + geometria 14,0%; kernel ASM da parede 11,8%; sprites (desenho) 8,3%;
lógica 8,2%; chão/teto 7,3%; BSP 7,3%; outros 7,2%; streaming de mapa 3,7%; sprites (projeção) 1,8%.

Confirma, agora para a demo inteira, a leitura da run 9: o gargalo é o C por coluna de parede e o setup/geometria por segmento, não o kernel ASM.
