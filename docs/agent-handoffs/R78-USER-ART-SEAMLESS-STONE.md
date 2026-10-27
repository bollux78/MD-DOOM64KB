# R78 — pedra inferior limpa e artes fornecidas pelo usuário

Base: R77 `6f4432976c022ab6317c4a773d16f6ede134a37e`. Data: 27/10/2026.

## Alterações

- Menu ingame passa a usar `hudw_bgmap[1]`, a linha inferior de pedra limpa, em vez de `hudw_bgmap[0]`, que continha a divisória clara.
- Shadow real, texto branco e compensação da intensidade por prioridade permanecem como na R77.
- TITLEPIC substituída por `titlescreen checksVH.png`; WIMAP0 pela `intermission floyd.png` anexada.
- As cópias PNG originais estão em `assets/art/r78-title.png` e `assets/art/r78-inter.png`, com SHA-256 e alocação de paletas fixados no JSON ao lado.
- Perfis de cores, renderer, HUD e benchmark continuam os da R77; HELP2 mantém o caminho anterior.

## Codificação das imagens

Ambas já têm 320×224 e componentes RGB da rampa MD. A abertura tem 32 cores e até 18 cores em um tile; a intermissão, 30 e até 17. Um único tile 4bpp não consegue conter todas essas cores. Converter novamente com Bayer ou Floyd modificaria as artes prontas.

A solução usa os dois planos:

- BG_B: base opaca que representa os pixels presentes em sua paleta e aproxima os poucos restantes.
- BG_A: correções esparsas, com as cores exatas desses pixels restantes.
- Quatro linhas de CRAM; PAL0/15 continua branco para a fonte nativa. Não há shadow nas telas estáticas.
- Cada tile de cada plano usa uma só paleta válida. A composição sem textos sobrepostos reconstrói o RGB original pixel a pixel.

| Tela | Cores da fonte | Tiles únicos conjuntos | Último índice VRAM | Pixels RGB alterados na reconstrução |
|---|---:|---:|---:|---:|
| Abertura | 32 | 1.412 | 1.427 | 0 |
| Intermissão | 30 | 1.207 | 1.222 | 0 |

A fonte começa em 1.440; as duas telas respeitam essa reserva. Os mapas de A e B são ROM somente, sem novo framebuffer em WRAM.

O texto nativo continua em A e sua remoção restaura o mapa de correção exato. Enquanto um caractere ocupa uma célula, seu fundo transparente revela a base de B, que pode aproximar alguns pixels dessa célula. Essa limitação está nos relatórios; não alegar igualdade da imagem em áreas cobertas pelo menu/estatísticas. Quando o texto sai, a correção volta.

## Verificações

- `gen_r78_art.py --verify-only`: confere hashes, tamanho, cores CRAM válidas, cobertura dos pares de paletas, tiles e reconstrução dos bytes/atributos/CRAM com zero diferenças RGB.
- `test_r78_native.py`: compila o carregador R35 real com portas VDP simuladas e valida os dois PNGs inteiros, o mapa de restauração de texto e o fallback espelhado de HELP2. É teste host, não uma simulação completa do VDP.
- `test_r77.py`: conserva os testes de igualdade digital entre a pedra em shadow e o fundo normal dos caracteres; fixture agora contempla as duas linhas do HUD.
- CI gera duas ROMs HUD PLAY/PERF e verifica SHA, ROM ≤4 MiB, BSS ≤57.920 e flags obrigatórias. Smoke PERF limitado a 800 frames BlastEm.

Teste visual pendente: pedra sem divisórias; abertura, menu sobre título, intermissão com estatísticas e marcadores, HELP2, retorno à partida, H32/H40 e restauração do HUD. Não há nova alegação de desempenho.
