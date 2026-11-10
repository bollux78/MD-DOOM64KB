# M10: resultado. HUD clássico do Doom (HUD-WAD da R128) na Manifold

Responde a `MANIFOLD-E1M1-M10-HUD-CLAUDIO.md`. Branch `exp-manifold-e1m1-m01`.
A release fixa **não** foi alterada: a publicação continua atrás de `vars.MANIFOLD_RELEASE_APPROVED`.

## O que foi feito
- O HUD-WAD da R128 foi reaproveitado. `scripts/lab/gen_hud_wad.py` e `src/hud_wad_logic.h` **não foram modificados**; a R128 e o Sega CD também não.
- `experiments/DOOM_Manifold_E1M1/m10/gen_hud_manifold.py` é um wrapper. Ele roda o gerador da R128 sem alterações e faz dois ajustes, só para a Manifold:
  1. **Caixas dos números grandes** (AMMO, HEALTH %, ARMOR %): a pedra sob os dígitos passa a ser um único tile por linha, o mesmo usado pela tabela de munição. Assim, cada dígito e cada posição compartilham um só tile. Os tiles estáticos caem de **389 para 132**, sem perder nenhum widget.
  2. **Uma única linha de CRAM (PAL2)**: a Manifold já usa PAL0 para a arma, PAL1 para a vista 3D e PAL3 para sprites de objetos e texto. As faces passam a usar a paleta da barra. Os 4–5 slots menos usados da barra, escolhidos por pixels × erro de substituição (as cores das chaves e dos dígitos ficam protegidas), dão lugar a tons de pele.
- `m10/doom_statusbar.c`: `doom_hud_init` e `doom_hud_update` usam `HUDW_ComposeRow`, `HUDW_Hash` e `HUDW_Face*`.
  - O tilemap da barra só é reescrito quando o hash muda.
  - A face (16 tiles, 512 B) só é enviada por DMA quando o quadro muda.
- `stage_rom.py`, passo `install_doom_hud`, ativado com `MANIFOLD_HUD=doom`:
  - gera o header no runner a partir do WAD (o header não é versionado);
  - copia a lógica e o `.c`;
  - em `inventory.c`, troca **apenas a renderização**: `inventory_init` chama `doom_hud_init`, e `inventory_draw` chama `doom_hud_update`. A lógica de inventário e chaves (`inventory_add_item`/`has_item`, usada por `level.c` e `object.c`) continua igual.

## Estado mostrado (sem fingir jogo inexistente)
A Manifold não tem vida, armadura, munição nem armas do Doom.
- **Valores fixos, TEMPORÁRIOS**, iguais ao início do Doom: HEALTH 100 %, ARMOR 0 %, AMMO 50; tabela 50/200, 0/50, 0/300, 0/50; ARMS só a pistola.
- **Chaves reais**, vindas do inventário da Manifold: azul = BLUE_KEY, amarela = GREEN_KEY, vermelha = RED_KEY.
- **Face**: `HUDW_FaceTick` com vida 100 (olha para os lados de forma ociosa). Segurar A ativa a "rage face", como no Doom.

## VRAM / CRAM / nametable (medido em runtime no MAME)
| | M08 (controle) | M10 (HUD do Doom) |
|---|---|---|
| tiles do HUD | inventário 912–1014 (103) | barra 912–1043 (132) + slot da face 1044–1059 (16) |
| `free_tile_loc` final (limite 0x500 = 1280) | 1165 | 1210 |
| buffers da arma | 128 na área normal + 128 no WINDOW (0xB000) | iguais, intocados |
| céu | linhas 30–63 do BG_B (131 tiles) | igual, intocado |
| fonte SGDK | 0x4E0–0x53F | igual, intocada (o fps continua visível) |
| CRAM | PAL2 = HUD da Manifold | PAL2 = barra + faces; PAL0, PAL1 e PAL3 sem alteração |
| linhas do BG_B escritas | 21–26 (imagem HUD2) | 22–25 (barra, colunas 4–35, margens de pedra nas colunas 0–3 e 36–39); 26–27 limpas; nada em 28 ou acima |

O assert existente (`VRAM tiles > LIMIT` → `SYS_die`) continua cobrindo a alocação. `doom_hud_vram_first` e `doom_hud_vram_count` ficam exportados para relatório.

## Desempenho
Tour de 86 setores no MAME, mesmo commit, controle versus HUD do Doom:

| | média | mínimo |
|---|---|---|
| Controle | 6,86 fps | 2,67 |
| HUD do Doom | 6,76 fps | 2,0 |

As diferenças por ponto ficam entre −5 e +5 renders a cada 1,5 s, centradas em 0 (36 pontos iguais). Isso está dentro do ruído de amostragem. A diferença média é de cerca de −1,5 %.

## ROMs (artefato `manifold-e1m1-roms-<run>`, mesmo commit)
- `m10-hud-control.bin`: M08 intacta (cópia da candidata).
- `m10-hud-doom.bin`: HUD do Doom.
- A ROM autowalk agora é compilada com `MANIFOLD_HUD=doom` e serve de teste de estresse do código novo (3600 quadros, exceções fatais).
- O passo do MAME captura `m10control_*` e `m10doom_*` com o mesmo script de controle.

## Pendências / riscos
- Na barra, o "4" do ARMS fica parcialmente coberto pelo quadrado da face. Isso já vem do layout 0,8× do gerador da R128.
- Os efeitos de sombra e realce da face (R79) não foram portados; não eram requisito.
- Vida, munição e armadura reais dependem de um sistema de jogador que a Manifold ainda não tem.
- A arma continua invisível (pendência independente).
- Aguardando: aprovação do usuário no BlastEm gráfico antes de liberar `MANIFOLD_RELEASE_APPROVED`; depois, teste no console real.

## Integração com o plano M11/M12 do Werk (`fac313c`)
- **Correção de nomenclatura:** a M10 é H40. O H32 é uma variante de teste separada (`MANIFOLD_H32=1`, ROM `m11-hud-doom-h32.bin`, commit `c7c3ed3`). Apesar do nome do arquivo, ela **não** faz parte da M11 do Werk e deve ser tratada como "variante H32".
- **Interruptores independentes**, todos variáveis de ambiente do `stage_rom.py` e desligados por padrão:
  - `MANIFOLD_HUD=doom`: só a renderização do HUD em `inventory.c`, mais `doom_statusbar.c`;
  - `MANIFOLD_H32=1`: `config.h`, a largura da tela em `game.c`, a janela inicial do `visit_graph` (2..62), o lote de DMA em `my_bmp.c` e as bordas do céu.

  As mudanças de render, PVS e LOD da M11/M12 podem ser compiladas com o HUD ligado ou desligado e com H40 ou H32 sem conflito. Os pontos de contato são o workflow (lista de variantes) e a ordem dos passos no `stage_rom.py`.
- **Dados já medidos que servem à M11B:**
  - Trace do MAME (68000) num ponto lento do tour: `visit_graph` ~37 %, transformação de vértices ~9 %, recorte ~6 %. Travessia e geometria dominam, não o preenchimento.
  - Há de 40 a 65 visitas de célula por quadro nas cenas lentas, com revisitas permitidas por `sector_rendered_cache` (até 7).
  - Isso favorece PVS, cache de vértices por quadro e agrupamento de render, e não troca de textura por cor; o resultado bate com a M09 revertida.
- **`bunch_render.c` não entra na ROM:** `first_wall_is_behind_second` e `draw_bunches` não aparecem no `symbol.txt` (o `--gc-sections` os remove), e `portal_rend` só chama `visit_graph`. O possível erro `w1y2` não afeta a E1M1 atual.
- **Fog:** está em 1600 unidades, com a cor mais escura da paleta (desde a M06). Os blocos azuis grandes das capturas antigas eram paredes de fog pintadas com a cor do piso, antes da M06. O teste F1 do Werk (desligar o fog em E0) é o certo para confirmar se ainda sobra algo.
- **VRAM para LOD/PVS:** as tabelas devem ficar em ROM. Em H40 sobram cerca de 70 tiles na área normal (1210 de 1280). O H32 com framebuffer de 30 colunas, ainda não feito, liberaria mais.
