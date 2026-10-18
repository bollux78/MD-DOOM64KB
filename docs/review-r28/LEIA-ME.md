# R28 — SRAM e auditoria de vídeo

Base: R27 8d6258d180487464404af8d32f9b4af028b51a64. Todas 8×8.

Teste primeiro low-window, low-fixed, low-group. Depois low-play e group-play.
Controle legado: control (timedemo) e play-control. Episódio completo: episode-perf e group-perf (duas otimizações de agrupamento).

low-window/fixed/group/play preservam todos os mapas, mas só a faixa E1M1 é usada em todos os eventos. Isso permite ROM inteira até 2 MiB e SRAM continuamente habilitada nas fixed/group/play. As variantes episode/group normais preservam a trilha completa e alternam o mapeador.

## O que mudou

Todas as ROMs com vídeo têm a mesma auditoria. Dois incrementos de 16 bits por apresentação/upload; leituras do heap só na alocação e após encerrar a medição. Comparar R28 entre si; os contadores podem alterar ligeiramente a comparação com R27.

Tela final, linhas adicionais:
- BUF PTR16 / HEADER: últimos 16 bits do endereço do snapshot e cabeçalho do alocador. HEADER esperado 2131 (=2128 bytes +2 de cabeçalho +1 de bloco ocupado).
- FREE BEFORE / AFTER: heap na alocação, diferença esperada 2130 bytes.
- COPIES / UPLOADS: ambos devem avançar. Podem diferir por uma transferência pendente.
- RAW FREE / ERRORS: leitura independente e volátil dos cabeçalhos SGDK e máscara de inconsistências. RAW FREE deve coincidir com SGDK FREE na linha anterior; ERRORS esperado 0.

Máscara: 1=cadeia inválida; 2=tamanho/ocupação do snapshot; 4=ponteiro não encontrado; 8=leitura SGDK divergente; 16=quantidade/tamanho de alocações; 32=buffer não utilizado.

A R27 low-fixed mostrou 3452 bytes livres, contra 1326 da low-window. Ambos os binários contêm a alocação de 2128 bytes. A causa da discrepância ainda não foi demonstrada em execução com VDP: esta auditoria permite distinguir telemetria incorreta, buffer ausente e corrupção. Não é declarada uma correção sem esta evidência.

low-group combina SRAM fixa e agrupamentos de lado/linha; low-play é sua equivalente jogável. group-play mantém todas as músicas.

Envie captura da tela completa, especialmente das quatro linhas de auditoria. Esperado DEMO3/E1M1, 2134 frames. Abertura e seletor mantidos.

Arquivos cpu-* são verificações internas sem VDP e ficam fora do ZIP para teste humano. Não abrem imagem em BlastEm.
