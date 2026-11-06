# SCD 03D — pré-teste de transporte

Gate isolado para alternar bancos de Word RAM em modo 1M. O sub-CPU gera 16 KiB de dados sintéticos. O Mega Drive verifica o ID, despacha o quadro seguinte antes do DMA e compara todas as palavras lidas da VRAM. A leitura da VRAM faz parte do teste de correção. O benchmark do renderer da R128 é uma etapa separada.

Compilar com `fish build.fish`. A ROM sai em `build/doom-scd-03d-transport.bin`. O resultado esperado é `TRANSPORT PASS / 16 VERIFIED` com zero `STALE` e `TIMEOUTS`.

[Manual de hardware](https://www.megadrive.org/elbarto/megacd/Official%20Sega%20CD%20Manual/segacd_toc.html)
