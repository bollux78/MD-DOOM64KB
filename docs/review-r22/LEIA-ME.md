# R22 — primeiro protótipo próprio de render76x44 / pixels4x4

Base lógica: código daR21, mantendoBSP/sight iterativos, matemáticaM1/M2/M3 e cache direto. Controle é aR21V2c com música confirmada no console:174,68s/12,22FPS;BlastEm172,48s. N3/N4 desligadas.

## ROMs e ordem

1. `doom-md-r22-pattern-p4.bin`:padrão de quadradinhos4x4, cada um com sua cor. Conferir se aparece estável, sem deslocamento de linhas nem tiles quebrados. É uma imagem parada, não uma demo; não há tempo final nem promessa de música nesse padrão.
2. `doom-md-r22-diag-p4.bin`:DEMO3 com diagnóstico. Deve terminar2134frames,erro0 e pilha abaixo de2560. O detector também protege o framebuffer com canários; falhas de alocação/limite de geometria devem aparecer como texto.
3. `doom-md-r22-p4.bin`:DEMO3 sem diagnóstico para medirtempo/FPS. O custo de quatro vezes mais amostras é novo; não esperamos automaticamente superar o8x8.
4. `doom-md-r22-control.bin`:controle8x8/V2c, para referência na mesma sessão/clock.
5. `doom-md-r22-play-p4.bin`:jogável, sem timedemo, músicaE1M1 e controles anteriores. Conferir menus, paredes, sprites/arma,H​​UD e áudio.

Primeiro testar noBlastEm e enviar imagens do padrão e da demo. Se travar, anotar nome e ponto. Depois finalista no hardware original a7,67MHz. Não há dependência deSRAM.

## O que mudou

Amostras independentes76x44 cobrem a área nominal304x176pixels. A faixa superior8px continua reservada aoFPS e texto, e a borda esquerda8px é preservada no jogo. Cada byte do framebuffer guarda duas cores de4bits:1672bytes+canários. Não é ampliação das células38x22.

Paleta global16cores:14representantes daPLAYPAL mais preto e branco. Texturas e iluminação passam pelo colormapDoom e são quantizadas para essa paleta. Paletas de dano/item são derivadas daPLAYPAL. É uma troca de cor por detalhe; não mantém as56cores simultâneas do8x8. Pisos/tetos continuam no caminho de cores planas da base; não se adicionou mapeamento de textura aos pisos nesta rodada. Gamma não foi implementado neste backend inicial.

Duas páginas naVRAM evitam atualizar os tiles que estão sendo exibidos. A CPU expande os quadrantes4x4 direto para a página oculta, tile a tile; só a troca do tilemap ocorre noVBlank. As interrupções ficam mascaradas por um único tile de32bytes, com oportunidade de serviço doXGM entre tiles. O volume de dados gráficos é maior, mesmo sem um framebuffer expandido naRAM.

LayoutVRAM:tiles16..851 e852..1687 para as páginas;fonte1696..1791;BG_AemE000;BG_BemF000;SAT/HScroll compartilhamFC00 e permanecem zerados (nenhum sprite de hardware; spritesDoom são software). O texto usa prioridade deBG_B nas22linhas superiores;HUD naslinhas23/25 deBG_A. Não ligar o sprite engineSGDK nesse layout sem reprojetá-lo.

Openings dobra para76colunas, com a mesma capacidade relativa de16porcoluna, mas é alocado noheapSGDK DEPOIS de oSDK terminar de mover/carregar a fonte. A zonaDoom43KiB permanece intacta. A capacidade de64drawsegs da base é preservada e, se excedida, o protótipo mostra erro em vez de ocultar paredes silenciosamente. O relatório deheap acompanha oZIP.

## Evidências e limites

Fonte e scripts embranchr22-px4. O pacote incluiBIN/ELF/flags/logs, orçamento deRAM, hashes e testeCPU das primitivas. Testes nativos conferem65536combinações de quadrantes,4096colunas reais,3344amostras,canários e layoutVRAM. O probeMC68000 usa os mesmos helpers. Isso não valida timing real doVDP nem execução integral deDEMO3:essa etapa depende dos testes no emulador/console.
