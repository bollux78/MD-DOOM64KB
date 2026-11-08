# M1.5: tirar a espera e a cópia do quadro MD (Cláudio para o Werk)

**Branch:** `exp-werk-scd-subport-s1s2`. **Base:** M01 aprovado no BlastEm (run 42495733287, `[m01-iterate]`), com a ROM `doom-md-scd-m01.bin`:
- modo de uso a 34,99 Hz, 0 tics descartados, apresentação de 3,56 FPS;
- teto de recuperação de 8 tics e leitura do relógio dentro do `publish` (commit `a19e004`, Cláudio).

**Meta:** **apresentação > 4,6 FPS** (nativo) no mesmo roteiro, mantendo 35 Hz ± 2%, 0 descartes e todas as auditorias. Desvios de comportamento são aceitáveis (critério do usuário).

## Onde está o tempo (M01, modo de uso)
- Quadro de ~281 ms. Raster MD de ~191 ms (M0: 6.221 unidades × 30,72 µs). Conversão = 0 com Shadow Off. DMA pequeno.
- **Sobram ~90 ms,** em dois blocos:
  1. **Espera síncrona do MD pela captura no sub.** O sub só captura (`S2B_Capture/Finish`, `S2C_Capture/Finish`) **depois** de ver a demanda em `$A12012`. O maior intervalo entre leituras do relógio no sub, dentro do `publish`, foi de 57 ms. Durante esse tempo o MD espera.
  2. **Aplicação no MD** (`S2B_ApplyFrame` + `S2C_ApplyFrame`): ~3,64 VBlanks ≈ 60 ms na S2e.

## Mudanças
### A. Snapshot pronto antes da demanda (o sub nunca captura sob demanda)
- **Depois de cada tic** (ou a cada 2 tics, se o custo pesar), o sub captura o estado **num dos dois bancos lógicos que ele controla:**
  - ele possui um banco 1M de cada vez; capturar no próprio banco é seguro, porque o MD não toca nele;
  - a captura vai para a área do pacote do banco do sub.
- **Na demanda do MD,** o sub só fecha o cabeçalho (sequência, gametic, CRC/eco já calculados) e faz a troca. A captura já está pronta, então a resposta leva microssegundos, não ~57 ms.
- **Deltas:** continuam "desde a última entrega". As marcas de sujo acumulam desde a última **entrega**, não desde a última captura:
  - **recaptura** a cada tic sobrescreve o snapshot inteiro do banco;
  - os deltas do mundo são recalculados contra a cópia "última entregue" que o sub já mantém.
- **Medir:**
  - tempo do MD entre escrever a demanda e ter o banco (alvo < 1 ms);
  - custo da captura por tic no sub;
  - folga do sub (média do tic + captura ≤ ~22 ms, abaixo dos 28,6 ms).
- **Se a captura por tic não couber:** capturar a cada 2 tics (o estado entregue fica até 1 tic mais velho, aceitável).

### B. Aplicação mais barata no MD
- **Atores:**
  - mandar só os **visíveis/relevantes** para o render MD: dentro de 1.280 unidades (o mesmo corte do R128 `far`) e com sprite válido;
  - **campos compactos** (x, y, z em 16.16 → manter; ângulo 8 bits; sprite/frame 16 bits; flags 8 bits; setor 16 bits);
  - o MD **reconstrói só as listas de setor dos atores que mudaram de setor.**
- **Mundo:** só os setores/sides marcados (já é delta). Conferir se o MD não percorre todos os setores para aplicar; ele deve percorrer só a lista.
- **Medir:** VBlanks de `S2B_ApplyFrame` e `S2C_ApplyFrame` separados, antes/depois. **Alvo:** ≤ 0,6 VBlank (10 ms) somados.

### C. O que não fazer agora
Não tocar no render MD (raster e conversão continuam R128). Isso é o M2/M3 do Cláudio.

## Testes (mesmos de `m01/test_realtime.py` + estes)
- **Apresentação no mesmo roteiro do modo de uso:** FPS > 4,6.
- 35 Hz ± 2%, `dropped` = 0, `max_poll` < 100 ms.
- Novos campos no relatório:
  - tempo de demanda→banco no MD;
  - custo de captura/tic no sub;
  - `apply_world`/`apply_actors` em VBlanks.
- **Auditorias:**
  - checksum dos pacotes;
  - reconstrução de deltas;
  - atores/listas;
  - eco de input;
  - alternância de bancos;
  - G_Ticker ausente no MD;
  - retorno normal.
- **Roteiro:** porta, item, tiro, inimigo parcialmente encoberto.
- **ROM para o console:** tela de diagnóstico + START → jogo (sempre jogável).
- **Relatório:** `build: PASS/FAIL` e `blastem: PASS/FAIL` separados. **Não declarar aprovada sem os dois.**

## Gatilho
Mesmo fluxo isolado: commits com `[m01-iterate]` disparam `scd-subport-m01-iterate.yml`. Usar `[m15-iterate]` num workflow copiado, se preferir não misturar.
