# DOOM SCD — Benchmark 03C

O sub-CPU gera 512 tiles (16 KiB) por bloco e devolve a Word RAM em modo 2M.
O Mega Drive espera o ACK e a posse da memória, copia os dados para WRAM,
valida todas as palavras e envia os tiles ao VDP por DMA. O padrão visível
muda a cada bloco. Pressione **A** para rodar o mesmo gerador no 68000
principal e comparar os tempos.

```fish
cd ~/Projetos/DOOM_SCD_Bench03C
fish build.fish
```

Abra `build/doom-scd-bench03c.bin` no BlastEm com a mesma configuração do 03B.
A tela mostra o total de blocos validados e os tempos da última amostra
exibida, em ticks do stopwatch de 12 bits do Sega CD (aprox. 30,72 µs/tick).
No modo CD, **HANDOFF + COPY** estima a latência de ida e volta excluindo o
tempo do gerador, e soma a cópia para WRAM. A verificação e o DMA são
cronometrados à parte. Tempos de estágio assumem duração inferior ao
período de 125,8 ms do contador. Os números representam blocos de tiles
sintéticos. O teste é serial, com espera do resultado pelo processador
principal, e antecede o teste de buffers alternados em modo 1M.

[Mapa da Word RAM e registradores do Sega CD](https://www.megadrive.org/elbarto/megacd/Official%20Sega%20CD%20Manual/segacd_toc.html)
