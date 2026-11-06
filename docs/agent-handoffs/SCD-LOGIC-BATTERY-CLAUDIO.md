# Sega CD — bateria de lógica para revisão do Cláudio

Base de código: `3811ee9b5602f69c04a590949ebdd436ea9a7fe7` na branch `exp-chatgpt-scd-bench03b`. As cinco ROMs estão em `/home/dan/Projetos/Personal/scd-logic/run-42294870972-1/`. O header e a tela final exibem o nome do arquivo. [Build e regressão no BlastEm](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42294870972).

## Evidência

Daniel rodou as cinco instâncias simultaneamente no BlastEm. A tela final mostra E1M1 Robin Woehler, AI NORMAL, SHADOW OFF, 2.600 quadros e FPS CHECK OK em todos os casos. As cinco telas mostram DEMO FINISHED / NO EXIT. A tabela registra o fim da reprodução, sem indicar conclusão do mapa.

| Variante | Média FPS | Mínimo de 1 s | Tic do mínimo | Tempo (s) |
|---|---:|---:|---:|---:|
| native | 7,02 | 2,4 | 299 | 370,42 |
| rays | 5,96 | 2,5 | 294 | 436,17 |
| all | 5,38 | 2,6 | 73 | 483,30 |
| sound | 5,18 | 2,1 | 296 | 501,57 |
| sight | 4,89 | 2,3 | 298 | 531,80 |

Raios e ALL mostram uma carga contabilizada. Os mínimos ocorrem em tics diferentes. Trate o ranking da bateria simultânea como observação a reproduzir. Compare VBlanks em janelas com os mesmos gametics, registre recargas e separe tempo emulado de tempo de parede do host.

Na [bateria curta automatizada](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42291907155), o controle marcou 4,000 / 4,293 FPS em E1M1 tics 200–260 e E1M7 tics 280–440. Som marcou 4,063 / 4,364, raios 3,996 / 4,293, visão 3,978 / 3,871 e ALL 4,040 / 3,926. Os hashes de imagem bateram nos checkpoints. Em E1M7, até o fim da coleta, ALL registrou 1.088 chamadas de visão, 15 de som e 66 de raios. Esses contadores incluem o trecho anterior à janela.

## Implementação atual

- Em `experiments/DOOM_SCD_03E/logic/`, `main_logic.c` faz duas trocas de Word RAM por chamada e espera a conclusão. `sub_logic.c` contém os núcleos.
- Visão: nós do BSP residentes. O CD devolve a sequência de subsetores. O MD ainda resolve as linhas, alturas e bloqueios.
- Som: grafo de portais residente. O MD envia todas as alturas de setor por alerta. O CD calcula alcance com o limite de uma barreira sonora. O MD aplica os alvos sonoros.
- Raios: o MD coleta interceptações. O CD só ordena as candidatas de cada bloco. O MD aplica os callbacks de tiro na ordem original.
- ALL liga os três núcleos. Todas as cinco variantes usam o render nativo. A BSS de 57.900 bytes passou no limite de 57.920.

## Pedido ao Cláudio

1. Diagnosticar a diferença entre o ganho curto de som e a regressão na demo inteira. Repetir **native × sound × rays** em série, na mesma configuração, separando o trecho 200–260, a região dos piores tics (~294–299) e a reprodução completa. Se a divergência persistir, comparar estado do jogo, recargas e atividade dos núcleos por janela.
2. Medir **tempo bloqueado do MD, bytes e trocas por janela**, separando preparação, cálculo remoto e aplicação do resultado. Considerar um controle local que use a mesma estrutura de dados e o mesmo algoritmo do núcleo candidato, especialmente para som e ordenação. Isso ajuda a separar ganho algorítmico de ganho do segundo processador.
3. Propor uma divisão que conclua uma tarefa útil na expansão. Hipóteses: som com atualizações de abertura e retorno compacto, visão completa em lote com retorno de bits e fallback para consultas inválidas ou atrasadas, raio inteiro com lista curta de eventos em ordem. Identificar qual merece um protótipo e como refutá-la. A redução de comunicação é uma orientação, e o tempo total decide se uma troca ou pacote maior compensa.

Preservar a sequência das ações de jogo e validar cenas com portas e monstros. Usar BlastEm nesta etapa e manter o nome exato do arquivo no header e na tela final. A tarefa deste handoff é diagnóstico e proposta; os números acima não pressupõem uma arquitetura vencedora.
