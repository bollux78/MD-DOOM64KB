# Limites duros do Manifold (levantamento, sem mudar código)

Fonte: headers e fontes do mapa E1M9 staged (`/tmp/m12/mm_E1M9/src`), `compose.py`, `md_split.ld` e o ELF da build PROJ/WPN2. Só leitura: nada aqui foi medido em jogo.

## Objetos e tipos
| Limite | Valor | Onde | Para remover |
|---|---|---|---|
| Objetos ativos (monstros etc.) | 63 | `object.h` NULL_OBJ_LINK (6 bits); vetores `m14_*[obj&63]` | link 8 bits + reindexar vetores m14 (RAM) |
| Decorações | 255 (u8) | `object.h` (já ampliado de 127) | link 16 bits |
| Tipos de objeto/sprite | 255 (u8 `object_type`), usados 125 | `object.h`, `m12_objects.py` TYPES | tipo 16 bits + tabela de dados |
| Objetos desenhados por setor | 32 | `OBJ_SORT_BUF_SZ` | buffer maior (RAM) |
| Struct do objeto | 22 bytes | `object.h` | — |
| Sprite de objeto | grade fixa 64x64, paleta 3D do mapa | `m12_objects.py` | formato novo de sprite |

## Mapa
| Limite | Valor | Onde |
|---|---|---|
| Setores | 1024 | `portal_map.h` MAX_SECTORS |
| Grupos de setor | 512 | MAX_SECTOR_GROUPS |
| Paredes | 2048 (build usa MANIFOLD_MAX_WALLS=4096 em E1M3/6/7/8) | MAX_WALLS |
| Vértices | 1024 | MAX_VERTEXES |
| Portais | 512 | MAX_PORTALS |
| Texturas por mapa | 32 | MAX_TEXTURES |
| Bloco de mapa na ROM | 1 MB (2 bancos de 512 KB) | `compose.py`; E1M3 já no teto |
| Profundidade de portais | 32 | `portal.c` MAX_DEPTH (usa margem de pilha) |
| Grupos por quadro | 32 "bunches" | `bunch_render.c` MAX_SORT_BUNCHES |
| Buffers de recorte | 16 | `clip_buf.h` |

## Jogador, armas, som, UI
| Limite | Valor | Onde |
|---|---|---|
| Tiles de arma (idle) / (fire) | 128 / 104 (+ frames extras divididos entre os dois) | `weapon_sprites.c`, `m14_wpn_gen.py` |
| Sprites de hardware da arma | 16 | MAX_SPRITES |
| Armas | 6 (tabela gerada) | `m14_wpn_gen.py` |
| Canais de SFX | 3 | `sfx.c` |
| Itens de inventário | 8 (9 tipos) | `inventory.[ch]` |
| Itens de menu | 14 | `menu_helper.h` |

## ROM (layout atual)
- Bloco comum: 0x10000..0x200000 (cabe 2.031.616 bytes). Usado agora: **1.982.464** -> só ~49 KB livres.
- Armas+sons: 0x200000..0x20E000 (55.552 de 57.344 usados).
- Intermissão 0x20E000, música 0x218000, **área nova de armas 0x21C000** (livre até 0x280000).
- Mapas: a partir de 0x300000, 9 mapas; ROM total hoje 12 MB (meta <= 15 MB).

## RAM (64 KB)
- Variáveis nomeadas: ~8,4 KB (maiores: sprite_draw_cache 1538, vdpSpriteCache 768, bunch_wall_entries 640, sky_row_buf 576, sort_bunches 448).
- O resto é heap (`man_malloc`): dados do mapa em RAM, clip buffers, yclip, tabelas de grupos dinâmicos.
- Folga atual de .bss: **~2 bytes** (as experiências PROJ/WPN2 tiveram que cortar vetores m14).
- Vetores do motor de monstros sobre limites de RAM: mortes 7, explosões de barril 5, projéteis 3.

## O que provavelmente é fácil / difícil
- Fácil (dados): tabela de tipos, sprites, armas, paleta, nomes. Movem para tabelas na ROM geradas por ferramenta.
- Médio: contagens de mapa (precisam de formato de ROM + ajuste dos laços), objetos por setor.
- Difícil: tudo que vive na RAM e escala com o mapa (heap), sprites por linha/VRAM, banda de DMA.

## Próximo passo sugerido
1. Medir, por mapa, o uso real de cada limite (quantos setores/paredes/objetos cada mapa usa).
2. Definir o formato de dados por episódio (definição de jogo).
3. Migrar sprites e armas para tabelas na ROM, sem teto de 255.
