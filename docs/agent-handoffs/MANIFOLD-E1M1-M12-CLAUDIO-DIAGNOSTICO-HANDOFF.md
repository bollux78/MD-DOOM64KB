# Manifold E1M1 M12 — diagnóstico independente do Cláudio e handoff (11/11/2026)

Responde a `HANDOFF_CLAUDIO_MANIFOLD_M11_FLICKER_HUD_FPS_2026-11-10.md`.
Branch: `exp-manifold-m12-claudio`, derivada de `exp-manifold-m11-nearclip-hud` (`567810c`).
**Nada disto foi compilado no runner nem testado em BlastEm gráfico ou console.** Tudo abaixo foi medido em MAME local, salvo indicação. A release e as outras branches não foram tocadas.

## 1. Resumo

| Problema | Causa encontrada | Estado |
|---|---|---|
| A. Paredes piscam ao encostar | (1) *bob* de corrida continua com o jogador bloqueado; (2) *bob* de respiração parado; (3) parede dentro do near plane é descartada inteira | Corrigido em MAME, falta console |
| B. Paredes distantes piscam / triângulos externos | Trechos de coluna não desenhados mostram o conteúdo antigo do outro buffer | Renderer em ordem BSP implementado; validação parcial |
| C. Retângulos pretos no HUD | **Não reproduzido nem explicado** | Só um defeito de cor do HUD corrigido |
| D. FPS | Sem ponto quente único; custo por célula visitada (~80 mil ciclos) | Um gargalo corrigido (parede colada); resto é proposta |

## 2. Fluxo real de apresentação (lido no código compilado)

- `my_bmp.c`: os dois framebuffers em VRAM **se sobrepõem pela metade** (FB0 = tiles base+0..575, FB1 = base+320..895). `do_vint_flip` leva **dois VBlanks** por quadro, cada um com 2 DMAs de 4608 bytes (9216 bytes por VBlank), e troca o scroll vertical do BG_A no segundo.
- O H-Int liga o display na linha ~32 e desliga na ~215 (medido por escrita no registrador 1). O HUD termina na linha 207.
- Orçamento do DMA a partir da linha 224: H40 termina por volta da linha 7 do quadro seguinte, H32 por volta da 17. O display só liga na 32. Cabe nos dois modos, com margem de ~25 linhas em H40 e ~15 em H32. Isso é cálculo, não medição em hardware.
- O renderer **não limpa o framebuffer**. Qualquer trecho de coluna que um quadro deixe sem desenhar mostra o que estava naquele buffer dois quadros antes, e os dois buffers alternam. Esse é o mecanismo do "pisca".
- `SYS_doVBlankProcess()` nunca é chamado. No SGDK 2 isso significa que **a fila de DMA nunca é descarregada**: toda chamada com `DMA_QUEUE` (SAT e tiles da arma, console) é perdida quando a fila enche. É a causa provável da arma invisível. Não corrigi.

## 3. Evidências medidas (MAME, ROM H32 + HUD Doom, sem música)

1. **Empurrando uma parede** (Cima segurado, posição x/y constante): a imagem inteira muda a cada quadro renderizado. Log por quadro: `x=1056 y=-2898` fixos e `z` variando 1,5 unidade por quadro. É o *bob* de corrida, que avança com direção pressionada mesmo sem deslocamento, ampliado pela proximidade.
2. **Parado numa vista longa**: 51 quadros capturados, **15 imagens distintas**, até 11.112 de 34.560 pixels diferentes. É o *bob* de respiração (`bobs[idle_bob_idx] * 0.2`) somado às texturas com dither.
3. **Câmeras fixas do Werk** (z travado): 5 de 6 câmeras com imagem idêntica entre quadros. Logo o renderer é determinístico quando a câmera não se mexe.
4. **Colado na parede: 7,4 fps**, contra ~29 no corredor. Perfil: 74 % das instruções em `draw_bottom_clipped_texture_vertical_line`, no caminho em C para paredes com mais de 512 px de altura projetada.
5. **Vista do spawn: 4,0 fps**. Perfil ponderado por ciclos: `visit_graph` 19 %, `bsp_box_visible` 7,6 %, transformação de vértices 6 %, piso 4,4 %, teto 4,3 %, divisões 3,9 %. ~26 células por quadro.
6. **HUD em VRAM**: girando e atirando por 3600 quadros, os 132 tiles do HUD não mudaram. A corrida "VInt interrompe escrita de VDP da thread principal" existe no código (SGDK não mascara interrupções), mas não ocorreu no MAME.
7. BlastEm sob Xvfb neste ambiente não gera imagem; não consegui inspeção visual nele.

## 4. O que está implementado na branch (tudo opt-in)

| Flag | Passo em `stage_rom.py` | O que faz |
|---|---|---|
| `MANIFOLD_STABLE_VIEW=1` | `stable_view` | Remove o *bob* de respiração; o de corrida só avança se x/y mudaram |
| `MANIFOLD_RADIUS=1` | `player_radius_collision` + `blocking_segments` no emissor | Mantém o jogador a 16 unidades de paredes sólidas e degraus altos, para a parede nunca entrar no near plane (10) |
| `MANIFOLD_BSP=1` | `bsp_order_renderer` + `bsp_tables` no emissor | Visita cada célula no máximo uma vez por quadro, em ordem frente-para-trás pela BSP do Doom, com oclusão por coluna; o que sobrar aberto é preenchido com a cor de neblina. Desliga a fusão de células |
| `MANIFOLD_EXTRA=hole_diag` | `hole_diag` | Diagnóstico: zera o buffer antes de cada quadro e conta trechos não desenhados |
| (sempre) | `manifold_wall_column_c` | Preenchimento por faixas de texel para paredes > 512 px |
| (sempre) | `m10/gen_hud_manifold.py` | Cores raras da barra podem cair no índice 0 em vez de virar o azul da chave |

Resultados com `BSP=1 RADIUS=1 STABLE_VIEW=1` (MAME):
- Empurrando parede: 15 quadros → **1 imagem distinta**. Parado: 51 quadros → **1 imagem distinta**.
- Colado na parede: 7,4 → **11,4 fps**.
- Tour de 86 setores: média 7,06 → **6,80 fps** (pior), mínimo igual (2,67); nos pontos mais lentos houve ganho (2,67 → 4,0 e 4,67), mas 44 de 86 pontos ficaram mais lentos. Os pontos do tour não são idênticos entre as duas ROMs porque a fusão de células muda, então a comparação é aproximada.
- Spawn parado: 4,0 → 3,6 fps.

**Procedência:** `bsp_order_renderer`, `player_radius_collision` e `hole_diag` foram escritos numa etapa anterior desta sessão cujo registro eu perdi; recuperei o código do diretório de trabalho. Nesta etapa eu só re-medi o conjunto. Não tenho os números do `hole_diag` que motivaram o diagnóstico de B; quem continuar deve rodá-lo de novo antes de confiar nessa parte.

## 5. Mudanças não commitadas no workflow

`manifold-e1m1-rom.yml` (commitado junto, **ainda sem run no runner**): gatilho na branch nova e três variantes sobre a base musical — `m12stable-h32.bin`, `m12stable-h40.bin`, `m12stableaw-h32.bin` (autowalk com vetores de exceção fatais, 3600 quadros no BlastEm).

**Validação local (11/11, sem runner):** as três variantes compilam com o mesmo toolchain do workflow (fonte `b6fe52a`, `prepare_r25_music.py` antes do build, `xgmtool` do kit m68k-elf). O autowalk passou em BlastEm headless com 1500 e 3600 quadros, sem exceção, sem `unmapped`/`fatal` e com o debugger silencioso. Os boots de 90 quadros de H32 e H40 também passaram. Isso prova que não trava e não tem exceção; **não prova que o jogador anda sem prender nas passagens**, porque o autowalk aqui é só checado por falha. Visual não foi avaliado.

Dois detalhes para quem reproduzir: (a) o workflow precisa de `res/r25-e1m1.vgm`, gerado por `scripts/lab/prepare_r25_music.py` com `DOOM_R25_MUSIC=1`; esse script regrava `res/music.res` (versionado), então restaure com `git checkout` depois; (b) no ambiente local o `xgmtool` não estava em `sgdkr/bin` e foi preciso um link para `mars/m68k-elf/bin/xgmtool`.

## 6. Proposta do que falta

Em ordem:

1. **Compilar e validar a M12** (`[manifold-rom]` na branch): build das três variantes, autowalk 3601 no BlastEm. Se o autowalk falhar, primeiro suspeito é `MANIFOLD_RADIUS` prendendo o jogador em passagens estreitas.
2. **Teste no console**, duas ROMs, uma pergunta cada:
   - `m11music-h32.bin` (controle) contra `m12stable-h32.bin`: parado e empurrando parede, a imagem ainda treme? Se tremer com a M12, a causa é apresentação/VDP e não render.
   - `m12stable-h32.bin` contra `m12stable-h40.bin`: sobra diferença entre H32 e H40?
3. **Retângulos pretos (C)**: preciso de uma foto ou captura. Hipóteses a testar, nenhuma comprovada:
   - corrida VInt × escritas de VDP: guarda `vdp_busy` (o VInt adia o flip se a thread principal estiver escrevendo). Depois do DMA da fase 1 do FB1 o ponteiro do VDP fica exatamente no primeiro tile do HUD (912), com auto-incremento 4;
   - colunas 0, 1, 62 e 63 do framebuffer em H32 nunca são desenhadas e aparecem nas bordas;
   - teste discriminante do handoff do Werk: HUD com render 3D congelado.
4. **Arma**: chamar `DMA_flushQueue()` no VInt ou trocar os envios para `CPU`. Cuidado: 128 tiles são 4 KB e estouram a margem de DMA do H32.
5. **Desempenho**, na ordem do retorno esperado:
   - fundir folhas BSP sem quebrar a ordem (ou agrupar por setor com teste de ordem), porque o custo é por célula;
   - combinar com o cache de vértices do Werk (`MANIFOLD_VERT_CACHE`, +22 a +43 % nas câmeras pesadas dele);
   - `bsp_box_visible` usa multiplicações de 32 bits por nó;
   - medir com as 6 câmeras fixas do Werk, não com o tour.
6. **Jogabilidade** (portas, THINGS) só depois de 1 e 2, em branch separada.

## 7. Ferramentas locais

`experiments/DOOM_Manifold_E1M1/tools/lbuild.sh` e `snaps.sh` (caminhos da máquina do Cláudio). Scripts Lua de MAME usados: empurrar parede, parado, perfil por trace, log de registradores do VDP por linha. Não estão no repositório; recriar a partir desta descrição se necessário.
