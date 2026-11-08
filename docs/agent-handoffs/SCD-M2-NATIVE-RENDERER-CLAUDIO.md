# M2 → M3: renderer próprio para o Sega CD (decisão e plano, Cláudio)

**Decisão do usuário (2026-11-08):**
- se um renderer específico para o Sega CD render mais, a linha passa a ser **exclusiva de Sega CD**, abandonando a compatibilidade com o MD sozinho nesta ROM. A R128 All continua sendo a versão MD;
- **no final, a resolução pode subir para 2×2.**

## Por que um renderer novo, e não o port do R128
O M2a/M2b-1 mostrou que o render R128 no sub arrasta peças feitas para as limitações do MD:
- mapa em layout de SRAM, com 64 KiB de RAM em bytes ímpares;
- colunas compostas R84 (146 KiB);
- tabelas de cor R76/R77 (104 KiB);
- a saída "pixel4" que depende da conversão R79/R91 do MD.

Somado, não cabe sem um carregador multi-janela, tabelas na Word RAM e subconjuntos por mapa.

**Um renderer escrito para o sub:**
- **lê o mapa** direto das estruturas RAM da lógica (sem SRAM);
- **lê as texturas/patches/flats** do cache de lumps (DIR/LUMP);
- **aplica luz** com um colormap simples (16 níveis × 256 → índice de cor do MD);
- **escreve direto em tiles 4 bpp** no banco 1M, já no formato de VRAM. O MD só faz DMA, **sem conversão nenhuma**: o FrameDelivery já provou o DMA da Word RAM no VBlank.

**O que muda para o MD:**
- o MD só faz DMA de tiles + HUD + som + input;
- a conversão R79/R91 e as tabelas de 512 KiB deixam de ser usadas no quadro.

## Formato de saída
- **Primeira versão:** mesma área útil e mesma densidade da R128 (o "pixel" do pixel4), em tiles 4 bpp. O MD monta a name table **uma vez** (tiles fixos) e cada quadro só faz upload dos tiles.
- **Versão 2×2:** pixel lógico de 2×2 pixels de tela. A área 3D de 256×144 vira 128×72 lógicos → 4,6 KB de tiles 4 bpp por quadro, que cabem no VBlank.
- **Paleta:** 16 cores (uma paleta 3D) + a do HUD. A quantização usa o colormap e a paleta da R128 como ponto de partida (cores já aprovadas no CRT).

## Escopo do renderer (Doom clássico, em ponto fixo, sem divisões no laço)
1. BSP front-to-back com clip de segs (solidsegs), como no Doom.
2. Paredes: colunas texturizadas com escala por coluna, recíproca por tabela pequena (≤ 8 KiB) ou `divu` por coluna (não por pixel).
3. Pisos/tetos: visplanes → spans. **Primeiro sólidos** (cor do flat), como a R128. Depois texturizados pelo sub ou pelo **ASIC** (uma linha de traço por span: o caso ideal do ASIC).
4. Sprites: vissprites ordenados e recortados por clipbot/cliptop, colunas com transparência.
5. Arma (psprite) e efeitos (fuzz simplificado).
6. Céu.

**Fonte de partida:** o algoritmo do próprio engine R128/GBA (`r_draw.c`) sem as camadas R22/R23/R84/R76: BSP, segs, planos e coisas são os mesmos. A parte nova é a saída em tiles, as texturas via cache e o colormap simples. **Reaproveitar, não reinventar.**

## Marcos
| Marco | O que é | Prova |
|---|---|---|
| **N1** | sonda: renderer novo linkado no sub com a lógica M01 (mesmo modelo de dados RAM). Tamanho + 0 não resolvidos | `build: PASS`, código ≤ 120 KiB, sobra de PRG-RAM para cache ≥ 128 KiB |
| **N2** | spawn congelado: o sub renderiza 24 vezes, o MD faz DMA dos tiles | imagem reconhecível × R128 no mesmo ponto; tempo de render no sub |
| **N3** | ao vivo, tudo no sub (M2): relógio M1, render a cada demanda, tiles no banco, MD DMA + HUD + som | FPS contra os 4,6 do nativo, com o jogo a 35 Hz |
| **N4 = M3** | lógica volta para o MD (o pacote do M1.5, no sentido inverso), o sub só renderiza, 1 quadro de pipeline | teto ~2× do nativo no spawn |
| **N5** | 2×2, chão texturizado (ASIC), assembly nos laços | — |

## Orçamento estimado da PRG-RAM (N3)
| Item | Tamanho |
|---|---|
| lógica (S2e/M01) | ~90 KiB |
| renderer novo | ~40–60 KiB |
| BSS | ~20 KiB |
| zone | 128 KiB |
| **cache de lumps** | **~200 KiB** (texturas/sprites do mapa) |
| colormap | 4 KiB |
| pilha | — |

Sem R84/R76/SRAM. **Cabe sem carregador multi-janela** se o código ficar ≤ 128 KiB. Se passar, o carregador multi-janela, que continua necessário cedo ou tarde.

## Riscos
- **Velocidade do renderer novo × o R128 ajustado** (R60 asm, R95/R96): o laço de coluna do R128 é muito otimizado. **Portar esse laço** (pair writer adaptado para tiles), em vez de escrever do zero.
- **Escrita em tiles:** colunas verticais em tiles 4 bpp exigem escrita de nibble com stride de 4 bytes por linha dentro do tile e salto de tile a cada 8 linhas. Alternativa: buffer linear de colunas e um passo de "transposição para tiles" no fim (custo medido).
  - **ou** a área "dot image" do modo 1M do sub (escrita por pixel, que o hardware arranja em cells): **testar primeiro, porque pode eliminar a transposição.**

## N0: resultado (run 42500537461, branch `exp-chatgpt-scd-bench03b`, `experiments/DOOM_SCD_CellImage`): `build: PASS`, `blastem: PASS`
- **Montagem:** o sub escreve um bitmap **linear** 4 bpp de 256×128 (stride de 256 B) em `banco+0x10000`. O MD lê a **visão "cell image"** em `0x630000` e recebe **tiles prontos**, em ordem por coluna (tile = coluna×16 + linha).

| Teste | Resultado |
|---|---|
| leitura pela CPU, 8.192 palavras | 0 erradas |
| 1 DMA de 16 KiB a partir da visão cell, tela desligada | 0 erradas, **5,1 ms** |
| 3 DMAs em 3 VBlanks seguidos, **tela ligada** | 0 erradas, 5,3 ms no total, **0 partes fora do VBlank** |

- **Consequência:** o renderer novo escreve **pixels lineares** (colunas com stride de 256 B), o hardware converte para tiles, e o MD só faz DMA.
  - Sem passo de transposição e sem tabela de conversão.
  - No modo 2×2, cada pixel lógico é **1 byte** (dois nibbles iguais) escrito em 2 linhas: `move.b d0,(a0); move.b d0,256(a0)`.
- **Ainda falta:** conferir no console (ROM só de diagnóstico, sem jogo).

## N1: resultado (run 42501603471): link do sub inteiro com a saída nova
- **Montagem:**
  - modelo "SRAM na RAM", com todos os defines R128 menos `DOOM_R12_RECIP*`;
  - **`i_genesisv.c` fora** (back end pixel4 do MD) e **`m2/scd_draw.c` dentro**: colunas de parede, sprite, fuzz e flat com a mesma matemática do R22, saída de 1 byte por pixel lógico em `scd_fb` (76×44);
  - stubs dos ganchos de MD em `m2/scd_n1_platform.c`;
  - libc/sistema do Werk.
- **87/87 fontes compilam.**
- **Fechamento** (`G_Ticker`, `P_SetupLevel`, `P_Init`, `R_RenderPlayerView`, `R_Init`):

  | Item | Tamanho |
  |---|---|
  | **Funções** | **108,6 KiB** |
  | **BSS** | 9,8 KiB |
  | **Const** | **177 KiB**, dos quais **`r84_pixels`+`offsets` = 149 KiB** |
  | **Não resolvidos** | só `G_InitNew` (é `static` no `g_game.c`; precisa de um wrapper, como o `S2D_InitGame` do Werk) e as 3 variáveis do profiler R21 |

  **`r91_joint` e `r76/r77` sumiram** com o back end novo: as tabelas de conversão e de cor do MD não são mais necessárias.
- **Orçamento:**

  | Item | KiB |
  |---|---|
  | funções | 109 |
  | const | 177 |
  | BSS | 10 |
  | "SRAM" | 64 |
  | zone | 112 |
  | **total** | **~472** |

  Sobram ~40 KiB para cache WAD (patches/sprites/flats) e pilha. **Apertado: o `r84` é o elefante.**

**Próximos passos para o N2 (spawn congelado):**
1. **Subconjunto `r84` por mapa:** só as colunas das texturas do mapa. O MD monta e manda pelo transporte (na carga), e o sub usa um `r84_offsets` remapeado. A estimativa no E1M1 é de dezenas de KiB.
2. **Carregador multi-janela:** a imagem tem 286 KiB sem o `r84`. Copiar em janelas de 128 KiB trocando os bits BK de `$A12003`.
3. **W no sub pelo cliente DIR/LUMP do Werk** (`scd_sub_w_wad.c`), compilado neste modelo, no lugar do `w_wad.c` com o WAD embutido.
4. **Programa do sub N2:** init, `G_InitNew` E1M1 (wrapper), `R_RenderPlayerView` 24×, expansão de `scd_fb` para o bitmap linear 4 bpp no banco (pixel 4×4, 304×176) e troca.
5. **MD:** DMA da visão cell em ~4 VBlanks + paleta `r22_cram` + tela de diagnóstico e START → jogo (ROM jogável).
