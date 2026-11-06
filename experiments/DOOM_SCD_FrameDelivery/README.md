# Sega CD: entrega de um quadro pronto ao VDP

[Build e teste no BlastEm](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42306456370). ROM privada em `/home/dan/Projetos/Personal/scd-frame-delivery/run-42306456370-1/doom-md-scd-frame-delivery.bin`.

O capturador usa um quadro real de 3.344 bytes no spawn do E1M1. O sub carrega os dois bancos da Word RAM antes da medição. O controle usa o mesmo conteúdo na RAM do Mega Drive. A rotina transfere para VRAM, com a tela desativada, e verifica cada palavra após o cronômetro. No caminho Sega CD, há troca de banco por mensagem e compensação da primeira palavra na transferência DMA, como no 03D. São 32 repetições de cada modo.

| Layout | Origem | DMA + troca, ticks | Média, ms/quadro | Palavras erradas |
|---|---|---:|---:|---:|
| Contíguo, 3.344 bytes, 1 DMA | RAM MD | 1.234 | 1,185 | 0 |
| Contíguo, 3.344 bytes, 1 DMA | Word RAM | 1.284 | 1,233 | 0 |
| Duas áreas com pitch de plano, 3.192 bytes, 42 DMAs | RAM MD | 7.111 | 6,827 | 0 |
| Duas áreas com pitch de plano, 3.192 bytes, 42 DMAs | Word RAM | 7.762 | 7,452 | 0 |

Conversão pelo stopwatch nominal de 30,72 µs/tick. Com quadro contíguo, o acréscimo sobre a RAM local foi 0,048 ms por quadro. O intervalo de pedido de troca até ACK/banco/marcador consumiu em média cerca de 0,05 ms. Os totais das fases podem diferir ligeiramente do total combinado por quantização.

O bloco contíguo foi entregue a uma região de teste na VRAM. Exibi-lo com o layout atual ainda exige projetar o armazenamento de destino e preservar as áreas fora da cena. O ensaio por linha replica o pitch e a quantidade de palavras da apresentação R128 sem crop, mas chama SGDK e espera a conclusão em cada linha. Esse tempo não é uma medição do código de apresentação R128, que programa o VDP diretamente e opera durante VBlank.

Próximo gate: produzir o quadro de uma cena fixa no sub e entregá-lo em poucas DMAs a um layout que o VDP realmente exiba, comparando render + espera + apresentação no mesmo trecho. A medição acima exclui render, preparação de cena, espera por VBlank e validação por leitura. O console ainda precisa confirmar os tempos e o transporte.
