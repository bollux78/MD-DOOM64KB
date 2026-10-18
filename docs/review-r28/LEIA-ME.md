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

A verificação isolada do código de máquina MEM_alloc da R27 confirmou 3456→1326 bytes na low-window e 3452→1322 na low-fixed, em heap inicializado com a fila DMA. Isso valida o alocador isolado, sem provar o estado do vídeo durante o timedemo. Veja R27-ALLOCATOR-CHECK.json.

## Verificações concluídas

CI: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39153691175
13 ROMs compiladas, nove destinadas ao teste humano. Mapas, DEMO3 e áudio E1M1 idênticos nas variantes correspondentes; código/músicas abaixo de 2 MiB e ROM inteira das fixed até 2 MiB.

CPU: nove mapas, duas dificuldades e 36 frames por variante, todos com hashes idênticos entre base, group, fixed e lowgroup. Ciclos de render: 23672760 / 23047024 / 23454728 / 23045216. Não são uma previsão de FPS: o teste não simula VDP/áudio. A combinação é correta nesse teste, mas seu ganho adicional precisa do timedemo.

Na R28, orçamento estático após snapshot: episode/low-window/group-perf 1310 bytes; low-fixed/low-group 1306 bytes. A auditoria ocupa 16 bytes extras em relação à R27. Esses números são previsão, a tela fornece a leitura real.
