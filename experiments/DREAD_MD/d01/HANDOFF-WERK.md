# Handoff DREAD-MD D01 → Werk: inimigos ativos, troca de fase, outros mapas

Branch base: `exp-dread-md-d01` (repo bollux78/MD-DOOM64KB). Diretório: `experiments/DREAD_MD/d01/`.
Último build aprovado pelo usuário: run 44832888870 (`dread-md-d01-som.bin`, 2,6 MB).
Trabalhe em branch própria (sugestão `exp-dread-md-d01-werk`), rebaseando sobre `exp-dread-md-d01`.

---------------------------------------------------------------------------------------------------
## 1. Estado atual

| Item | Situação |
|---|---|
| Renderer | estilo Dread: BSP front-to-back + PVS pré-calculado, colunas em asm, chão/teto em cor sólida |
| Modos (menu START) | H40/H32 × linhas duplicadas (160×72, HInt) / colunas duplicadas (80×144); recorte lateral 0/−2/−4 tiles; música liga/desliga |
| Texturas | escaladores Dread (128 níveis, 1 instrução por linha), cor por **pares de pixels (linhas verticais)** numa paleta única de 16 cores |
| Objetos/inimigos | 91 coisas da E1M1 (6 monstros) **parados**, só frame A rotação 1, recortados pela janela das paredes |
| Som | SGDK XGM2 (Z80), músicas Intro e E1M1 (arranjo YM2612 do d32xr), custo ~0 de CPU medido |
| Portas | B abre (especiais 1, 26–28, 31–34, 117, 118 e por tag); fecham sozinhas após ~4 s (manuais) |
| Colisão | raio 16 contra linhas, grade de 128 unidades gerada pelo conv |
| HUD/arma | barra do Doom (plane B), rosto, pistola em sprites de hardware; A atira (só animação + munição) |

Bench (BlastEm, rota fixa, `dt` fixo): H40 linhas 6,80 fps · colunas 5,60 · recorte −2 7,38 · recorte −4 7,99.
**Atenção:** Genesis Plus GX (nosso `mdhost`) mede ~metade (3,68). O usuário vai filmar console e BlastEm
para calibrar; até lá trate o BlastEm como referência relativa, não absoluta.

Perfil (H40 linhas): seg_columns 20% · draw_seg (C) 18% · texturas (tex_part+tex_solid+escaladores) ~22% ·
BSP/projeção (render_node, bbox_visible, proj, xform) ~20% · asm da montagem (seg_anchors, calc_uq, seg_rows) ~10% ·
sprites ~5%.

### Orçamento de memória (E1M1)
- **RAM: ~37 KB usados de 64 KB → ~23 KB livres** (framebuffer 22,5 KB fixo, renderer ~9 KB, sprites visíveis ~4 KB,
  SGDK/HUD o resto). O usuário quer **mapas grandes depois** e **não quer SRAM** (nem um 2º framebuffer).
  Toda tabela fixa vai para a ROM.
- **ROM: 2,6 MB de 4 MB.** O usuário quer evitar mapper/SSF → **tudo tem que caber em 4 MB**.
  Peso por mapa hoje: texturas ~700 KB (bytes) + ~1,4 MB (cópia em words para o modo colunas), PVS ~120–380 KB,
  sprites ~17 KB. Isso **não escala** para várias fases (ver §4).

---------------------------------------------------------------------------------------------------
## 2. Arquivos e pipeline

| Arquivo | Papel |
|---|---|
| `tools/conv.py` | WAD → `mapdata.c` + `mapcounts.h` (geometria, texturas, paleta, setores, portas, grade de colisão, coisas e sprites) |
| `tools/pvsgen.c` | PVS (amostra a visibilidade com o próprio renderer; portas abertas antes) → `pvs.c` |
| `tools/gen_scalers.py` | escaladores de parede/sprite → `scalers.s` |
| `tools/gen_tables.py` | recíprocos em ROM → `tables.c` |
| `tools/gen_music.py` | VGMs Intro/E1M1 de `assets/r25-music.json` → `res/*.vgm` + `res/music.res` (XGM2) |
| `tools/gen_hud.py`, `gen_weapon.py`, `gen_title.py` | HUD (STBAR do Doom), pistola, tela de abertura |
| `src/render.c` | renderer (C), modos, sprites (`project_thing`, `draw_sprite`, `draw_things`) |
| `src/colasm.s` | `seg_columns`, `tex_part`/`tex_solid`, fills, cores mascarados, `spr_scale` |
| `src/segasm.s` | `seg_anchors`, `seg_rows1/2` (com referência C idêntica em render.c para o host) |
| `src/hint.s` | HInt de duplicar linhas (2 fases) |
| `src/main.c` | jogo: título, menu, modos, portas, colisão, bench, música |
| `src/game_hud.c` | HUD, rosto, arma, texto; todas as escritas de VRAM no VBlank |
| `host/host.c` | renderer no PC (mesmo `render.c`): `host PREFIX` (8 vistas), `raw X16 Y16 Z ANG16`, `things N [m]` |
| `test_d01.py` | bench no BlastEm via RSP (FPS, perfil por função e por linha) |
| `../tools/mdhost/mdhost.c` | emulador headless (Genesis Plus GX): script `run N botões`, `shot`, `dump` |

Build no CI = função `build()` do workflow (conv → pvsgen → gen_* → make SGDK com `-DNPAL=1 -DSTART_MODE -DSTART_CROP -DSTART_MUSIC`).

### Ferramentas de verificação
- **ROM × host idênticos:** compile com `-DFREEZE_AT=N` (o bench congela no quadro N), rode no `mdhost` com `dump`,
  leia `view` (símbolo `view` do ELF, RAM com bytes trocados: `ram[a^1]`) e renderize no host com
  `host x raw X16 Y16 Z ANG16`. Foi assim que validei todo o asm novo.
- **Vistas de coisas:** o CI gera `things/tNN.png` (primeiras coisas) e `things/mNN.png` (monstros) com o host.
- **Armadilha conhecida:** os caches de vértices têm o tamanho de `MAP_NVERTS` (`mapcounts.h`); mapa local
  diferente do usado na compilação corrompe a RAM silenciosamente.

---------------------------------------------------------------------------------------------------
## 3. Inimigos ativos (tarefa 1)

Hoje: `MapThing {x, y, sprite, sub, flags}` em **ROM**, lista estática por subsetor (`map_sub_things`).
`project_thing()` é chamado quando o BSP entra no subsetor (antes das paredes dele) e guarda a janela
aberta de cada coluna; `draw_things()` desenha do mais longe ao mais perto. **Esse esquema de janela é o que
garante o recorte certo — mantenha.**

Proposta:
1. **Atores em RAM**: copiar as coisas para `Actor {x, y (16.16), z, angle, type, state, tics, sub, hp, target, frame}`
   (~24 bytes × ~100 = 2,4 KB). Lista encadeada por subsetor em RAM (`sub_head[nsubs]`, 1 ou 2 bytes cada,
   `next` no ator), religada quando `R_PointInSub` muda. Itens coletados saem da lista.
   Troque o laço de `map_sub_things` em `render_node` por essa lista.
2. **Sprites completos** no conv: para cada tipo de monstro, frames de andar (A–D), ataque (E–F, G), dor e
   morte (H–L…), **rotações 1–8** (lumps combinados tipo `POSSA2A8` = rotação 2 e 8 espelhada → gerar a
   espelhada invertendo as colunas na conversão ou desenhando colunas em ordem inversa no runtime para economizar
   ROM). Escolha da rotação: ângulo entre o ator e a câmera, como no Doom (`R_PointToAngle`). Mesma conversão de
   cor por pares (é o que o usuário pediu: "linhas verticais, sempre funciona bem").
   Posts já têm 3 bytes de padding no fim (os escaladores podem ler 1–2 além); mantenha.
3. **IA mínima à moda Doom** (estados e tics em 1/35 s convertidos para `dt` em VBlanks): parado → acorda por
   visão (REJECT do WAD ou linha de visão simples pelo BSP/PVS) ou som do tiro → persegue (passo + `blocked()`)
   → ataca (hitscan para zombie/sargento, bola de fogo do imp como projétil-ator) → dor → morte (cadáver fica).
4. **Tiro do jogador**: hitscan no centro da tela contra atores visíveis (já temos a lista `vis[]` do quadro com
   colunas e profundidade) e dano; HUD (`HUD_Draw`) já mostra vida/munição.
5. **SFX**: XGM2 tem canais PCM livres (`XGM2_playPCMEx`, canais 2–3); o repo principal já tem efeitos convertidos
   (`src/gen_sfx.h`, uso em `src/i_genesis.c`).
6. **Desempenho**: sprites custam ~5% com 6 monstros parados; a IA deve rodar em lotes (ex.: metade dos atores por
   quadro) e nunca percorrer todas as linhas do mapa (use a grade `map_bm`).

---------------------------------------------------------------------------------------------------
## 4. Troca de fase e vários mapas na ROM (tarefa 2)

Hoje o conv gera **um mapa** com nomes globais (`map_verts`, `map_segs`, …, `tex_blob`, `md_palette`).
Para várias fases:
1. **Struct de mapa**: `MapDef { const int16_t (*verts)[2]; const MapSeg *segs; … counts; pvs; things; start; }`
   e `R_SetMap(const MapDef *)`. Todo acesso global vira ponteiro (render.c, main.c, colisão, portas).
   Arrays de RAM dimensionados pelo **maior** mapa (`MAP_NVERTS` máximo, setores etc.).
2. **Texturas e paleta compartilhadas** entre as fases do episódio (um só `tex_blob` deduplicado, uma paleta
   ajustada para todos os mapas juntos). Sem isso o episódio não cabe.
3. **ROM**: a cópia em words das texturas (modo colunas) dobra o peso. Opções: (a) gerar words só se couber;
   (b) no modo colunas ler bytes e escrever word duplicada (`move.b` em registrador + `move.w` com o byte
   repetido via tabela de 256 words, ~+8 ciclos por linha); (c) reduzir buckets de luz de 4 para 3. Meça.
   O PVS também é grande: considere RLE/compressão por linha de bits.
4. **Saída da fase**: especiais de linha 11 (exit), 51 (secret exit), 52/124 (walk-over exit). Ao ativar:
   tela de intervalo simples → `R_SetMap` do próximo → reiniciar atores, portas, `XGM2_play` da música da fase
   (`assets/r25-music.json` tem E1M1–E1M9, Intro, Inter e End; `gen_music.py` só extrai Intro e E1M1 hoje).
5. Lifts/plataformas (especiais 62, 88, 10…) ainda não existem; portas são só teto subindo (`doors_tick`).

---------------------------------------------------------------------------------------------------
## 5. Converter outros mapas (tarefa 3)

Uso: `DREAD_NPAL=1 python3 tools/conv.py WAD MAPA OUTDIR` (MAPA = `E1M1`…`E1M9` ou `MAP01`…).
Depois: compilar e rodar o `pvsgen` com o `mapdata.c` gerado (ver workflow) e compilar a ROM.
O conv lê os 10 lumps depois do marcador do mapa (THINGS, LINEDEFS, SIDEDEFS, VERTEXES, SEGS, SSECTORS,
NODES, SECTORS, REJECT, BLOCKMAP) — formato binário Doom (não suporta Hexen/UDMF).
Para trocar o mapa no CI: parâmetro `E1M1` na chamada do conv dentro de `build()`.

### Limites atuais que vão quebrar com mapas maiores (corrigir antes)
- `MapSeg.front/back` são **uint8** (0xFF = sem setor de trás) → **no máximo 255 setores**. Muitos mapas do
  Doom passam disso. Mudar para uint16 (e o 0xFF → 0xFFFF em conv/render/main).
- `MapSeg.mid/upper/lower` uint8 → máximo 255 texturas por mapa (ou por episódio, se compartilhar).
- `map_sectors` em RAM tem `MAP_NSECTORS` entradas (10 bytes cada).
- PVS cresce com subsetores² (E1M1: 237 subsetores; mapas grandes têm 1000+ → centenas de KB).
- `pvsgen` é `-DMAXV=4096`; `vis[]` no máximo 32 sprites visíveis; `winpool` 3 KB.
- Fila de portas: no máximo 64 (`door_target[64]`).
- Colisão usa raio 16 e degrau de 24; sem altura de ator ainda.

### Doom shareware (doom1.wad) — E1M1 a E1M9
WAD em `/home/dan/Projetos/doom-md/assets/wads/doom1.wad` no runner. Tudo do conv já é para Doom:
`THING_SPR` (tipos → prefixo de sprite), `MONSTERS`, texturas TEXTURE1/PNAMES, flats, `F_SKY1`, `PLAYPAL`/`COLORMAP`.
E1M2 em diante têm mais setores/linhas: confira o limite de 255 setores. ROMs do shareware podem ser públicas.

### Freedoom (freedoom1.wad = E1M1…E4M9, freedoom2.wad = MAP01…)
Compatível com Doom: mesmos tipos de coisas, mesmos nomes de sprites (arte diferente), mesmo formato de
texturas → o conv funciona como está (mapas MAP01+ só mudam o nome do marcador). Licença livre (BSD) —
pode ser público. Os mapas do Freedoom costumam ser maiores que os do shareware: limites acima.
O HUD (`gen_hud.py`) e a arma (`gen_weapon.py`) leem STBAR/PISG do WAD: confira se existem no Freedoom
(existem com arte própria); a música continua sendo a do Doom (arranjo d32xr) — trocar se quiser outra.

### Heretic (heretic1.wad shareware = E1M1…E1M9)
Mesmo formato de mapa e de patches/texturas (TEXTURE1 + PNAMES), `PLAYPAL`, `COLORMAP`, céu `F_SKY1`.
O que precisa adaptar:
- `THING_SPR` / `MONSTERS` / `THING_FRAME`: tipos e prefixos de sprite do Heretic são outros (por exemplo
  gárgula, golem, cavaleiro morto-vivo, discípulo). **Leia os tipos e os prefixos no próprio WAD** (lumps entre
  `S_START`/`S_END`) e crie uma tabela por jogo (`--game heretic`).
- HUD e arma: não há STBAR/PISG do Doom; desligar `gen_hud.py`/`gen_weapon.py` ou fazer versões Heretic.
- Especiais de linha de porta/saída são quase os mesmos do Doom; chaves são verde/azul/amarela.
- O usuário só autorizou publicar ROMs do Doom shareware; **pergunte antes de publicar algo com Heretic**.

---------------------------------------------------------------------------------------------------
## 6. Regras do projeto (do usuário)
- Nunca commitar WAD/ELF públicos; ROMs do Doom shareware podem; WAD registrado é privado.
- ROMs em `/home/dan/Projetos/Personal/` (o workflow já grava lá); vários arquivos → um zip.
- Toda ROM de teste: tela preta com fonte do SGDK com nome, o que testa e "aperte START ou aguarde 15 segundos";
  cabeçalho da ROM com o nome; START entra no jogo (tem que ser jogável).
- rXXX só sobe quando aprovado; intermediários usam tag/sufixo.
- Sempre informar o link do artefato quando o build passar.
- Sem merge na main sem autorização. BlastEm ≤ 10.000 quadros por execução. Nada de segredos em logs.
- Sem SRAM e sem mapper/SSF; RAM livre é para mapas grandes, atores e projéteis.
- Conversão de cor dos sprites: sempre por pares de cores lado a lado (linhas verticais), paleta única.
