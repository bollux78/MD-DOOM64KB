# R80 — prioridades após os testes R79

Definição do usuário em 27/10/2026: (1) extrair desempenho do jogo atual; (2) save/load e fontes originais nos menus, pequenas se necessário; (3) novos testes de shadow somente com diferença visual grande.

## Base e evidência

Código de referência: R79 `31807c0355298f35ec36ab0c42a847a2493d92e4`, configuração `r79-base`, `DOOM_R79_SHADOW=0`.

Benchmark completo enviado pelo usuário, DEMO3 / NTSC 60 Hz, 2.134 quadros:

| Variante | FPS médio | Mínimo 1 s | Máximo 1 s | Tempo |
|---|---:|---:|---:|---:|
| R79 base | 7,32 | 2,9 | 13,5 | 291,68 s |
| SH1 | 5,82 | 2,6 | 9,2 | 366,38 s |
| SH2 | 5,82 | 2,6 | 9,2 | 366,48 s |

SH1/SH2 rejeitadas como evolução principal: cerca de 20,5% menos FPS e benefício visual pequeno. Preservar como histórico, sem propagar seu pós-processamento para a base. Manter pedra limpa do menu com shadow, texto branco, margem do rosto, HUD original, artes fornecidas pelo usuário e quatro perfis atuais.

## 1. Desempenho primeiro

- Atualizar o perfil da R79 base; os relatórios R71 ajudam a escolher candidatos, mas não substituem a medição do build atual.
- Investigar a cola das colunas de parede (`R42_DrawPackedWall`), endereçamento de flats (`R_DrawColumnFlat`), BSP/setup em `R_Subsector`, acessos à SRAM e sincronismo/DMA.
- Conferir no assembly o que o compilador já eliminou. Candidatos iniciais: endereços pré-calculados em ROM e caminho rápido com contrato comprovado para paredes. Não repetir propostas já rejeitadas sem evidência nova.
- Uma mudança por experimento, controle e candidato separados, equivalência de saída e lógica, análise de BSS/ROM e benchmark comparável.
- Clock original, mesma área/resolução, mesmo perfil de cores, HUD, áudio, simulação e demo. Não reduzir qualidade ou alterar tempo de jogo para fabricar ganho.
- Ganho só é aceito no DEMO3 completo, no mesmo ambiente. Smoke ou amostra curta não provam ganho. Testes automatizados BlastEm continuam limitados a 10.000 frames; benchmark completo no hardware do usuário não é substituído por um smoke.
- Limites atuais: BSS ≤57.920 bytes, ROM ≤4 MiB. R79 usa 57.896 bytes PERF e 57.910 PLAY. Procurar liberar RAM sem introduzir custo no caminho quente.

Entrega da primeira rodada: controle e candidato PLAY/PERF, descrição da mudança, testes de equivalência e evidência de desempenho; não promover candidato regressivo.

## 2. Save/load e fontes

### Save/load: implementar de verdade

Achados do código atual:

- `src/m_text.c` define `DISABLE_SAVE_GAME`.
- `LoadSRAM` e `SaveSRAM`, em `src/g_game.c`, são stubs que não leem nem gravam.
- `gba_save_data_t` contém mapa, dificuldade, tempo acumulado, armas e munição. `G_DoLoadGame` chama `G_InitNew`, reiniciando a fase; não restaura posição, saúde, inimigos, itens coletados ou portas. Portanto simplesmente ativar esse menu não entrega um save completo.
- `src/r23_mapmem.c` admite até 30.720 bytes para estado de trabalho do mapa na janela SRAM de 32 KiB. Isso não comprova que os 2 KiB restantes estejam livres para saves nem que comportem um estado completo. Medir o uso real nos mapas antes de reservar espaço persistente.

Alvo: salvar a partida no ponto atual, incluindo jogador, inventário, posição, RNG, inimigos/objetos, alterações do mapa e mecanismos ativos. Não apresentar reinício de fase como save completo.

Primeiro fechar o orçamento de SRAM e a compatibilidade com o cartucho do usuário. Começar com um slot se necessário. Separar armazenamento persistente da área que a carga de mapas limpa ou usa como RAM. Se o estado completo não couber, apresentar o tamanho medido e a limitação antes de escolher um comportamento reduzido.

Formato explícito e versionado, identificação do WAD/build compatível, comprimento, checksum e confirmação de gravação. Referências de objetos devem ser serializadas por IDs, com reconstrução das ligações, sem persistir ponteiros brutos. Gravar/restaurar em fluxo ou blocos pequenos; evitar alocar todos os oito slots antigos em WRAM.

Gravação apenas quando solicitada, com render pausado. Verificar CRC antes de modificar a partida ao carregar. Testar slots vazios/corrompidos/incompatíveis, gravação interrompida, SRAM ausente, reset e desligar/religar. O jogo não deve informar sucesso quando a gravação falhar. Save/load não deve acrescentar trabalho periódico durante a partida.

### Fonte original pequena em VRAM

Primeiro caminho: extrair do WAD a fonte pequena original de Doom e testar sua legibilidade em células 8×8. Usar o intervalo de fonte existente, 96 tiles em 1440…1535, em vez de abrir uma nova reserva de VRAM. Isso é uma proposta de alocação, não uma conversão já validada.

A arte R78 de abertura termina no índice 1427; o font bank existente deve continuar preservado. O menu R77 lê os glyphs carregados na VRAM para compor texto branco sobre pedra escura; aproveitar esse caminho. Manter texto branco ou bege, conforme aprovado pelo usuário. A origem dos glyphs é a arte do Doom; o tamanho pode ser adaptado para o menu atual.

Checar todos os caracteres e opções, cursor, dígitos, mensagens, menu ingame, título, intermissão, H32/H40 e retorno ao HUD. Carregar/gerar a fonte na inicialização ou entrada de tela/menu, sem novo trabalho por quadro de gameplay.

## 3. Shadow: condicionado a benefício visual e desempenho

- Reabrir somente depois de estabelecer a base otimizada.
- Primeiro produzir uma comparação estática fiel ao VDP, com cena e perfil iguais, mostrando uma diferença visual grande e útil: suavidade das colunas, detalhes ou tons de materiais. Contagem de candidatos teóricos sozinha não justifica uma ROM.
- Implementação deve evitar a segunda passagem adaptativa pelos 798 blocos usada em SH1/SH2. Investigar atributos pré-calculados, tabelas em ROM ou integração no caminho que já escreve o mapa de tiles.
- Respeitar a granularidade de prioridades dos dois planos; não prometer shadow independente por coluna quando a geometria Pair-V não o permite.
- Comparar o desempenho com a mesma base otimizada, com as demais alterações idênticas. Exigir ausência de regressão mensurável no DEMO3 completo.
- Rejeitar o experimento se a mudança visual for pequena ou se houver perda de desempenho. Highlight continua fora do escopo autorizado.

## Sequência

1. Perfil atual e primeira rodada de otimizações isoladas.
2. Fonte pequena em VRAM e auditoria do orçamento de SRAM.
3. Save/load completo, conforme a capacidade realmente comprovada.
4. Protótipo visual de shadow e somente depois implementação candidata com benchmark.

Estado deste documento: prioridades e critérios registrados após inspeção do código. Não representa save/load, fonte ou nova otimização já implementados.
