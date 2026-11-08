# Resposta do Cláudio à revisão S2e: caminho para ficar acima do Mega Drive nativo

**Base lida:** `SCD-S2E-REVIEW-CLAUDIO.md` (`f11b12d`) e `s2d/md_live.c`.
**Critério do usuário (2026-11-08):** equivalência exata com o nativo não é necessária. Desvios valem se melhorarem muito o desempenho.
**Legenda:** [D] demonstrado pelos números do handoff · [H] hipótese · [P] trabalho proposto.

## 1. Diagnóstico
- [D] **Render/DMA no MD = 14,25 de 19,04 VBlanks (75%)**, e é uma tarefa serial no MD. Com o resto zerado, o teto é ~4,2 FPS.
- [D] **Isso é mais lento que o quadro nativo inteiro.** No spawn do E1M1, o nativo fez 313 VBlanks / 24 quadros = **13,0 VBlanks por quadro**, já com lógica e render (benchmark 03E). O render sozinho, no modo SCD, custa mais que o quadro nativo completo.
- [H] **Suspeitos dentro dos 14,25,** lidos no código (`md_live.c` 136–143). A cada quadro:
  - `S2A_Display()` e depois `R20_StopVideo()`;
  - `SYS_disableInts()` + **2× `VDP_drawText`**;
  - ritmo/espera de VBlank do caminho de display.

  Pode haver também custo de ler proxies na Word RAM ou de `R23_SET`.
- [D] **A arquitetura atual não tem como superar o nativo de forma significativa:**
  - o MD continua fazendo a parte mais cara (render) e ainda soma aplicação de estado (3,64);
  - o Sega CD faz a parte barata (lógica);
  - e em série com o quadro (1 tic por quadro, 9% da velocidade do jogo).

## 2. Recomendação: 4 marcos, cada um medido e reversível
### M0. Instrumentar e tirar o desperdício do quadro MD [P] (pequeno)
- **Contadores separados** em `S2A_Display`, nos dois builds, nativo R128 e S2e, **na mesma cena** (spawn do E1M1, 24 quadros):
  1. `R_RenderPlayerView` (rasterização);
  2. conversão para o plano (R79/R91/R115);
  3. DMA/upload + espera de VBlank;
  4. `R20_StopVideo`;
  5. texto.
- **Resolução:** `_g_vblankCount` é grosseiro. Somar quadros (média de 24) ou usar o HV counter do VDP para frações de VBlank.
- **Correções baratas,** e cada uma medida:
  - `VDP_drawText` **uma vez**, não por quadro;
  - verificar se `R20_StopVideo` a cada quadro é necessário (o nativo não faz isso em todo quadro? confirmar);
  - nenhum `SYS_disableInts` extra no caminho.
- **Aprovação:** o render SCD na mesma cena ≤ o render nativo medido do mesmo jeito. Senão, explicar a diferença antes de seguir.

### M1. Lógica a 35 Hz contínua no Sega CD (velocidade correta do jogo) [P]
**Política:**
1. O sub roda `G_Ticker` **no próprio relógio**, sem esperar o MD:
   - acumulador com o stopwatch do sub (`$FF800C`, ~30,72 µs, volta a cada ~125,8 ms, então somar deltas a cada iteração);
   - um tic a cada 28,571 ms.
2. **Teto de recuperação:** no máximo 4 tics atrasados por iteração. O excesso é descartado (o jogo desacelera em vez de entrar em espiral) e contado em `dropped`.
3. **Input:** o pacote de cada troca traz o input atual. O sub usa esse input em todos os tics até a próxima troca, como a R128 nativa, que lê o controle uma vez por quadro e usa o mesmo comando nos tics do quadro.
4. **Troca:** o sub só atende `$A12018` **entre tics**, com latência ≤ 1 tic.
   - Publica o estado do **tic mais recente**, troca, faz ACK e lê o input.
   - O MD nunca recebe um estado no meio de um tic.
5. **Deltas:** passam a ser "desde o último estado **entregue**", e não desde o tic anterior. As marcas de sujo de setor/side/R24 acumulam até a entrega e só então são zeradas. Os atores continuam em snapshot completo.
6. **Medidas novas** (no pacote e no relatório):
   - tics executados por segundo emulado;
   - `dropped`;
   - tics entregues por quadro;
   - **custo do tic no sub** (stopwatch por `G_Ticker`: média e máximo).

   Isso responde se o sub sustenta 35 Hz.

**Aprovação:**
- o jogo anda em tempo real: 35 tics por segundo emulado ± 2%, `dropped` = 0 no roteiro;
- o FPS de apresentação não piora;
- as auditorias continuam passando no mesmo binário.

**Se o sub não sustentar 35 Hz:** desvios permitidos pelo usuário, medidos e anotados:
- A_Chase/A_Look a 17,5 Hz por monstro (alternado por endereço, como o sight R128);
- corpos e decoração sem thinker;
- visão pelo ASIC.

### M2. Render no Sega CD, onde o estado já está [P] (o salto)
**Por que agora, e por que no sub:** o sub **já tem mundo e atores reais** em RAM.
- Renderizar lá elimina de uma vez a serialização de mundo/atores, os proxies MD, a aplicação de 3,64 VBlanks e os backups de banco.
- O MD vira terminal: controle, conversão para o plano + entrega, HUD e som.

**Divisão:**
- **sub:** lógica a 35 Hz (M1) + `R_RenderPlayerView` → framebuffer pixel4 (3.344 B) no banco dele;
- **MD:** a cada troca recebe o framebuffer e roda a conversão R128 (R79/R91, tabelas na ROM) + entrega. Usar o caminho direto do FrameDelivery quando a conversão gerar o layout de plano: 2 DMAs no VBlank, ~1,8 ms.
- **HUD:** pacote pequeno com vida, munição, armas, chaves, rosto e mensagem. Psprites (arma) desenhados pelo sub no framebuffer, como o render R128 já faz.
- **Som:** fila de eventos (id, origem) no pacote, tocada pelo MD.

**Primeiro passo de memória, antes de codar:**
- `s0_report.py` com o conjunto do sub de agora + `r_*`;
- defines do sub sem SRAM e `-UDOOM_R12_RECIP_LUT` (sem a tabela de 127 KiB);
- identificar o uso de `r84_pixels` (136 KiB).

**Orçamento** (`_end` atual = 0x60680):
- as reservas de stream 0x68000–0x7BFFF (80 KiB) deixam de existir no M2;
- o código de render entra no lugar delas e do heap que sobrar;
- **o loader precisa passar de 128 KiB:** copiar a imagem em várias janelas, trocando os bits BK de `$A12003` (bits 6–7), o banco da PRG-RAM visto em `$420000`, com o sub parado em bus request, como hoje.

**Texturas/sprites/flats:** do cache de lumps de 128 KiB (DIR/LUMP já existem), sem despejo dentro da fase. Medir o pico no E1M1–E1M9. Se não couber: despejo LRU só de lumps de textura/sprite, que o render pede por número a cada uso.

**Expectativa [H]:**
- render no sub ≈ render nativo / 1,65, menos o custo de SRAM/proxies;
- quadro ≈ max(MD: conversão+entrega+HUD ≈ 2–3 VBlanks, sub: lógica do quadro + render).
- **Meta de aprovação:** FPS no spawn do E1M1 **> 4,6** (nativo) com o jogo em tempo real (M1).

### M3. Se o sub virar o gargalo: dividir lógica e render [P]
- O MD volta a rodar `G_Ticker` (o código R128 dele) e manda ao sub os deltas de mundo + atores. **É a mesma máquina de serialização S2b/S2c, no sentido inverso.**
- O sub fica só com o render, desenhando o estado N enquanto o MD roda N+1 (1 quadro de atraso).
- Quadro ≈ max(lógica MD, render sub).
- **Só fazer se o M2 mostrar o sub saturado** com lógica + render.

## 3. Respostas diretas às perguntas do handoff
1. **Cadência:**
   - acumulador no relógio do sub, um tic a cada 28,571 ms, no máximo 4 tics de recuperação por iteração;
   - input amostrado por troca (igual à R128), troca só entre tics, deltas "desde a última entrega";
   - **primeiro teste:** o M1 com a mesma cena e o roteiro atual.
2. **Render:** a instrumentação do M0. Os 5 contadores em `S2A_Display`, nos dois builds e na mesma cena. Só então escolher o caminho. A recomendação já é o render no sub (M2), porque ali somem também os 3,64 de atores.
3. **Menor conjunto `r_*`:**
   - `r_main`, `r_bsp`, `r_segs`, `r_plane`, `r_things`, `r_draw` (com o kernel R60, já usado no sub no 03D), `r_data`, `r_sky` + `tables`;
   - sem SRAM, sem a recíproca de 127 KiB.
   - **Medir primeiro com o S0** e com `-Wl,--gc-sections` a partir do novo `sub_main`.
4. **Atores:** não vale investir em compactar ou em subsectorID agora. O M2 elimina essa etapa. Se o M3 for necessário, aí sim, no sentido inverso.
5. **Validação:** manter as auditorias. Acrescentar ao roteiro:
   - porta abrindo/fechando;
   - coleta de item;
   - morte do jogador e reinício;
   - travessia de vários setores;
   - limite de 64 atores (forçar spawn);
   - START → saída;
   - cena com inimigo parcialmente encoberto.
   - **No M2:** framebuffer do sub × framebuffer do render MD do mesmo estado, em checkpoints. Diferença de poucos pixels é aceitável; quadro errado não.
6. **Marco jogável seguinte:** M0 + M1 na mesma ROM, A/B no spawn do E1M1:
   - FPS de apresentação;
   - tics/s;
   - `dropped`;
   - custo do tic no sub;
   - os 5 contadores de render.

   Depois, a ROM M2 com a meta > 4,6 FPS. As duas com tela de diagnóstico e START → jogo.

## 4. Desvios aceitáveis, a usar só se medidos e se renderem muito
- IA a 17,5 Hz por monstro;
- visão aproximada pelo ASIC;
- corpos que somem (já na R128);
- sprites distantes cortados (já na R128).

**Não reduzir resolução nem qualidade de imagem** (pedido do usuário).
