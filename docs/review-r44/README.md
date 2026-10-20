# Corrigir texto da intermissão — R44 / R40ci

**Diagnóstico reproduzido a partir da captura do usuário:** durante a intermissão E1M1 em `WIMAP0`, só aparecem partes de `E1M1: HANGAR`, `FINISHED`, `Kills`, `Items`, `Secret`. O texto fica no lado direito e os tempos desaparecem, embora a imagem Bayer8 em 320×224 esteja correta.

**Causa confirmada em `src/wi_libt.c`:** a mesma rotina de layout textual usa `VIEWWINDOWWIDTH=76`, `VIEWWINDOWHEIGHT=44` nas ROMs pixel4 (amostras da geometria 3D). Mas a camada WINDOW e a fonte usam **38 colunas e 22 linhas** de caracteres 8×8. Como o compositor ignora/recorta posições fora desses limites, títulos ficam truncados, números das porcentagens desaparecem e temporizadores são enviados a y=41/42, fora da tela.

## Correção pequena e segura

O código agora define, somente quando `DOOM_R22_PIXEL4`:

```c
#define WI_TEXT_WIDTH 38
#define WI_TEXT_HEIGHT 22
```

Nos outros renderizadores permanecem `VIEWWINDOWWIDTH` e `VIEWWINDOWHEIGHT` originais. **Só `src/wi_libt.c` foi alterado para usar dimensões textuais** em `WI_drawLF`, `WI_drawEL`, `WI_drawStats` e coordenadas da animação do mapa `lnodes`. `src/r22_video.inc`, `src/r35_native4.inc`, kernels 4×4 e dither/cores NÃO foram alterados.

Resultado esperado: nome do mapa e FINISHED centralizados, Kills/Items/Secret com porcentagens, Time/Total/Par visíveis dentro da área, e marcadores de próximo mapa na posição correta, com limpeza sem flicker da R40b. O layout do jogo 3D continua **76×44 amostras nativas**, sem impacto esperado em FPS.

## Variantes e testes

- **Branch:** `r44-pixel4-intermission-fix`, derivada de ASM R42.
- Teste estático `scripts/lab/test_r44_intermission_layout.py` cobre layout, limites, tempos, mapas e preservação do 8×8.
- Duas ROMs: **play** para terminar E1M1 e comparar a captura da intermissão; **perf** para garantir regressão zero na DEMO3.
- A CI valida scripts, ROM linear ≤4 MiB, flags, cabeçalho e boot de 300 quadros. **O boot não atravessa a E1M1 até a intermissão; a confirmação visual do usuário é indispensável.**
- Os checkpoints de desempenho são aproximadamente **3,01 FPS / 709,67 s** para a R40ci e **3,88 FPS / 550,32 s** para a R44 ASM. São referências anteriores, não medidas nestas ROMs.

**Importante:** não confundir com o bug anterior da R40 original, que acumulava textos no menu por limpeza incorreta. A R40b já resolveu aquele problema; este é um defeito de *coordenadas de layout* independente.
