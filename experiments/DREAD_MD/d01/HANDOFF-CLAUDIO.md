# Dread MD D01 — handoff para o Cláudio

A versão mais recente é **Combate 03**, uma ROM de 3,75 MiB com os nove mapas do Doom shareware. É uma build de teste para cartucho padrão.

[Baixar Doom-D01-Combate-03-Menu.zip](builds/Doom-D01-Combate-03-Menu.zip?raw=true) · [Comparar toda a branch com a base do Cláudio](https://github.com/bollux78/MD-DOOM64KB/compare/fa5339e69e4e2dd5f8fe6a088f1a3c5fadb8ccba...exp-dread-md-d01-werk) · [Instruções de build](tools/BUILD-MAPS.md)

Na abertura, START, A, B ou C mostram o menu. **New Game** entra em E1M1, **Select Level** lista E1M1–E1M9 pelo nome e **Benchmark** executa o percurso fixo de E1M1. Durante o jogo, A dispara, B opera portas compatíveis e START abre a pausa do D01.

## Histórico

| Commit | O que entrou |
| --- | --- |
| [8a7d458](https://github.com/bollux78/MD-DOOM64KB/commit/8a7d4588dded5fa575a276c3d3a4e969f4a8b7cb) | Conversor com setores de 16 bits, builds por mapa e suporte a testes de geometria. Foram abertas em emulador as 18 ROMs individuais de Doom shareware e Freedoom Phase 1 E1M1–E1M9. |
| [59ec940](https://github.com/bollux78/MD-DOOM64KB/commit/59ec940c760fad08f490987c2af4033b8cfa341d) | Nove fases na mesma ROM, colunas de textura e dados de sprites deduplicados, PVS compactado por linha, dicionário de tiles do HUD e da pistola, introdução e nove músicas XGM2. |
| [feff31b](https://github.com/bollux78/MD-DOOM64KB/commit/feff31b40372d7248e508a279b6ea8f8509acfd4) | Combate opcional com setores e recorte do D01, monstros que acordam, perseguem e causam dano, pistola que acerta o primeiro alvo visível. |
| [c85afd2](https://github.com/bollux78/MD-DOOM64KB/commit/c85afd2f6b90e081569c0d81729d33ba413b0a8a) | Combate 02. Restaurou o incremento de 2 bytes do VDP antes de carregar as paletas, tiles e tabela de sprites da interface. |
| [2aecba2](https://github.com/bollux78/MD-DOOM64KB/commit/2aecba2ee07f3a8018830876d1353d23b376514b) | Combate 03. Restaurou a arte de abertura do Bollux, com texto branco e fundo escurecido no menu inspirado na R128. |

## Validação

- **Combate 03 no Genesis Plus GX.** Menu, abertura das nove fases, HUD, pausa, mudança de H40 para H32 e retorno ao jogo. No encontro controlado de E1M1, a pistola marcou seis acertos e dois abatimentos.
- **HUD e arma no BlastEm.** Na Combate 02, foram observados a pistola, o clarão do disparo e a munição de 50 para 49.
- **Benchmark de E1M1 no Genesis Plus GX (NTSC).** Foram 312 quadros no mesmo percurso. Combate 02 e Combate 03 ficaram em 3,80 FPS. A build da Combate 03 com a IA desativada ficou em 3,79 FPS.
- **Cadência no encontro controlado.** Dois atores moveram-se a cada 48 e 53 VBlanks, respectivamente, cerca de 0,8–0,9 s. A IA roda em quatro grupos e limita o deslocamento por atualização. O percurso fixo de benchmark mede o FPS naquela rota e não caracteriza todas as cenas de combate.

## Engenharia reversa de Bermuda e E1M1 Alpha 2

Rastreamento das ROMs fornecidas pelo Bollux no Genesis Plus GX instrumentado, em NTSC, com hardware em modo Mega Drive sem Sega CD (`system_hw = 0x80`). O início de um quadro exibido foi identificado pela troca da tabela de tiles do viewport, depois da transferência gráfica. Esse marcador deixa as animações do HUD e os flashes de paleta fora da contagem. O FPS foi calculado pelo total de intervalos completos dividido pelo tempo em VBlanks.

| ROM e trecho | VBlanks por quadro 3D | FPS observado |
| --- | --- | ---: |
| `Bermuda.bin`, *Hello Bermuda*, em movimento e com inimigos ativos | 6–15, com moda de 10, em 25 intervalos | 6,27 |
| `Bermuda.bin`, após a morte, com a câmera parada | 5 consecutivos no trecho estável | ~12 |
| `E1M1-alpha2.bin`, caminhada e giros em E1M1 | 5–18, com mediana de 7, em 136 intervalos | 7,64 |

Os ~7 FPS observados jogando são compatíveis com as médias. A duração de cada quadro varia em jogo. Na Bermuda, o trecho de renderização medido antes do empacotamento levou **74,7–135,3 ms** em 26 amostras, com mediana de **122,1 ms**. O empacotamento levou **20,5–20,9 ms** em 29 amostras. Essas durações são tempo decorrido no emulador, incluindo interrupções e eventuais paradas de barramento durante cada trecho.

### Pipeline 68000 → SRAM → VDP

1. As duas ROMs desenham **72 linhas distintas**. O empacotador em assembly duplica as linhas para formar o viewport de **320 × 144 pixels**. Ele está em `$07EEDE` na Bermuda e em `$07E3EA` na Alpha 2. Os bytes dessa rotina coincidem nas duas ROMs.
2. Sem Sega CD, o buffer empacotado usa a **SRAM do cartucho**. Os cabeçalhos declaram `$200000–$20FFFF` e o DMA lê o viewport a partir de `$20A600`.
3. São **11.520 palavras / 23.040 bytes** por viewport. A Bermuda envia os quatro lotes em VBlanks sucessivos, **um lote por VBlank** durante a transferência, e alterna o destino na VRAM entre `$0200` e `$5C00`. O tamanho normal foi 3.144 + 3.200 + 3.200 + 1.976 palavras. O primeiro e o último lotes variaram quando o primeiro VBlank também enviava dados da interface.
4. Depois dos lotes gráficos, o engine copia a tabela correspondente para `$E100` com um DMA de **1.152 palavras**. Esse foi o marcador de apresentação usado no perfil.

| Endereço na Bermuda | Ponto de verificação |
| --- | --- |
| `$08D8C6 → $08D902` | Janela medida do trecho de renderização, do preparo imediato da chamada até o retorno |
| `$08D940`, `$08DFA8` | Verificação e espera pela fila gráfica antes de empacotar o próximo quadro |
| `$07EEDE → $08E0D4` | Entrada e retorno do empacotador na chamada do loop principal |
| `$088362` | Callback de VBlank que avança a fila de DMA |
| `$088700`, `$0887BE` | Seleção do próximo lote e sinalização de término do envio do viewport |
| `$08E2A6` | Caminho alternativo associado ao Sega CD, fora das execuções deste teste |

### Comparação com a D01 Combate 03

Os **3,80 FPS** da D01 vieram do percurso fixo do benchmark. Os **7,64 FPS** da Alpha 2 vieram de outra sequência de poses no E1M1. Para quantificar a diferença, use as mesmas posições e ângulos nas duas ROMs, com as portas e os atores em estados equivalentes. Registre separadamente **visibilidade e preparação de paredes**, **rasterização de colunas e sprites**, **empacotamento** e **apresentação por VBlank**. A prioridade sugerida é medir os dois primeiros estágios. A Alpha 2 já demonstra que a cadência observada é possível mesmo com o custo do empacotador e quatro lotes DMA.

Os offsets acima correspondem às ROMs com estes SHA-256:

- `Bermuda.bin` — `9b9e61f63c18a2934d42081ca31eeb5e2200d56dc6d03bd1c541c0a69b322cc6`
- `E1M1-alpha2.bin` — `47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267`

## Estado da build

A seleção de fases funciona na abertura. Ainda faltam transições pelas saídas, projéteis, outras armas e animações direcionais dos monstros. O episódio usa o modo de linhas duplicadas e mantém o recorte de sprites do D01. O modo de colunas está disponível nas builds antigas da base. A ROM pública deste handoff é a do Doom shareware.

```bash
GDK=/caminho/sgdk DREAD_COMBAT=1 \
  bash experiments/DREAD_MD/d01/tools/build_map.sh \
  /caminho/doom1.wad EPISODE /caminho/saida 'DREAD MD COMBAT 03'
```

SHA-256 do ZIP `6d2c20e68b1a63817240b9a593b8a9661e96b7a6e6d039647d4665c32bb88709`.
