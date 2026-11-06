# SCD 03E: renderer completo da R128 no 68000 do Sega CD (Cláudio para o Werk)

**Branch:** `exp-chatgpt-scd-bench03b`. **Base do jogo:** R128 All (não muda).
**Estado:** projeto, **não executado**.
**Relatório de cada marco:** `build: PASS/FAIL`, `blastem: PASS/FAIL`, `console: PASS/FAIL` (este último o usuário preenche).

## 0. Ponto de partida (03D aprovado no console, 2026-11-06)
| Medida, 64 quadros | Console | BlastEm |
|---|---|---|
| Colunas da R128, principal | 60.856 ticks (~29 ms/quadro) | 60.442 |
| As mesmas colunas, sub | 36.548 ticks (~17,5 ms/quadro, 1,67×) | 36.670 |
| Espera de troca 1M | 129 ticks (~0,06 ms/quadro) | 127 |
| DMA para a VRAM | 13.707 ticks (~6,6 ms/quadro) | 15.413 |
| Quadros velhos / timeouts | 0 / 0 | 0 / 0 |

- O BlastEm previu o console com cerca de 1% de diferença no desenho.
- A troca é desprezível.
- **Regra herdada:** a troca 1M é pedida pela palavra de comunicação `$A12018` e nunca por DMNA. No console, DMNA lê 1 logo depois da troca 2M→1M.

## 1. Arquitetura
| Mega Drive principal | 68000 do Sega CD |
|---|---|
| lógica (`P_Ticker`), entrada, som/Z80, menus/HUD | `R_RenderPlayerView` da R128 (BSP, segs, visplanes, sprites, psprites) |
| monta o **pacote de quadro** no banco 1M dele | lê o pacote no banco que recebeu |
| DMA do framebuffer pronto para a VRAM, como a R128 já faz | escreve o framebuffer pixel4 no mesmo banco |

**Pipeline:** o principal roda a lógica do tic N enquanto o sub desenha o N−1. Isso dá **um quadro de atraso visual**, aceitável.

O sub-CPU **não lê a ROM do cartucho**. Tudo o que o renderer usa precisa estar na Program RAM (512 KiB) ou chegar pelo pacote.

## 2. Dados por fase (carga do mapa)
1. **Packer** novo, `tools/pack_level.py`. Recebe o WAD convertido da R128 (o mesmo da build) e o mapa. Gera um blob com:
   - geometria de render: vértices, segs, sidedefs, linedefs, setores, nodes, subsetores;
   - só as texturas/patches, flats e sprites usados no mapa e no episódio;
   - colormaps e as LUTs pixel4 (`r22_color`, R56/R59) com os mesmos valores da build R128.

   **Orçamento:** o packer falha se o blob passar de 448 KiB. A primeira medida é um relatório por mapa do E1.
2. **Carga:** o principal copia da ROM para a Program RAM com o sub-CPU em bus request, pela janela de 128 KiB em `$420000`. O banco vai nos bits BK de `$A12003`, o mesmo caminho do `boot_sub`, que já funcionou no console. Depois disso, verificação por CRC no próprio sub.
3. **Sem SRAM no sub:** os acessos R23/R24/R25 (estado de mapa na SRAM e proxies da ROM) viram estruturas diretas na Program RAM. Esse era o maior custo dos picos na R121.

## 3. Pacote de quadro
Fica no início do banco 1M do principal, que vai para o sub na troca.
- **Cabeçalho:** ID do quadro, gametic, CRC do pacote.
- **Câmera:** viewx/y/z, viewangle, extralight, fixedcolormap e o estado das psprites (estado/frame e luz).
- **Deltas de setor** desde o pacote anterior: floor, ceiling, light, floorpic, ceilingpic (portas, elevadores, luzes piscando).
- **Deltas de lado/linha:** troca de textura (interruptores) e flags de linha que o renderer usa.
- **Things:** todos os mobjs do mapa (x, y, z, ângulo, sprite, frame, flags como `MF_SHADOW`, setor). O E1 tem algumas centenas de mobjs; a 16 bytes cada são menos de 8 KiB.
- O sub aplica os deltas na cópia dele e desenha.
- **Ressincronização:** se `stale`/timeout, o principal manda um pacote completo com todos os setores.

## 4. Código
- Compilar as fontes de render da R128 **duas vezes**:
  - **principal:** a build normal, para o controle;
  - **sub:** com `-DSCD_SUB`, no lugar de `scd_replay`.
- Com `SCD_SUB`:
  - `R23/R24/R25` → acesso direto à RAM;
  - `I_Error` → código em `$FF802A` + fault;
  - sem SGDK, Z80 ou VDP;
  - o kernel de colunas é o mesmo do 03D.
- **Lado principal:** `R_RenderPlayerView` vira `SCD_SubmitFrame()` + `SCD_Present()`. Uma opção de build `DOOM_SCD_RENDER` mantém a R128 normal como fallback, por exemplo se não houver Sega CD.
- **Escrita no banco:** o principal só escreve pacote e lê framebuffer no banco que possui. Nada é escrito fora do protocolo 1M.

## 5. Marcos e testes
**E1, quadro estático:**
- E1M1 carregado no sub;
- 8 câmeras capturadas da R128, nos mesmos tics 200–260 do 03D;
- **framebuffer idêntico byte a byte** ao da R128 em cada um. Diferenças explicadas por escrito ou FAIL.

**E2, demo:**
- demo 1 com a lógica no principal e o render no sub;
- fingerprints de lógica (`r118_logic_check.py`) idênticos aos da R128;
- framebuffer igual ao da R128 do tic anterior em 10 checkpoints (o atraso é de 1 quadro);
- 0 stale, 0 timeout.

**E3, desempenho:**
- Run All das demos;
- FPS médio/mínimo e tempo total contra a R128 All;
- tempo livre do principal e espera por quadro.

Esperado: o render sai do caminho crítico. O limite passa a ser `max(lógica, render no sub)` e não a soma. Ganho grande nos mapas pesados de render (E1M1, escadas).

**Console:** E1, E2 e E3 nessa ordem, só depois de `blastem: PASS`.

## 6. Critérios de parada
- **Blob de algum mapa do E1 > 448 KiB:** antes de seguir, decidir entre carregar texturas por setor visível e reduzir sprites.
- **E1 sem framebuffer idêntico:** não seguir para o E2.
- **E3:** se o FPS médio não subir pelo menos 30% contra a R128 All no BlastEm, revisar o que domina no principal antes de ir ao console.

## 7. Restrições
- ROM, WAD, blobs e capturas só em `/home/dan/Projetos/Personal/`.
- Nada de CD-DA nem leitura de disco nesta fase.
- BlastEm: no máximo 10.000 quadros por execução, com a configuração fixa.

## 8. Objetivo final: uma ROM só, com detecção (pedido do usuário, 2026-11-06)
A mesma ROM usa o Sega CD se ele estiver acoplado. Sem ele, roda como a R128 pura.

**Detecção na partida, antes de qualquer acesso a `$A12xxx`:**
1. `$A10001` bit 5 = 0 (dispositivo de expansão presente) **e** `"SEGA"` em `$400100` (cabeçalho do BIOS).
2. `boot_sub()` completo, com assinatura do sub e o modo 1M confirmado (MODE/RET, nunca DMNA), tudo dentro do prazo.
3. Qualquer falha nos passos 1–2 → **modo Mega Drive (R128), sem `I_Error`**. A tela de título mostra `SEGA CD: ON/OFF`.
4. Em jogo, se houver timeout persistente do sub (por exemplo 3 seguidos), cai para o render do Mega Drive na carga do próximo mapa.

**ROM sem duplicar o WAD:**
- O "packer" do §2 roda **no próprio principal, na carga do mapa**. Ele lê o WAD que já está na ROM e monta o blob direto na Program RAM.
- Na ROM entra só o código do sub, de algumas dezenas de KiB.
- Um script host (`pack_level.py`) gera a mesma saída e serve para conferir o CRC e o orçamento de 448 KiB.

**RAM do principal:**
- BSS ≤ 57.920 continua valendo nos dois modos.
- O código SCD do principal não pode acrescentar BSS relevante: estado do protocolo em poucos bytes, pacote montado direto no banco 1M.
- No modo Sega CD, as estruturas de render do principal ficam simplesmente sem uso.

**Testes obrigatórios da ROM única:**
| Ambiente | Exigência |
|---|---|
| BlastEm **sem** Sega CD | lógica idêntica à R128 All nas 10 demos e FPS dentro de ±2% da R128 (o modo Mega Drive não pode piorar) |
| BlastEm **com** Sega CD | marcos E1–E3 |
| Console sem Sega CD | Run All igual à R128 |
| Console com Sega CD | Run All com `SEGA CD: ON` |
| Flashcart + Sega CD | o mesmo, porque o Mode 1 por flashcart é o caso real do usuário |
