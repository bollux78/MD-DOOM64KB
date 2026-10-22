# R54 — busca experimental da frequência de lógica que melhor se adapta ao Mega Drive

Data: 22/10/2026. Isolado da R53 microdither e da R52 validada. `r54-logic-cadence-lab`.

## Hipótese revisada: nenhum valor pré-fixado é o vencedor

A cadência original é **35 tics/s**, mas os ~5,43 FPS da R52 em hardware NÃO provam que PLAY executa 35 updates/s. `d_main.c` tem dois caminhos:
- PERF/DEMO3 força `singletics`: um `G_Ticker` por frame desenhado; benchmark antigo totaliza 2134 frames por 2134 tics.
- PLAY real usa `TryRunTics()`, almeja o tempo de `I_GetTime() = VBlanks * 35/60` e só prepara até cerca de 4 comandos pendentes. Pode perder tics sob carga pesada.
É preciso medir os **TPS realmente executados**, FPS, resposta dos controles, velocidade física e estabilidade simultaneamente.

## Primeira matriz diagnóstica — sete cadências

`doom-md-r54-l32f-hXX-play.bin` com XX = 35, 28, 24, 21, 18, 15, 12.

Todas usam exatamente a mesma base R52 Cláudio `luma32-forbid`, composição `COLORMAP` e Pair-V Fast; sprite de pistola por hardware desligado. Apenas a geração dos tics de gameplay muda.

Implementação:
- `I_GetTime()` e o relógio físico/benchmark permanecem baseados em 35 ticks Doom derivados dos VBlanks de 60 Hz.
- `I_GetGameTime()` calcula `VBlanks * R54_LOGIC_HZ / 60`, exclusivamente para o agendamento de PLAY, sem acumulador de erro.
- `D_BuildNewTiccmds()` e `TryRunTics()` usam essa cadência no experimento.
- HUD superior esquerdo mostra `Lxx TPSyy` com tics de `G_Ticker` efetivamente concluídos em 60 VBlanks. HUD superior direito mostra FPS de apresentação no relógio físico.
- **IMPORTANTE:** `TICRATE` global, física, duração de estados, movimento por tic e lógica de inimigos permanecem em 35 Hz! Portanto, reduzir a cadência faz o gameplay ficar MAIS LENTO. As ROMs são diagnóstico de custo, não a versão final normalizada.
- O benchmark DEMO3 PERF não é adequado a essa comparação: executa um tic/frame independentemente do relógio de PLAY. O workflow só compila variantes PLAY.

## Teste recomendado (um minuto real por ROM)

1. Com a mesma fase e câmera, observar FPS estável e TPS exibido no alto à esquerda por ~60 segundos.
2. Em cada frequência, caminhar em linha reta por 10 segundos cronometrados, anotando deslocamento aproximado no mapa; depois medir virar 90°, disparos e recargas em segundos reais.
3. Observar inimigos e colisões: verificar se o jogo fica demasiadamente lento; FPS alto com movimentação deficiente NÃO é progresso.
4. Repetir com 1, 2 e 3 inimigos na tela, com e sem música, anotando variações e engasgos.
5. Comparar responsividade (botões, strafe, abertura de portas, animação de pistola) com o controle R52. 
6. Não usar o cronômetro de tics do próprio jogo como métrica de duração real, nem comparar progresso do DEMO3 entre variantes de frequência diferente.

## Regra de decisão para R54B

Selecionar uma faixa candidata **a partir da medição do console**, e não por suposição de que 15, 20 ou 35 serão ideais. O objetivo final é preservar sensação de velocidade parecida com DOOM e priorizar fluidez/responsividade. Se 35 Hz simulado continuar caro, há três estratégias para avaliar separadamente:
1. Otimizar `G_Ticker/P_Ticker` ou seus subpassos e manter 35Hz lógico (preferível se viável).
2. Fazer relógio de jogo menor e normalizar tempos/velocidades de forma explícita, auditando movimento, colisões, inércia, estados, armas, IA e scripts; demos originais 35Hz precisam modo compatível.
3. Usar cadência diferenciada para subsistemas caros, sem desincronizar física básica ou entrada, somente após profiling.

Evitar mudar globalmente `#define TICRATE 35` sem dimensionar a base de tempo, RNG/demos, efeitos temporizados e muitas constantes literais em `p_mobj.c`. Também evitar auto-adaptação contínua da frequência em plena ação: pode produzir velocidade variável, perda de determinismo e comportamento irregular dos inimigos. Estabelecer um regime fixo confiável primeiro.

## Critérios de compilação

R54 GitHub Actions `r54-logic-cadence-matrix.yml`: valida geração racional de tempo, 7 ROMs, identidade de cabeçalho de 4 MiB, orçamento de BSS e teste de inicialização de 800 frames no BlastEm. Esses testes não verificam velocidade de gameplay; esse é o objetivo das medições de PLAY no hardware.
