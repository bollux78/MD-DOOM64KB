# SRAM como RAM de trabalho — e o que mais RAM nos daria (análise, 18/11/2026)

Base: r079 + armas v10c/v10d, 9 mapas, ROM 12 MB, SSF. Fatos **medidos** estão marcados [M]; estimativas [E]; o que só o console responde [?].
Nada aqui foi implementado além do que já está na v10d (pools por mapa e save/pausa).

## 1. Resumo (a resposta curta)

1. **A RAM que falta é pequena e pontual**: heap 47,5–50,2 KB de 64 KB, pilha 1,4–6 KB, área de variáveis cheia até o byte [M]. A folga entre heap e fundo da pilha era ~1,4 KB nos piores mapas [M].
2. **Cada KB importa de verdade** [M]: liberar 2,35 KB no E1M1 (pools por mapa) subiu a profundidade de portais alcançada de 10 para 15 e derrubou os cortes da guarda de 27 para 13 no mesmo percurso. Cortes da guarda = ramos de portal não visitados = geometria que some.
3. **A SRAM (256 KB no X7, janela por banco) NÃO serve como RAM geral**: só se acessa por uma janela com interrupções mascaradas, Z80 parado e troca de banco; é lenta por acesso e mexe com som e H-Int. Serve bem para: (a) persistência (saves, opções, diagnóstico), (b) **estado frio** que entra e sai da WRAM em blocos (monstros dormentes, snapshot de fase), (c) área de preparação na carga da fase.
4. **Antes de gastar SRAM há ~6–8 KB de WRAM recuperáveis só por projeto** (seção 5), sem risco de timing de console.
5. Boa parte do que você listou (mais quadros de animação, mapas maiores, mais distância de visão) **é limitado por ROM, por formato e por limites de índice (6 bits, 8 bits, 32 buffers)**, não por RAM. RAM entra como custo secundário.

## 2. Números atuais

| Item | Valor |
|---|---|
| WRAM total | 64 KB |
| .data + .bss (fixo, cheio) | 9,7 KB (fim em 0x2604; v10d reserva +64 B para o save) [M] |
| Heap (E1M1 → E1M6) | 48,3 → 50,2 KB [M] |
| Framebuffers 3D (2 × 128×144) | 36,9 KB = 76% do heap [M] |
| DMA queue + buffer (SGDK) | ~3,3 KB [M] |
| Clip buffers 16 × 129 B | 2,1 KB [M] |
| Decorações (10 B) / objetos (22 B) | 255 / 63 máx.; hoje por mapa (v10c) [M] |
| Pilha usada nas caminhadas | 1,4 – 6,0 KB; guarda corta se SP < heap_high + 1792 [M] |
| SRAM X7 | 256 KB, 16 bits, metade superior do banco 31 [doc handoff]; acesso pelo slot 5 ($280000) |
| SRAM clone antigo (R104) | janela $A130F1 sobre $200000, só bytes ímpares (movep) [doc R104] |

Custos de janela de SRAM [E]: entrar = salvar SR + mascarar + pedir barramento do Z80 + 2 escritas de mapper; sair = restaurar. Ordem de dezenas de µs por janela (68000 a 7,67 MHz ⇒ 1 µs ≈ 7,7 ciclos). **Medir no console** [?].

## 3. O que realmente limita hoje (por causa)

| Causa | Efeito visível | Escala com |
|---|---|---|
| Guarda de pilha/heap do portal | geometria faltando; E1M1/2/6/9 cortam | KB livres |
| Link de objeto 6 bits (63) | máx. de monstros+pickups móveis por mapa | formato, depois RAM |
| OBJ_SORT_BUF_SZ = 32 | objetos "somem" se > 32 num setor/quadro | RAM pequena (sort bufs) |
| sprite_draw_cache 1,5 KB, vdpSpriteCache 768 B | teto de sprites por quadro | RAM pequena |
| Vetores m14 (mortes 7, explosões 5, projéteis 3, `[obj&63]`) | efeitos simultâneos | RAM + formato |
| Bloco de mapa 1 MB na ROM | tamanho de mapa, frames por mapa | ROM (E1M3 no teto) |
| MAX_* (setores 1024, paredes 2048/4096, texturas 32, bunches 32) | mapas grandes | formato/ROM |
| Fila DMA / VBlank | faixas pretas, tiles quadrados | tempo de VBlank, não RAM |
| Área .bss fixa | cada variável nova quebra o link | layout comum entre mapas |

## 4. Lista exaustiva: o que mais RAM de trabalho permitiria

Legenda de via: **W** = WRAM (por projeto), **S** = SRAM em janelas, **R** = é problema de ROM/formato (RAM não resolve), **—** = sem relação. Viabilidade: ✔ boa, ~ possível com custo, ✘ ruim.

### 4.1 Renderização e distância de visão
| # | Possibilidade | Via | Custo/ganho estimado | Viab. |
|---|---|---|---|---|
| 1 | Menos cortes de portal (guarda) | W | cada KB ≈ +2 níveis de recursão no E1M1 [M]; 6–8 KB provavelmente zeram os cortes | ✔ |
| 2 | Margem de pilha maior para mapas abertos (E1M6) | W | E1M6 tem 61 cortes mesmo após pools; precisa >2 KB | ✔ |
| 3 | Recursão mais funda que 32 (MAX_DEPTH) | W/R | só útil após 1–2; mudar constante + pilha | ~ |
| 4 | Mais "bunches" por quadro (32→48) | W | 448 B hoje; +50% ≈ +220 B | ✔ |
| 5 | Mais clip buffers (16→20) para cenas com muitos objetos | W | +520 B; hoje prof. máx. medida ≤15 | ✔ |
| 6 | Viewport maior (pitch 128→160) | W | framebuffer cresce 25% = +9,2 KB: **inviável** sem SRAM no caminho quente | ✘ |
| 7 | Viewport menor para devolver RAM | W | cada coluna a menos devolve ~144 B ×2 buffers | ~ |
| 8 | Framebuffer simples (sem double buffer) | W | −18 KB, mas pisca/rasga | ✘ |
| 9 | Framebuffer em SRAM | S | escrita por pixel via janela: impossível | ✘ |
| 10 | Cache de visibilidade por quadro (reaproveitar entre quadros parados) | W | N bits/setor ≈ 70 B | ✔ |
| 11 | Mais paletas/sky buffers (céu mais elaborado) | W | sky_row_buf 576 B; variações pequenas | ✔ |
| 12 | Menos glitch "geometria some" | W | = item 1 | ✔ |
| 13 | Menos glitch de DMA/H-Int (faixas pretas) | — | **não é RAM**; é tempo de VBlank/ints. SRAM com ints mascarados **piora** | ✘ |

### 4.2 Objetos, inimigos, decorações
| # | Possibilidade | Via | Custo/ganho | Viab. |
|---|---|---|---|---|
| 14 | Mais objetos móveis (63→127/255) | W+R | link 8 bits; +22 B/objeto; 127 objetos ≈ +1,4 KB, vetores m14 reindexados | ✔ |
| 15 | Muito mais monstros "dormentes" (paginados) | **S** | ativos na WRAM (ex.: 32), dormentes na SRAM (22 B cada); janela só ao acordar/dormir (~1×/s) | ~ |
| 16 | Decorações estáticas em ROM (const), só as mutáveis em RAM | W | E1M1 −850 B, E1M3/6/7 −1,7 KB, bitmask de "removida" | ✔✔ |
| 17 | Mais decorações (255→512) | R+W | link 16 bits; só se 16 vira dado de ROM | ~ |
| 18 | Mais objetos por setor visíveis (sort 32→64) | W | +516 B | ✔ |
| 19 | Mais projéteis/explosões/mortes simultâneos | W | cada vetor m14 pequeno (≤64 B); hoje 3/5/7 | ✔ |
| 20 | IA mais rica (estado por monstro: alvo, caminho, pânico) | W | +4–8 B/objeto; 60 objetos ≈ +0,5 KB | ✔ |
| 21 | Spawns dinâmicos (ressurreição, lost souls, teleporte) | W | exige pool maior; slack hoje 10/32 | ✔ |
| 22 | Persistir estado de monstros ao sair/voltar na fase | **S** | snapshot ≈ 1–3 KB por mapa (22 B × N); 9 mapas ≪ 256 KB | ✔ |
| 23 | Corpos permanentes (mais decorações de morte) | W | decorações de pool por mapa | ✔ |

### 4.3 Animação e sprites de inimigos
| # | Possibilidade | Via | Custo/ganho | Viab. |
|---|---|---|---|---|
| 24 | Mais quadros de animação por inimigo | **R** | frames são RLE na ROM; limite é o bloco 1 MB/mapa e .mapgap/.mapextra, não RAM | R |
| 25 | Mais famílias de monstros por mapa (hoje divididas gap/extra) | **R** | idem; E1M3 no teto de ROM | R |
| 26 | Cache de sprite decodificado | W | sprite_draw_cache 1,5 KB; dobrar ≈ +1,5 KB, menos redecodificação [E] | ~ |
| 27 | Frames descomprimidos em SRAM | S | ler por janela é mais lento que ler da ROM; só ajudaria se a ROM guardasse comprimido | ✘ |
| 28 | Sprites maiores/escala melhor | R | tabelas na ROM | R |

### 4.4 Mapas, episódios, Heretic
| # | Possibilidade | Via | Custo/ganho | Viab. |
|---|---|---|---|---|
| 29 | Mapas com mais setores (até 1024) | W | ≈ +4 B/setor (3 listas + cache): 1024 setores ≈ +2 KB sobre E1M6 | ✔ (com 1, 16) |
| 30 | Mais grupos de setor dinâmicos (portas/elevadores/luzes) | W | tabela dyn_ram: ≈ 8 B por grupo animado | ✔ |
| 31 | Mapas do Doom registrado (E2/E3) | R+W | limite é ROM por mapa (1 MB) e MAX_*; RAM por setor pequeno; **medir contagens reais do WAD** | ~ |
| 32 | Heretic (voo, artefatos, chaves, mais tipos) | R+W | inventário de 8 itens vira 13+ artefatos (+bytes), eixo Z/voo no motor (CPU), sprites na ROM | ~ |
| 33 | Um conjunto de mapas por episódio (ROM por episódio) | R | remove limites duros 255/63 como dado de ROM por episódio | ✔ |
| 34 | Mapas de ROM maior que 1 MB (streaming de banco) | R | troca de banco em runtime; RAM só para índice | ~ |
| 35 | Hub/volta entre fases com estado preservado | S | ver 22 e 41 | ✔ |

### 4.5 Armas, HUD, som
| # | Possibilidade | Via | Custo/ganho | Viab. |
|---|---|---|---|---|
| 36 | Mais armas/quadros de arma | R | tiles ficam na ROM; limite é VRAM (128/104 tiles) e vblank | R |
| 37 | HUD com mais campos (munição por tipo, relógio, mapa) | W | poucos bytes | ✔ |
| 38 | Mais canais de SFX (3→4) | W/Z80 | RAM do Z80 é do XGM; custo em buffers | ~ |
| 39 | Sons maiores/mais amostras | R | ROM (.wpndata 57 KB cheio) | R |
| 40 | SRAM como fonte de PCM | S | Z80 não lê SRAM; piora o chiado | ✘ |

### 4.6 Menus, save, persistência, engenharia
| # | Possibilidade | Via | Custo/ganho | Viab. |
|---|---|---|---|---|
| 41 | Save-state completo (mundo, monstros, portas, projéteis) | **S** | ≈ 5–8 KB por slot [E]; vários slots cabem folgados | ✔ |
| 42 | Vários slots de save e checkpoint automático por fase | S | 64 B por checkpoint hoje | ✔ |
| 43 | Opções persistentes (dificuldade, mapeamento de botões, volume, HUD) | S | dezenas de bytes | ✔ |
| 44 | Recordes/estatísticas por fase (kills, itens, tempo, segredos) | S | alguns bytes/fase | ✔ |
| 45 | Menus complexos (opções, cheats, galeria) | — | rodam na imagem de menu (bare-metal, RAM livre); limite é VRAM/ROM, não RAM | ✔ |
| 46 | **Telemetria persistente de teste no console** (FPS, pilha mínima, cortes da guarda, heap por mapa gravados na SRAM e lidos no boot seguinte) | **S** | ~100 B/mapa; elimina depender do MAME para medir o console | ✔✔ |
| 47 | Crash dump persistente (PC, SP, últimos eventos) | S | 64–256 B; ajuda em ADDRESS ERROR como o R104 | ✔✔ |
| 48 | Área de preparação na carga da fase (descomprimir mapa) | S | uma vez por fase; janela longa só fora do jogo | ~ |
| 49 | Gravar/reproduzir demos (input log) | S | 1 B/quadro; 5 min a 7 FPS ≈ 2 KB | ✔ |
| 50 | Cheats/ferramentas de debug (godmode já existe) | W | bytes | ✔ |

### 4.7 Desempenho
| # | Possibilidade | Via | Efeito |
|---|---|---|---|
| 51 | Dados quentes em SRAM | S | **pior**: janela por acesso custa dezenas de µs; nenhum laço do renderizador tolera |
| 52 | Dados frios em SRAM, copiados em bloco | S | neutro a levemente pior; ganho é RAM, não velocidade |
| 53 | Mais RAM → tabelas pré-computadas (divisões, projeções) | W | melhor, mas as tabelas grandes já estão na ROM (leitura na ROM ≈ RAM no barramento do 68000) |
| 54 | Código gerado/desenrolado em RAM (`set_up_scale_routine`, .ramprog) | W | melhor: colunas desenroladas são o ganho clássico; cada rotina custa centenas de bytes |
| 55 | Interrupções mascaradas por janelas | — | **pior**: pode perder H-Int/VBlank (como o R104) e travar o Z80 (PCM) |
| 56 | Menos cortes/redesenho → menos trabalho perdido | W | melhor, indireto |

## 5. WRAM recuperável por projeto, sem SRAM (candidatos)

| Origem | KB | Risco |
|---|---|---|
| Decorações estáticas em ROM (item 16) | 0,85 – 1,7 | médio (rastrear pickups removidos) |
| DMA queue/buffer do SGDK reduzidos (medir uso máximo) | até ~1–2 | médio (DMA perdido = glitch) |
| Clip buffers 16→14 (profundidade ≤15 medida; hoje `die()` se faltar) | 0,26 | médio |
| tile_buf do console 21 tiles → 12–14 (mensagens de chave são ≤30 caracteres) | 0,25–0,3 | baixo |
| Paletas de fade (8×128 B), só se o fade for usado | 1,0 | médio; ajustar `. = 0x1F44` |
| sprite_draw_cache otimizado/compactado | 0,5 | alto (renderizador) |
| Viewport 8 colunas mais estreita (−1 coluna de tile = −144 B ×2) | 0,3 por coluna | visual |
| **Soma plausível** | **≈ 4 – 8 KB** | |

## 6. Desenhos de uso de SRAM como "RAM" que fazem sentido

1. **Paginação de monstros dormentes** (item 15): lista ativa na WRAM, resto na SRAM; troca em blocos de 22 B × N num único intervalo de janela fora das linhas ativas.
2. **Snapshot de fase** (22, 41): ao sair da fase, copia objetos, decorações mutáveis, grupos dinâmicos e estado do jogador para a SRAM em uma janela longa (fora do jogo, como o `r81_save_codec` do R104).
3. **Staging de carga** (48): descomprimir dados da fase na SRAM e copiar por pedaços; só na carga.
4. **Telemetria/diagnóstico** (46, 47): escrita em lote 1×/segundo ou no boot; zero custo no quadro quente.
5. **Regra do R104 para tudo isso**: SR mascarado dentro da janela, janelas não aninham, nada de acesso direto a `$A130F1`/`$A130FA` no código do jogo, e validar no console (BlastEm não reproduz).

## 7. Riscos e restrições (o que quebra)

- **Slot 5 é compartilhado**: tem os dados extras do mapa (frames de monstros em .mapextra). Durante a janela esses dados ficam invisíveis; o código que roda a janela precisa estar na área comum, e nada pode ler o slot 5 com interrupções mascaradas.
- **Z80/PCM**: o XGM lê amostras pela mesma janela do cartucho; trocar banco enquanto o Z80 roda corrompe PCM. Hoje a rotina para o Z80, o que causa **estalos de som** se usada com frequência.
- **H-Int/VBlank**: ints mascarados por longos períodos perdem VBlank (faixa preta, DMA atrasado). O R104 provou corrupção no console que o emulador não mostra.
- **Persistência**: depende do firmware (clone antigo salva SRAM no SD). O X7 foi o alvo do módulo; **o clone pode mapear diferente** [?].
- **Layout comum**: o bloco de código é idêntico em todos os mapas (compose.py). Qualquer limite por mapa deve estar nos dados do mapa (como `m14_maxobj`), não em constantes compiladas.
- **Área .bss cheia**: cada variável nova exige reserva no .ld ou reaproveitamento.
- **Energia**: escrita interrompida no meio; o módulo atual usa dois registros alternados com checksum.

## 8. Experimentos que decidem (ordem sugerida)

1. **ROM de benchmark de SRAM no console** (START entra): mede ciclos de janela (enter/leave), ler/gravar 64 B, 1 KB, 8 KB; compara com WRAM; mede efeito no PCM (som) e em quadros perdidos. Define o orçamento real. (1 sessão de teste)
2. **Telemetria persistente** (item 46): barato, vale já na próxima ROM; passa a dar medições de console para todas as decisões abaixo.
3. **WRAM por projeto**: decorações estáticas em ROM + DMA queue enxuta + console menor; medir cortes da guarda de novo nos 9 mapas.
4. **Links de 8 bits para objetos** (item 14) por episódio, junto com o formato de ROM por episódio.
5. **Snapshot de fase e save-state completo** (41, 22), reutilizando o módulo do native-save.
6. Só depois: paginação de monstros dormentes (15), se o benchmark mostrar janela barata.

## 9. Conclusão de engenharia

- **Mais "WRAM efetiva" vale ouro** para visibilidade e glitches de geometria (medido), e para mais objetos; mas 4–8 KB saem de projeto, sem SRAM.
- **SRAM vale muito para persistência, diagnóstico e estado frio**; como memória quente é pior para desempenho e arrisca som, H-Int e VBlank.
- **Animação, mapas grandes, Heretic e mais armas são problemas de ROM e de formato por episódio** (limites 63/255/32/1 MB); RAM só entra como custo pequeno por setor/objeto.
