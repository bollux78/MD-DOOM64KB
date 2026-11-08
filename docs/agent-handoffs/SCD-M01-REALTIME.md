# M0/M1 — relógio independente e custo do display

Estado: implementação experimental em validação; não declarar ROM aprovada a partir de compilação apenas. S2e permanece referência separada. M2a do Cláudio não foi alterado.

## Critério do Daniel

Não exigir equivalência exata de trajetórias, IA ou estado em relação ao nativo. Aceitar desvios documentados quando trouxerem ganho substancial. Integridade de memória, Word RAM, pacotes, controles e aplicação do estado continuam obrigatórias.

## Implementação

`build_setup.py --m01` deriva da S2e e produz `doom-md-scd-m01.bin`. O CD usa o stopwatch de 12 bits (30,72 µs/unidade), acumulador racional de 35 Hz, até quatro tics de recuperação e contador de tics descartados. O MD escreve uma demanda em `$A12012`. Entre tics, o CD anuncia um pedido TIC, aguarda input preparado pelo MD, captura o estado completo mais recente e troca os bancos. As diferenças de mundo/R24 são calculadas somente na publicação, portanto desde a última entrega. O input recebido permanece ativo até a próxima troca.

Sequência de entrega e gametic agora são distintos. O cabeçalho mantém a sequência no word 2; câmera word 9 contém o gametic real. Métricas nos words 52–60: gametic, tempo de stopwatch acumulado, descartes, quantidade de tics, soma/máximo do custo de G_Ticker, maior intervalo entre leituras do relógio, fase acumulada, sequência de publicação. A espera síncrona por lumps também lê o relógio para contabilizar eventual bloqueio enquanto o MD desenha.

Não reduzir IA nesta primeira variante. Não prometer 35 Hz antes do teste pelo relógio independente do MD. O timer de 12 bits exige leituras em menos de uma volta (~125,8 ms); comparar cadência com VBlanks do MD para detectar perda de voltas.

## M0

Na mesma ROM, modos de depuração congelam o spawn e renderizam 24 quadros usando estado nativo ou proxies CD. Modos adicionais repetem os dois textos de diagnóstico antigos para medir seu custo. Não exigir imagem idêntica para aprovar desempenho.

Medições separadas: raster, conversão R92/R115, ISR de entrega DMA, espera extra após display, textos e total. Unidade: stopwatch, convertível por 0,03072 ms. VBlank permite desambiguar voltas do stopwatch em fases longas; não substitui a medição fina. DMA e espera são intervalos potencialmente sobrepostos, não somar todas as colunas como custos exclusivos. Scratch do profiler em Word RAM `$61B200–$61B257`; não reservar arrays na RAM de trabalho escassa do MD.

Na execução normal, retirados os dois textos por quadro. Mantida a espera extra de vídeo enquanto sua redundância não estiver comprovada. HUD, resolução, conversão e raster permanecem os da R128.

## Verificações

`m01/test_frozen.py`: 24 quadros por modo, relatório privado de custo. `m01/test_realtime.py`: aplicação real dos estados, checksum de cada pacote, reconstrução de deltas, auditoria de atores/listas/armas, eco de input, alternância dos bancos, ausência de G_Ticker no MD e retorno normal. Medir Hz a partir de gametics entregues e VBlanks MD; meta 35 ±2%, descartes zero. Diferentes trajetórias entre modo profundo e produção são esperadas quando inputs permanecem ativos por durações diferentes.

Resultados e caminho da ROM deverão ser acrescentados após uma execução validada. A primeira compilação gerou ROM mas falhou na inicialização com mensagem SGDK de falta de memória; não usar aquela ROM como entrega de teste.
