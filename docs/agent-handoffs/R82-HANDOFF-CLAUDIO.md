# R82 — Handoff do Cláudio para o GPT

**Branch:** `exp-claudio-r82-d8088-20261028` (derivada de `exp-chatgpt-r81-menu-save-cheats-20261028`, commit `7b2b566`)
**Nova base aprovada:** **R82 = R81 + P1F1** (ROMs `doom-md-r60-r82-p1f1-pf.bin` / `-pl.bin`)
**Artefato com as ROMs:** https://github.com/bollux78/MD-DOOM64KB/actions/runs/40685851767

## O que é o P1F1

Duas mudanças de código no renderer, ambas aplicadas pelo hook `scripts/lab/apply_r80_performance.py` (`R80_EXPERIMENTS="P1+F1"`) **depois** de `apply_r81.py`, numa cópia descartável:

- **P1:** em `R42_DrawPackedWall` e `R_DrawColumnFlat`, `R22_PixelByte(...)` é trocado por duas leituras de tabela em ROM (linha por y, coluna por x). Remove os dois `MULU.W` por coluna. Usa 240 B de ROM e 0 B de WRAM. Se os macros Pair-V estiverem desligados, cai no código original.
- **F1:** o laço de pares do flat (V_FAST) vira `move.b / lea 152 / dbra`, sem os `MULU.W #$98` que o GCC gerava para o ponteiro de fim. Escreve os mesmos bytes nos mesmos endereços.

## Resultados

| ROM | Benchmark do usuário (DEMO3 completo) | A/B BlastEm (mesmo job) | Framebuffer |
|---|---|---|---|
| R81 (`r81-menu`) | 7,27 FPS / 293,60 s | — | — |
| **R82 (`r82-p1f1`)** | **7,42 FPS / 287,45 s** | −2,40% e −3,30% de vblanks (dois jobs) | idêntico, 717/717 e 321/321 tics |

BSS igual ao da R81: PERF 57.844 (folga 76), PLAY 57.852 (folga 68). ROM com 2.883.584 B.

## Testado e descartado (não repetir)

| Experimento | Resultado |
|---|---|
| `-fno-ivopts` | −0,15% (ruído) |
| Flags do Doom8088 (`-fira-loop-pressure -fno-tree-pre -fgcse-sm -fgcse-las -fipa-pta`) | +0,59% (**mais lento**); o `-fgcse-*` é anulado pelo `-fno-gcse` do `makefile.gen` do SGDK |
| BSP recursivo (sem `DOOM_R20_BSP_ITERATIVE`) | sem ganho (7,27 FPS no benchmark); libera 192 B de BSS, mas usa mais pilha: pico 1.674 de 2.562 B no DEMO3, e ~2.010 B estimados nos mapas de BSP mais funda (20 níveis: E1M5/M7/M8) |
| Cache do `P_CheckSight` (Doom8088) | não implementado: não é estritamente equivalente e custaria ~9 B de BSS |

## Como reproduzir o R82

```sh
python3 scripts/lab/apply_r81.py
python3 scripts/lab/test_r80_pixofs.py --src src          # equivalência sobre o fonte pós-R81
R80_EXPERIMENTS="P1+F1" python3 scripts/lab/apply_r80_performance.py
R82_NAME=p1f1 python3 scripts/lab/apply_r82_d8088.py      # nome da versão: ROM, header e tela do benchmark
python3 scripts/lab/build_r71a12mul_hud.py
```

No runner: `.github/workflows/r82-claudio-ab.yml`, acionado por `.github/triggers/r82-claudio-ab.trigger`. Ele aceita push de `exp-claudio-*` e `exp-chatgpt-*` e compila a R81 (controle) mais os conjuntos de `AB_SETS`. Depois captura cada PERF uma vez (≤8.000 quadros) e compara o framebuffer por tic.

## Regras pedidas pelo usuário

- Toda ROM nova sai com o **nome da sua versão** no `.bin` e no título/header do benchmark. Não reaproveitar `r81-menu` em candidatos.
- Comparar vblanks **só dentro do mesmo job**. A mesma ROM da R81 deu ~5,5 vblanks/quadro num job e ~12 em outro, então números absolutos de jobs diferentes não são comparáveis. A palavra final é o benchmark do usuário.

## Próximos alvos sugeridos (com base no perfil)

1. O mesmo P1/F1 em `R_DrawColumnSprite`, que tem o mesmo padrão: 5× `MULU.W #$98`, ~3,6% no perfil.
2. O bloco de clipping e fração da parede (`R42_DrawPackedWall`, ~2% no perfil).
