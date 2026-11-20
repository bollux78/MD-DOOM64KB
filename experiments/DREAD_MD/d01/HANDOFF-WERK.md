# Handoff DREAD-MD D01 → Werk

Branch: `exp-dread-md-d01` (repo bollux78/MD-DOOM64KB). Diretório: `experiments/DREAD_MD/d01/`.
Workflow: `.github/workflows/dread-md-d01.yml` (roda no push que mexe em `experiments/DREAD_MD/**`;
se o push só mexer no yml: `gh workflow run dread-md-d01.yml --ref exp-dread-md-d01`).

## Estado atual (commit "Dread-style wall scalers ... run-time modes")

- Renderer estilo Dread para a E1M1 do doom1.wad (shareware): BSP do Doom front-to-back podado por PVS
  pré-calculado (`tools/pvsgen.c`), teste de bbox de 2 cantos, union-find `nxt[]` para pular colunas
  fechadas, chão/teto em cor sólida por setor, cada pixel escrito uma vez.
- Paleta única (NPAL=1). Texturas pré-iluminadas por bucket de luz, 1 byte = par de pixels.
- **Modos em tempo real** (START no jogo abre o menu, na window plane):
  - modo 0 H40 linhas duplicadas (160×72, HInt a cada 2 linhas reescreve VSRAM; buffer duplo)
  - modo 1 H40 colunas duplicadas (80×144, words; buffer simples)
  - modo 2 H32 linhas (128×72) e modo 3 H32 colunas (64×144)
  - `R_SetMode(colb, tcols)` em `render.c` define `r_vw, r_vh, r_colb, r_halfw, r_horizon, r_vfocal,
    r_zppk, r_tcols, r_fbbytes, r_colofs[]` e os ponteiros dos cores asm. `set_mode()` em `main.c`
    refaz name tables, H32/H40, HInt on/off e layout do HUD (`HUD_SetLayout`).
- **Paredes**: escaladores no estilo Dread (`tools/gen_scalers.py` → `scalers.s`): 256 níveis de passo de
  texel (log, 1/64..32 texel/linha), cada linha um `move.b/move.w d16(a1),d16(a0)` (16 ciclos).
  Fallback com máscara (`tmkb`/`tmkw`) quando o trecho passa da coluna armazenada 2×.
- Texturas em dois blobs: `tex_blob` (bytes) e `tex_blob_w` (words, modos de colunas). ROM ~3,4 MB
  (limite 4 MB sem mapper — atenção ao adicionar sprites!).
- HUD do Doom (plane B, PAL3), rosto (PAL2), pistola por sprites de hardware (PAL1), abertura
  "REPROGRAMMED BY BOLLUX78 2026". Portas abrem com B. Colisão em `blocked()`.
- Bench (BlastEm, rota fixa, dt fixo = 4): linhas H40 6,0 fps antes dos escaladores. O run atual mede
  o ganho dos escaladores. Meta: passar o DreadMD do happy ferret (~7 fps).

## O que o Claude está fazendo agora (NÃO mexer para evitar conflito)

- `src/colasm.s` (seg_columns, tex_part, escaladores, fills) e `tools/gen_scalers.py`.
- `draw_seg()` em `src/render.c`: fase A (arrays por coluna: yc/yf/ybc/ybf, âncoras de u/zpp) e o
  setup por seg → asm. Hoje draw_seg ≈ 25% do quadro.
- Menu/modos (`set_mode`, `menu` em `main.c`).

## Frentes para o Werk

### 1. Outras otimizações (fora das paredes)
- `render_node` / `bbox_visible` / `xform` / `proj` (≈ 15% juntos): passar para asm ou reduzir chamadas
  (cache de vértices já existe via `vstamp`).
- `blocked()` percorre TODAS as linhas do mapa por movimento (2,4%): usar blockmap do WAD ou grade.
- `R_PointInSub` chamado várias vezes por quadro em main.c (doors_tick, cur_floor, render): calcular
  uma vez por quadro e reaproveitar.
- `doors_tick`, `use_line`: só rodar quando houver porta ativa.
- DMA do framebuffer: hoje 2048 bytes por VBlank em pedaços; avaliar DMA maior em H32 e no modo
  colunas (buffer simples espera o DMA antes de renderizar — dá para renderizar a parte já enviada).
- Sega CD (detecção e aceleração, como o ROM do ferret) — futuro.

### 2. Atores e objetos (THINGS da E1M1)
Proposta (coerente com o Dread e com o ferret, que desenha inimigos no framebuffer):
- `conv.py`: exportar THINGS (x, y, ângulo, tipo, flags de skill) e os sprites necessários
  (frames de frente/rotação mínima), convertidos para pares de cor da paleta única, colunas
  armazenadas como as texturas (byte e word). Cuidado com o tamanho da ROM (4 MB).
- Depth por coluna: durante as paredes, guardar o z (ou 1/z) da parede que FECHOU cada coluna e,
  para colunas que seguem abertas, os recortes (ceil/floor) por "drawseg" como no Doom
  (`R_DrawMasked`), ou mais simples: lista de drawsegs com x-range, escala e clips.
- Depois das paredes: projetar things visíveis (subsetores visitados com PVS), ordenar de trás para
  frente, desenhar colunas com máscara (cor 0 = transparente) recortando contra os drawsegs mais
  próximos. Reaproveitar o estilo dos cores (jump-in, offsets fixos).
- Objetos estáticos primeiro (barris, colunas, itens), depois inimigos com IA mínima
  (acordar/andar/atirar) e colisão com o jogador.
- Arma do jogador continua em sprite de hardware (já existe).
- Interface sugerida: `void R_DrawThings(const View *v)` chamada no fim de `R_RenderView`;
  não alterar a ABI de `ColJob`/`seg_columns` sem combinar.

## Regras do projeto (do usuário)
- Nunca commitar WAD/ELF públicos; ROMs shareware podem. WAD registrado é privado.
- ROMs saem em `/home/dan/Projetos/Personal/` (o workflow já grava lá).
- Toda ROM de teste: tela preta com fonte SGDK com nome, o que testa e "aperte START ou aguarde 15
  segundos"; cabeçalho da ROM com o nome; tem que ser jogável.
- rXXX só sobe quando aprovado; intermediários usam tag/sufixo.
- Vários arquivos = um zip. Sempre informar o link do artefato quando o build passar.
- Sem merge na main sem autorização. BlastEm ≤ 10.000 quadros por execução.
- Nada de segredos em logs; e-mail do usuário é privado.
- Trabalhar em branch própria (sugestão `exp-dread-md-d01-werk`) e rebasear sobre
  `exp-dread-md-d01`; conflitos em `render.c` são prováveis — combinar via handoff.
