# SCD 03D/03E: Sega CD como renderer auxiliar (Cláudio para o Werk)

**Branch:** `exp-chatgpt-scd-bench03b`. **Base:** 03C (`7775125`).
**Estado:** desenho aprovado pelo usuário. Ainda não há código nem execução.
**Validação:** cada teste é relatado com dois campos separados, `build: PASS/FAIL` e `blastem: PASS/FAIL`. Nada vai para o console antes de `blastem: PASS`.

## 0. Leitura do 03C
- **Geração:** 1.630 → 989 ticks, 1,65× mais rápido. É a razão dos clocks (12,5 contra 7,67 MHz). O ganho que interessa é o **paralelismo**: o principal fica livre para a lógica enquanto o sub desenha.
- **Troca + cópia (48 ms):** é custo puro e deve sumir (seção 3). A R128 já faz DMA do framebuffer em todo quadro, então o DMA a partir da Word RAM não é custo novo.
- **Verificação integral (78 ms):** só na rodada de correção, nunca na cronometrada.
- **Restrição central:** no Mode 1, o sub-CPU **não lê a ROM do cartucho**. Tudo o que ele desenha precisa estar na Program RAM (512 KiB) ou na Word RAM. A vantagem é que um mapa do E1 com as texturas cabe ali. Do lado do sub somem as janelas de SRAM (R23/R25) e os proxies da ROM (R24), justamente os custos dos picos medidos na R121.

## 1. 03D: kernel de colunas real, não um corredor sintético
O corredor sintético não tem BSP, visplanes, sprites nem o formato de textura da R128, então a medida não prevê o DOOM. O 03D mede a metade "desenho" com dados reais:

1. **Captura** (script novo, BlastEm, R128 All de 4 MiB, que não muda):
   - breakpoint na entrada do desenho de coluna da R128 (`R_DrawColumn` ou a variante pixel4 em uso; ver no `.map`);
   - em 8 quadros, gravar os parâmetros de todas as chamadas: x, yl, yh, textura/coluna, iscale, texturemid e colormap;
   - quadros: E1M1 tics 200–260, que incluem o pior quadro do jogo, o tic 237 da R126b;
   - grava também as colunas de textura usadas e o colormap, como blob, e o framebuffer final do quadro, para comparar.
   - Saída privada em `/home/dan/Projetos/Personal/scd-03d/`, nunca no repositório (é conteúdo do WAD).
2. **Kernel:** a mesma rotina de coluna da R128, copiada para `experiments/DOOM_SCD_Bench03D/src/column.s` (ou compilada do mesmo C com as mesmas flags). Roda **idêntica** no principal e no sub.
3. **Dados:** os blobs vão para a ROM do teste. Na partida, o principal os copia para a Program RAM pelo mesmo caminho do 03B. Cada comando manda só o "quadro k" (0–7).
4. **Saída:** o framebuffer no mesmo formato da R128, entregue como na seção 3.
5. **Correção, em rodada separada:** o framebuffer do sub, o do principal e o capturado da R128 têm de ser idênticos byte a byte nos 8 quadros.

**Medidas**, na rodada cronometrada, depois do aquecimento, 64 quadros (8 × 8 voltas):
- intervalo entre quadros apresentados;
- tempo de desenho no sub e no principal;
- espera do principal pela troca;
- DMA;
- **tempo livre do principal**: um laço de "trabalho útil" contado separadamente da espera ativa.

Para o tempo, usar o stopwatch com contagem de VBlanks junto, já que o stopwatch volta a zero a cada ~125,8 ms.

## 2. Word RAM 1M em dois bancos: protocolo
Notação: **N** é o quadro na tela, **X** é o banco que o principal tem agora e **Y** é o outro.

| # | Principal | Sub |
|---|---|---|
| 1 | termina o DMA do banco X (consulta o bit de DMA ocupado do VDP) | desenha N+1 no banco Y |
| 2 | escreve o comando N+2 nos registradores de comunicação | grava o ID N+1 no cabeçalho do banco e "pronto N+1" na comunicação |
| 3 | espera "pronto N+1" com prazo de 6 VBlanks; no prazo, conta um timeout e reapresenta N | espera o pedido de troca |
| 4 | pede a troca | efetiva a troca e lê o comando N+2 |
| 5 | confirma a troca e confere ID == N+1; senão conta `stale` e reapresenta N | começa N+2 |

Contadores na tela: `frames`, `stale`, `timeouts`, `swaps`.

**Conferir antes de codar**, no manual e no `segacd.c` do BlastEm:
- quem efetiva a troca em 1M. A minha leitura é que o principal pede pelo DMNA e o sub efetiva pelo RET; confirmar;
- os endereços de cada banco, dos dois lados;
- a latência da troca.

## 3. Transferência: medir nesta ordem
1. **(A) DMA direto do banco 1M para a VRAM.** É o candidato principal. O DMA a partir da Word RAM tem uma peculiaridade conhecida: a primeira palavra sai deslocada. A solução comum é começar o DMA 2 bytes adiante e escrever a primeira palavra à mão. Confirmar no BlastEm e no console com a checagem de integridade.
2. **(B) A mesma coisa a partir da área "cell image" do lado principal (1M, `$220000`).** Pelo que lembro do manual, um bitmap linear escrito pelo sub aparece ali arranjado em tiles. Se confirmar, o sub desenha colunas num bitmap comum e o empacotamento em tiles sai do hardware. O modo "dot image" do lado sub (pixels de 4 bits por endereço) também pode simplificar o kernel. Ambos são **a confirmar**: uma tela de teste com um padrão conhecido basta.
3. **(C) A cópia via WRAM do 03C,** só como referência.

Descartado: devolver comandos de desenho em vez do quadro, porque a rasterização voltaria para o principal.

## 4. 03E: o renderer inteiro no sub
Só fazer se o 03D passar.
- O `R_RenderPlayerView` da R128 compilado para o sub, com o E1M1 inteiro na Program RAM (mapa, BSP, texturas e sprites usados).
- Por quadro, o principal manda a câmera e a lista de things visíveis (x, y, z, ângulo, sprite/frame; algumas centenas de bytes) pelo banco 1M ou por um bloco pequeno de comunicação.
- **Arquitetura final:**
  - Mega Drive: lógica, entrada, áudio e DMA;
  - Sega CD: renderer.
- **Bônus para depois:** música do CD controlada pelo sub, o que tira a música da ROM e do Z80.

## 5. ASIC (rodada seguinte ao 03E)
O ASIC desenha uma linha horizontal de destino por vez, com ponto inicial e incremento. Isso é um span de chão ou teto do DOOM, cuja distância é constante na linha. Paredes não encaixam.

**A/B:**
- chão texturizado por spans no sub contra o ASIC;
- medir separadamente a montagem da tabela de traço, a execução e a espera pelo fim.

Se a R128 desenha chão sólido, o ganho do ASIC é de **qualidade** (chão texturizado sem custo de CPU), não de velocidade.

## 6. Critérios para mudar de rumo
- **03D:** o sub abaixo de ~1,4× o principal no kernel real, ou framebuffer diferente → parar e investigar antes do 03E.
- **Troca + DMA** acima de ~1 VBlank por quadro no principal → refazer a transferência (seção 3).
- **Qualquer diferença entre BlastEm e console** na troca 1M ou no DMA → a trilha trava até ser explicada.
- **03E sem ganho perceptível na lógica** no Run All → o Sega CD vira um "renderer mais bonito", não mais rápido. Decisão do usuário.

## 7. Restrições de sempre
- ROMs, WAD e capturas só em `/home/dan/Projetos/Personal/`. Nunca no repositório nem em artefato público.
- A R128 All continua sendo a base do jogo e não é modificada.
- BlastEm: no máximo 10.000 quadros por execução e configuração fixa (divisor 7).
