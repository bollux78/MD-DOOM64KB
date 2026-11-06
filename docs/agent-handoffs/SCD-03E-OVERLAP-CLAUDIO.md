# SCD 03E: paralelismo Mega Drive × Sega CD (Cláudio para o Werk)

**Base:** `8db7fcf`, ROM de 3,13 FPS (run 42274512230). **Controle:** nativo, 4,60 FPS no spawn (313 VBlanks / 24 quadros).
**Estado:** proposta, **não executada**.
**Relatório:**
- `build: PASS/FAIL`;
- `blastem: PASS/FAIL`, com quadros, VBlanks e FPS;
- console fica para depois.

## 1. Por que hoje é serial (lido no código)
- `install.py` faz `R_DrawColumnSprite` e `R_DrawColumnFlat` chamarem `SCD_Flush()` **antes** de desenhar.
- Pisos e tetos (flats sólidos) se intercalam com as paredes durante o BSP. Por isso cada troca parede→flat gera um lote completo:
  1. sobe o framebuffer (3.344 B);
  2. espera o sub desenhar;
  3. desce os 3.344 B.
- Daí os 18 lotes na janela, com ~5 ms de cópia + ~11,5 ms de espera cada. Nesse tempo o principal não faz nada.
- **O ponto central:** parede e flat da mesma coluna ocupam **linhas disjuntas** (teto acima da abertura, piso abaixo). A ordem entre eles não importa para o resultado. Só importa **não apagar o nibble vizinho** no byte que guarda dois pixels verticais.
- Os sprites, sim, precisam vir depois de todo o cenário.

## 2. Proposta: "SPLIT-ALT", a divisão do Daniel com lotes alternados
| Trabalho | Quem |
|---|---|
| BSP, visibilidade, portas (lógica) | Mega Drive |
| **Paredes texturizadas** (colunas R60) | **Sega CD** |
| **Pisos/tetos** (`R_DrawColumnFlat` / `R95_Fill`) | Mega Drive, nativo, **na hora**, sem flush |
| Sprites, psprites, HUD | Mega Drive, nativo, depois da última composição |

**Fluxo de um quadro, com os dois bancos 1M alternando (X com o principal, Y com o sub):**
1. O principal percorre o BSP. Cada coluna de parede vai para o pacote no banco X: offset, phase, step, rows, odd, LUT e texels, como hoje. Cada flat é desenhado na hora em `r115_draw`.
2. Quando o lote enche (256 colunas ou 64 LUTs), o principal **troca** (`$A12018` = id, nunca DMNA):
   - o sub recebe X e desenha as paredes **no `frame[]` do próprio banco**;
   - o principal recebe Y, que traz o lote anterior já desenhado;
   - **compõe** Y (seção 3) e continua o BSP empacotando em Y.
3. No fim do BSP, a última troca, a espera, a composição desse lote e depois os sprites nativos.

**Pontos importantes:**
- **Sem upload do framebuffer**, porque o sub só escreve os pixels das próprias colunas. O conteúdo do resto de `frame[]` não importa.
- **Sem quadro de atraso:** o quadro apresentado é o mesmo do estado de jogo, então mundo e sprites ficam coerentes.
- **Única espera bloqueante:** na troca, se o sub ainda não terminou o lote anterior, e no fim do BSP.
- **O que sobrepõe:** BSP + flats do principal com as paredes do sub, lote a lote.

## 3. Composição sem apagar nibble
A lista de colunas do lote já está no banco devolvido. O principal percorre essa lista, sem BSS nova:
- **pares internos** (os dois pixels do byte são da parede): cópia do byte inteiro de `frame[]` para `r115_draw`, com passo de 152;
- **bordas** (primeira linha se `odd`, última se a contagem for ímpar): mescla de nibble, como em `verify_batch`.

O `verify_batch` atual já é a referência exata. O teste de pixels continua comparando o lote composto com a referência independente.

**Custo:** ~1 `move.b` por 2 pixels, bem menos que desenhar. Precisa ser **medido** (seção 5).

## 4. Variante que pode decidir o jogo: rotear por custo
- Empacotar uma parede custa **copiar os texels amostrados**, ~`rows·step/512` bytes, até 128.
- Paredes distantes têm poucos pixels e muitos texels. Para elas, empacotar custa mais que desenhar no próprio Mega Drive.

**Variante `SPLIT-ALT-ROUTE`:**
- coluna com `texel_bytes > rows` (ou outro limiar medido) → desenha nativo na hora (pixels disjuntos, sem flush);
- senão → vai para o sub.

Medir os dois limiares: `rows` e `rows/2`.

## 5. Medidas obrigatórias (sem BSS nova)
- Reaproveitar os contadores existentes:

  | Contador | Passa a medir |
  |---|---|
  | `scd_copy_ticks` | composição |
  | `scd_wait_ticks` | **espera bloqueante real**, só o tempo parado no laço |
  | `scd_sub_ticks` | desenho do sub |
  | `scd_textured_columns` | colunas enviadas |

- **Empacotamento** (`SCD_Column` + `copy_bytes` dos texels/LUTs): falta um acumulador de 4 bytes. Cabe nos 8 bytes de folga. Se não couber, colocar no cabeçalho do pacote (campo `reserved`) e somar na troca.
- **Por quadro:** VBlanks totais, número de trocas, colunas para o sub e colunas roteadas para nativo.
- **Controle nativo, na mesma janela:** o mesmo esquema de PC sampling do `r117_profile.py` separa BSP, paredes, flats, sprites, lógica e apresentação.

  **Isso vem primeiro.** Se as paredes texturizadas forem, por exemplo, 15% do quadro nativo, o teto teórico do SPLIT-ALT é ~+18% (≈5,4 FPS no spawn). É preciso saber antes de estimar mais.

## 6. Menor experimento (ordem)
1. **Perfil nativo**, só medição: repartir o quadro de spawn e um trajeto curto e determinístico (demo 1, tics 200–260, o mesmo do 03D).
2. **SPLIT-ALT** (`install.py`):
   - tirar o `SCD_Flush()` de `R_DrawColumnFlat`, cujos flats seguem nativos;
   - manter o flush antes do **primeiro** sprite de cada quadro;
   - `SCD_Flush` vira "trocar sem upload e compor o lote devolvido";
   - o sub (`sub_render.c`) não muda, porque já desenha só colunas.
3. **SPLIT-ALT-ROUTE**, com os dois limiares.
4. Os três medidos contra o nativo e contra a ROM de 3,13 FPS: spawn com 24 quadros, mais o trajeto.

## 7. O que refuta a proposta
- **`scd_wait_ticks`** ≈ `scd_sub_ticks`: não houve sobreposição e o desenho do sub continua no caminho crítico.
- **Empacotamento + composição** ≥ o tempo nativo das mesmas paredes: o offload não paga, mesmo com sobreposição. Nesse caso o próximo passo é **texturas/LUTs residentes no sub** (seção 8), não mais sobreposição.
- **VBlanks totais** não abaixo de 313/24 no spawn: não supera o nativo. Volta-se ao nativo, ou ao 03E completo, com BSP no sub.

## 8. Comparações pedidas e próximos passos condicionais
- **LUT residente:** se os LUTs vierem de uma tabela contígua (R59/R56), copiar a tabela inteira para a PRG-RAM na carga do mapa (via bus request, como o boot). O pacote leva só o índice (`(ptr−base)/256`), e as cópias de 256 B somem.
  - Conferir os ponteiros no ELF;
  - medir quantas LUTs novas por lote há hoje.
- **Texturas residentes:** é o caminho do 03E completo. Só depois de o empacotamento aparecer como gargalo medido.
- **Sprites no sub:** só se o passe de sprites passar a dominar depois do SPLIT-ALT. Isso exige recorte (`clipbot/cliptop` por coluna) e lidar com o fuzz/`MF_SHADOW`, que lê o framebuffer. Neste caso, um fuzz força o caminho nativo naquele quadro.
- **Quadro anterior** (pipeline com 1 quadro de atraso, tudo no pacote): maior sobreposição possível, que inclui a lógica do tic seguinte, mas com atraso visível. Fica como alternativa se SPLIT-ALT + rota não alcançar o nativo.

## 9. Validação
- Pixels: composição de cada lote contra `verify_batch`, com o framebuffer completo igual ao nativo no mesmo estado de jogo:
  - no spawn;
  - durante a abertura de uma porta;
  - com um inimigo ou item parcialmente encoberto.
- E1M1 com e sem expansão.
- 0 stale, 0 timeout.
- Fallback para nativo após falha.
- ROM única.
- BSS ≤ 57.920.
- BlastEm: no máximo 10.000 quadros por execução.
