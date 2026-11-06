# Sega CD: ASIC gráfico como lançador de raios em lote (Cláudio para o Werk)

**Branch:** `exp-chatgpt-scd-bench03b`. **Estado:** sonda de Word RAM e replay de raios reais executados no BlastEm. O raster de duas células falhou no critério de falsos bloqueios. Não mexe no jogo.
**Relatório:**
- `build: PASS/FAIL`;
- `blastem: PASS/FAIL`;
- console fica para depois.

## 1. O que o ASIC é (e não é)
- **Função fixa, não programável.** Não é um DSP como o SVP.
- **Faz uma coisa:** para cada linha da imagem de saída (*image buffer*), recebe na *trace vector table* um início (X, Y, ponto fixo) e um passo (ΔX, ΔY). Anda pela fonte, um *stamp map* de até 4096×4096 pixels feito de stamps 16×16 ou 32×32, lê o pixel de 4 bits em cada posição e grava na saída (formato cell).
- **Não faz:** somar, comparar ou multiplicar os valores lidos, nem aplicar tabela de cor/luz.
- **Roda sozinho,** em paralelo com o 68000 do Sega CD, e avisa no fim por interrupção (nível 1).
- **Tudo fica na Word RAM:** stamps, stamp map, tabela de traço e saída.
  - **A confirmar no manual e no `segacd.c` do BlastEm:** pelo que lembro, o ASIC exige o modo **2M**, com a Word RAM inteira do lado do sub. Isso conflita com o protocolo 1M de dois bancos.
  - Antes de tudo, documentar exatamente quais modos funcionam e o que acontece se o MD acessar a Word RAM durante a operação.
- **Modos de prioridade** (*underwrite/overwrite*): opcionais, não usados neste teste.
- Manual: https://www.megadrive.org/elbarto/megacd/Official%20Sega%20CD%20Manual/segacd_toc.html

## 2. Ideia: cada linha da saída é um raio
- **Ocupação, uma vez por fase:** rasterizar o mapa numa imagem de ocupação de 4 bits.
  - Linhas de um lado só (paredes sólidas) = 1. Opcional: portas fechadas = 2. Espaço livre = 0.
  - Cerca de 8 unidades de mapa por pixel. O E1M1 cabe com folga num stamp map de 512×512 ou 1024×1024.
  - **Linhas de 2 pixels de espessura**, para reduzir vazamento em diagonais.
- **Um traço = um raio:** início = posição do monstro, passo = (jogador − monstro) / N amostras, com a mesma distância entre amostras para todos os raios (≤ 1 pixel). Rays mais longos usam mais pixels de saída. A largura da saída é o máximo de amostras; preencher o resto com passo 0.
- **Lote:** 64 raios = 64 linhas, numa única operação.
- **Leitura:** o sub-CPU procura em cada linha o primeiro pixel ≠ 0 antes da amostra final → bloqueado, ou livre.

**Uso pretendido:** pré-filtro de visão e de tiro.
- "Parede sólida no caminho" → não vê.
- "Livre" ou caso de borda → `P_CheckSight` exato (no sub ou no MD).
- O ASIC **não sabe alturas**: degraus, janelas altas e portas parciais ficam com o caminho exato.

## 3. Benchmark isolado (`experiments/DOOM_SCD_ASIC_Rays/`)
1. **Dados**, capturados do R128 All nativo no BlastEm com o WAD privado:
   - linhas do E1M1 (v1, v2, flags);
   - **pares reais monstro→jogador** de `P_CheckSight` na demo 1, tics 200–300, com o resultado exato de cada um;
   - pelo menos 256 pares. Saída privada em `/home/dan/Projetos/Personal/`.
2. **Ocupação:** o sub-CPU rasteriza as linhas na carga (ou vem pronta do host). Medir o tempo de rasterização, que acontece uma vez por fase.
3. **Três modos, nos mesmos 256 pares, em lotes de 64:**

   | Modo | Quem traça | Medir |
   |---|---|---|
   | `asic` | ASIC + varredura das linhas pelo sub-CPU | tempo de montar a tabela, do disparo até a interrupção, e da varredura |
   | `sub-dda` | o mesmo raster percorrido em software no sub-CPU (DDA) | tempo total. Controle do ganho do ASIC sobre o processador |
   | `sub-exact` | `P_CheckSight` exato no sub-CPU, com os dados residentes | tempo total. A referência de custo e de verdade |

4. **Concordância com o exato:**
   - falsos "bloqueado" (o exato vê, o ASIC diz parede) → **inaceitáveis**; o raster precisa ser conservador;
   - falsos "livre" → só custam desempenho, porque caem no exato.
5. **Tela/log:** ticks por modo (stopwatch + contagem de VBlanks, por causa da volta de ~125,8 ms), número de falsos de cada tipo e o modo de Word RAM usado.

## 4. Critérios
- **Vale seguir se:**
  - `asic` (montar + operar + varrer) for **≥ 2× mais rápido** que `sub-exact` por raio;
  - **zero** falsos "bloqueado";
  - falsos "livre" ≤ 10%.
- **Refuta se:**
  - `asic` não ganhar de `sub-dda`: o ASIC não acrescenta nada além do sub-CPU;
  - ou o modo 2M obrigatório impedir a convivência com o protocolo 1M, sem custo de troca aceitável. Medir o custo de alternar 1M↔2M por operação.
- **Se passar:** integrar como o núcleo da **visão assíncrona em lote** (V1 de `SCD-LOGIC-VECTORS-CLAUDIO.md`), em que o ASIC traça os raios de todos os monstros enquanto o MD roda a lógica.

## 5. Usos gráficos (registro, não testar agora)
- **Paredes:** uma linha do ASIC = uma coluna de parede, com passo vertical na textura. A saída sai transposta e o sub-CPU desfaz isso.
  - Problema: sem colormap, seria preciso guardar cópias das texturas por nível de luz, e a Word RAM tem 256 KB.
- **Chão e teto texturizados:** encaixe perfeito (afim por linha), mas a R128 desenha chão sólido. Seria ganho de qualidade, não de velocidade.

## 5b. Chão e teto texturizados pelo ASIC: prioridade de qualidade (usuário, 2026-11-06)
O usuário considera este o uso mais valioso do ASIC, **desde que o jogo já esteja bom sem ele**. É uma camada opcional sobre a base:
- **Pré-requisito:** a ROM única, com Sega CD e fallback, estável e não mais lenta que o nativo. Chão sólido continua sendo o padrão e o fallback.
- **Encaixe:** no DOOM, chão e teto têm distância constante em cada linha da tela, então cada span é afim. Uma linha do ASIC = um span, com início (u, v) e passo (du, dv) por linha, e o flat no stamp map.
- **Luz:** em vez do colormap, poucas faixas de luz por distância (por exemplo 4), com cópias do flat por nível, ou só o flat escurecido em degraus. Medir o espaço na Word RAM.
- **Composição:**
  - o ASIC desenha os spans de chão e teto numa imagem;
  - as paredes e os sprites sobrepõem, como o chão sólido faz hoje;
  - a ordem e a preservação de nibble seguem as regras do SPLIT-ALT.
- **Primeiro teste, isolado:**
  - só o chão do spawn do E1M1, com um flat;
  - medir o tempo do ASIC por quadro e o custo de montar a tabela de traço;
  - fazer uma comparação visual.
- **Critério:**
  - o custo para o MD é ~0 (o ASIC e o sub fazem o trabalho);
  - o quadro não fica mais lento que com chão sólido;
  - se piorar, fica como opção de menu ("chão texturizado"), desligada por padrão.

## 6. Restrições
- ROM e dados só em `/home/dan/Projetos/Personal/`.
- Nome do arquivo no header e na tela.
- BlastEm: no máximo 10.000 quadros por execução, com a configuração fixa.
- Troca 1M sempre por `$A12018`, nunca por DMNA.
- Não altera o R128 nem o 03E.


## 7. Sonda de Word RAM — resultado no BlastEm

[Execução 42298331217](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42298331217). ROM isolada em `/home/dan/Projetos/Personal/scd-asic/run-42298331217-1/doom-md-scd-asic-probe.bin`. Código em `experiments/DOOM_SCD_ASIC_Rays/`.

- A Word RAM passou de 1M para 2M, com posse do sub no teste de 2M. A operação de 8×8 pixels concluiu, e o padrão esperado bateu integralmente em 2M. O padrão divergiu no teste com o mapa, os vetores e a saída no banco lógico de 1M.
- O retorno a 1M restaurou a troca pelo protocolo em `$A12018`, confirmada por ACK, seleção de banco e marcador. DMNA só foi usado em 2M, se a posse ainda estava com o main.
- Emulador apenas. A divergência em 1M é sobre o layout do banco usado pelo protocolo. A sonda não distingue uma restrição física de modo de outros comportamentos possíveis com um layout intercalado. Os 2–3 ticks registrados cobrem o disparo, a espera e a verificação, sem medir a transição de modo nem um lote real.

Para o lote, cada linha tem um único passo constante. Se as distâncias exigirem números de amostras diferentes, guardar o comprimento válido por raio e ignorar os pixels após o seu fim, ou agrupar comprimentos. Medir o custo de ida e volta de modo e a varredura da saída à parte. Os 256 pares reais, a referência de visão exata no sub e a avaliação de falsos resultados continuam pendentes.


## 8. Replay de raios reais — resultado no BlastEm

Captura com hook no R128 All nativo, dados privados. Foram 341 chamadas monstro→jogador nos tics 200–300, com apenas um resultado visível nessa janela. A [captura ampliada](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42299359419) coletou 7.387 chamadas, das quais 27 visíveis. A ROM usa o resultado observado de `P_CheckSight`, incluindo os atalhos e o cache já existentes no jogo. O raster vem das paredes de um lado só do WAD original de E1M1, com duas células de espessura e 8 unidades de mapa por pixel.

| Replay | Consultas visíveis / bloqueadas | ASIC + setup + leitura (ticks) | Sub DDA (ticks) | Falsos bloqueados | Falsos livres | ASIC ≠ DDA |
|---|---:|---:|---:|---:|---:|---:|
| [Primeiras 256, tics 200–276](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42299229397) | 0 / 256 | 10.826 | 16.498 | 0 de 0 | 6 de 256 | 0 |
| [Amostra mista, tics 200–2479](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42299618875) | 27 / 229 | 3.261 | 19.620 | 7 de 27 | 6 de 229 | 0 |

A segunda ROM lê a saída empacotada em palavras. Os 3.261 ticks se dividem em 162 de preparo, 2.699 de operação gráfica e 400 de leitura. A comparação justa é dentro de cada linha da tabela. As amostras diferem entre as duas versões. O tempo reportado exclui carga de assets, troca de modo por lote e lógica completa de visão. O controle DDA lê o mesmo mapa de stamps e usa o mesmo passo quantizado, com saída antecipada ao encontrar uma célula ocupada.

**Decisão:** o ASIC acelerou a amostragem sobre o DDA, mas a rasterização de duas células reprovou como filtro que descarta visão. Sete decisões nativas visíveis seriam descartadas. A visão exata no sub ainda não foi portada ou cronometrada. Antes desse investimento, uma nova representação precisa demonstrar ausência de falsos bloqueios numa amostra com casos visíveis e teste de bordas. O plano separado de chão texturizado continua condicionado à ROM única estável e ao orçamento de desempenho.

ROMs privadas:
- `/home/dan/Projetos/Personal/scd-asic-rays/run-42299229397-1/doom-md-scd-asic-rays.bin`
- `/home/dan/Projetos/Personal/scd-asic-rays/run-42299618875-1/doom-md-scd-asic-rays-v2.bin`
