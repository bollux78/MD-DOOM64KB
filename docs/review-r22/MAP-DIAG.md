# R22d — memória ao carregar E1M8

Quatro ROMs8×8 da mesma base R22c; música E1M1, zona/cache mantidos. Sem SRAM e sem aumentar memória para esconder a falha. Inclui sempre o par de controles.

| ROM (prefixo doom-md-r22d-) | Uso |
|---|---|
| control.bin | Controle8×8 timedemo DEMO3 |
| play-control.bin | Controle8×8 jogável normal |
| diag-direct8.bin | Inicia direto em E1M8 na dificuldade média; congela no diagnóstico ao falhar ou ao completar o carregamento |
| diag-transition.bin | Jogável desde o menu/E1M1; ao terminar E1M1, acompanha a liberação e o carregamento de E1M8 |

Teste primeiro `diag-direct8`. Se carregar, a tela diz **E1M8 LOADED OK - DIAG STOP**: parada intencional, não travamento. Depois `diag-transition`: selecione dificuldade média (Hurt me plenty) para comparar. Guarde a tela inteira da falha ou do sucesso. O teste com jogo/combate real pode revelar dados persistentes que não existem na entrada direta.

A tela mostra mapa, número da etapa, tamanho solicitado, tamanho real exigido com alinhamento/cabeçalho e tag. As últimas16medições aparecem em ordem, com memória total livre(FREE) e maior bloco(MAX). Essas duas métricas incluem cabeçalhos de bloco; compare MAX com NEED, não só REQUEST.

Etapas:0 PRE-FREE (antes de liberar a fase anterior),1 POSTFREE (depois),2 THINGS,3 SECTORS,4 LINES,5 SEGS,6 BLOCKMAP,7 NODES,8 SIDES,9 REJECT,10 SUBSECT,11 GROUP,12 SPAWN,13 DONE,14 FAIL (estado após a tentativa frustrada/purga). A entrada de cada etapa mede memória antes da operação; a seguinte mostra o resultado dela. Na entrada de E1M8, o anel conserva o fim de E1M1 e a limpeza, conforme o ponto da falha.

A instrumentação acrescenta cerca de220bytes estáticos somente às duas diag. O orçamento SGDK/font é auditado em cada ELF; a zona do DOOM não é aumentada nem reduzida pela instrumentação. Os controles não têm a instrumentação. O código de erro Z_Malloc agora usa uma mensagem curta que cabe no buffer80, e a tela divide mensagens em linhas de38caracteres. Não se está afirmando que isso era a causa da falta de memória.

Histórico: transição já falhava na primeira ROM silent/desde R18, antes de4×4. Com LOW_MEMORY, E1M1 aponta explicitamente para E1M8. O WAD real na ROM possui mapas distintos E1M1 e E1M8; as demais entradas E1 repetem E1M1. Blocklinks precisam3312bytes em E1M1 e11648em E1M8 (+8336), mas a operação que falha deve ser identificada pela tela, não presumida.

Resultados possíveis: falha em entrada direta indica que a demanda/capacidade do carregamento de E1M8 já é problemática sem uma fase anterior; sucesso direto e falha na transição orienta a investigação para dados persistentes/liberação/fragmentação ou diferenças de estado. Isso ainda não prova vazamento específico.
