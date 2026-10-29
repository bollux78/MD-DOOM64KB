# R89 — IA aprovada e seletor Normal / Low

Uma PLAY baseada na R88 AI, com céu original. Options -> AI mode: Normal / Low; Low é o padrão na inicialização. Esquerda/direita alternam. A seleção permanece na sessão, inclusive ao iniciar partida/carregar save, mas não é gravada no slot nem persistida após reiniciar a ROM. Normal faz o predicado de adiamento retornar zero e percorre os caminhos originais de decisões. Low usa a variante já aprovada: decisões distantes de 512 unidades adiadas em três de quatro fases; movimento/collision thinker continuam ativos.

Benchmark E1M1/E1M7 respeita o modo escolhido e mostra AI MODE no resultado. Não gera PERF nova. Um byte inicializado de estado; verificar RAM total/BSS e ROM no workflow. Teste host compila funções C reais do seletor, callback do menu e predicado; verifica default Low, alternância, modo Normal, proximidade e cadência distante. Smoke em BlastEm verifica inicialização; a UI e benchmarks completos precisam de teste pelo usuário.

Próximas hipóteses: medir chamadas/custo de P_CheckSight, P_TryMove e espacialização de sons; testar fases de decisão distribuídas por inimigo para reduzir picos; avaliar cadências/limiares alternativos. Nenhum ganho novo dessas hipóteses está demonstrado.
