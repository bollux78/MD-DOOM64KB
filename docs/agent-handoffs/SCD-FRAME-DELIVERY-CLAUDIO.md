# Sega CD: melhorias na entrega do quadro ao VDP (Cláudio para o Werk)

**Base:** `experiments/DOOM_SCD_FrameDelivery` (`5d05884`, run 42306456370). **Estado:** proposta, não executada.

## Leitura do resultado
- **Bloco contíguo:** 1 DMA de 3.344 B, da Word RAM, em **1,23 ms**. A Word RAM custou só +0,05 ms sobre a RAM do MD e a troca, ~0,05 ms. O transporte está resolvido.
- **Layout real de plano:** 42 DMAs de 38 palavras com pitch de 64 em **6,8–7,5 ms**, quase **6× mais**. O custo não está nos bytes, mas em programar e esperar 42 DMAs separadas (SGDK + `VDP_waitDMACompletion` por linha).

## Melhorias
### M1. O sub escreve o quadro **já no pitch do plano** → 1 DMA (principal)
- O MD não pode guardar um quadro de 64 colunas: são +2 KB de BSS. Na Word RAM isso é de graça.
- O sub monta cada linha com as 64 entradas de name table do plano, 128 B. As colunas 38–63 recebem os valores fixos de borda/fora da cena, gravados uma vez por banco na carga, porque as linhas inteiras serão sobrescritas.
- Entrega: **1 DMA** de 42 × 128 = 5.376 B (ou 2 DMAs, uma por área, se as "duas áreas" forem planos distintos).
- **Estimativa:** proporcional ao contíguo medido, ~2 ms em vez de ~7 ms.
- **Cabe no VBlank:** o NTSC em H40 dá ~7 KB de DMA por VBlank, e 5,4 KB cabe, sem desligar a tela.
- **Medir:** o mesmo teste, linha "plano inteiro, 1 DMA", Word RAM × RAM do MD (esta só para referência, porque não caberia na BSS real).

### M2. DMA no VBlank, sem desligar a tela, e em fila
- O MD só marca "quadro N pronto no banco X" e segue a lógica. O **handler de VBlank** faz a troca e a DMA única.
- O laço principal nunca espera pela apresentação.
- **Medir no VBlank real:**
  - tempo da DMA dentro do VBlank;
  - se transborda para a área ativa: contar linhas com o HV counter;
  - o tempo do MD que deixa de ficar bloqueado.

### M3. Double buffer de name table na VRAM (anti-tearing)
- Duas name tables do plano na VRAM. A DMA vai para a de trás e, no VBlank seguinte, troca-se a base do plano (registrador 2 ou 4, uma escrita).
- A entrega pode até começar no VBlank e terminar no seguinte sem rasgar a imagem. Também ajuda se M1 + HUD passarem do orçamento de um VBlank.
- **Custo:** VRAM para mais uma name table (8 KB em 64×64, ou menos se o plano for 64×32). Verificar se há espaço no mapa de VRAM da R128.

### M4. Referência que falta: o custo real da apresentação da R128
- O teste por linha usa SGDK e espera em cada linha. **Não é** o código da R128, que programa o VDP direto.
- **Medir** a apresentação real da R128 no mesmo quadro: VBlanks e ticks em `I_FinishUpdate`/R115. Só com esse número dá para dizer quanto M1 + M2 ganham de verdade sobre o nativo.
- **Se a R128 também faz ~42 DMAs**, o caminho Sega CD já ganha do nativo nesta etapa, porque o nativo não tem RAM para o layout de 1 DMA.

### M5. Remover a verificação do caminho cronometrado
A leitura de VRAM fica só na rodada de correção, como já é. Manter assim em todos os novos modos.

## Ordem e critérios
1. **M4** (só medição).
2. **M1 + M2** no mesmo teste isolado:
   - quadro real do spawn, no layout de plano;
   - 1 DMA no VBlank, tela ligada;
   - verificação da VRAM em rodada separada.
3. **Critério:**
   - DMA + troca ≤ 2,5 ms por quadro;
   - dentro do VBlank, sem rasgo;
   - 0 palavras erradas.
4. **Refuta se** a DMA de linhas inteiras não couber no VBlank com HUD/som. Nesse caso, M3, ou 2 DMAs por área.
5. Depois: **cena fixa renderizada pelo sub** entregue por M1 + M2, como no gate do README, comparando render + espera + apresentação com o nativo no mesmo trecho.

Mantém: troca 1M por `$A12018` (nunca DMNA), compensação da 1ª palavra no DMA da Word RAM, nome do arquivo no header e na tela, BlastEm ≤ 10.000 quadros por execução, console depois do BlastEm.
