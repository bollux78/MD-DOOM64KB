# R128 — E1M1 em blocos nativos para o 68000

Experimento de 18/11/2026. Três ROMs de 3 MiB, somente E1M1, com dados do shareware. Mantém Pair-V, amostragem tonal e arma no viewport da base usada no laboratório. Não substitui a R128 estável.

## Testar

Abra uma ROM, pressione Start e escolha `Benchmark E1M1` no menu. Use as mesmas opções nas três. A comparação abaixo usa AI NORMAL e SHADOW OFF. O benchmark executa a mesma demo de 2.134 frames. Start retorna ao menu no resultado. Também é possível jogar normalmente a E1M1; a progressão volta para ela.

| ROM | Acesso ao mapa | FPS | VBlanks | Ganho sobre controle |
| --- | --- | ---: | ---: | ---: |
| controle | Formato anterior do laboratório | 8,2788 | 15.466 | — |
| chunks-rom | Páginas lidas diretamente da ROM | 8,4997 | 15.064 | 2,67% |
| chunks-ram128 | Uma página copiada para uma janela em RAM | 8,3834 | 15.273 | 1,26% |

Medição no Genesis Plus GX, NTSC, em tempo emulado: FPS = frames × 60 / VBlanks. Não é uma medição no console. O ganho é pequeno; este teste não demonstrou uma grande aceleração do motor.

## Pré-processamento implementado

- 732 segmentos convertidos em registros de 32 bytes, com atributos de textura incorporados e referências preparadas.
- 341 páginas espaciais de 128 bytes, alinhadas a 128 bytes em ROM. Cada uma contém cabeçalho de 16 bytes, três registros de 32 bytes e 16 bytes reservados.
- Diretório de 237 regiões, com entradas de 8 bytes. A ordem original de percurso da BSP é preservada.
- Limites conservadores pré-calculados por página permitem rejeitar páginas fora da caixa de um teste de visão.
- 236 nós BSP convertidos de 28 para 32 bytes, com tipo de partição e resultados dos casos axiais pré-decodificados.
- 564 segmentos classificados previamente para o render: fechado, ignorável ou normal. Os demais mantêm cálculo dinâmico. Setores especiais, marcados e adjacências relevantes são tratados conservadoramente.
- 37 lados mutáveis usam 222 bytes de estado em RAM para deslocamento e texturas. As escritas passam por essa tabela; a leitura desses campos deixa de depender da SRAM.
- Render e visão dos monstros consomem as páginas compartilhadas. O payload antigo de SEGS foi removido, preservando a entrada de diretório para manter IDs de recursos.

As páginas ocupam 43.648 bytes em ROM e o diretório 1.896 bytes. O formato troca espaço por menos interpretação em execução. A variante RAM usa mais uma janela de 128 bytes alocada na memória do nível e uma referência para ela.

## Validação e limites

As duas variantes reproduziram exatamente os pixels das 66 amostras do viewport do controle, de 32 em 32 frames até o frame 2.112. Exclui a faixa superior de FPS e o HUD. Isso verifica a demo amostrada, não todas as situações possíveis do jogo. Os hashes e capturas estão no pacote.

Um desalinhamento da área de alocação alterava a fase da limitação de visão dos monstros, que na base depende do endereço do objeto. Alinhar essa área a 32 bytes restaurou a equivalência das 66 amostras, sem alterar a regra de IA.

Este passo converte o consumo de geometria do render e da visão. A topologia BSP, o algoritmo geral de render e os dados de compatibilidade de colisão e simulação ainda existem. Alturas de setores continuam dinâmicas. Não é uma conversão completa de todo o estado do jogo para RAM, nem um novo algoritmo de visibilidade.

O alinhamento não cria um cache no 68000. A janela usa cópia pela CPU, não DMA do VDP para RAM do 68000. Nesta demo, essa cópia foi menos eficiente do que ler as páginas na ROM.

## Código e reprodução

Branch: https://github.com/bollux78/MD-DOOM64KB/tree/exp-r128-e1m1-native-chunks

Conversor: `scripts/lab/r128-shareware/chunk_format.py`, chamado por `map_format_lab.py`. O script `build_maplab_fast.py` recebe um checkout R128 já preparado, SGDK, formato (`control`, `chunkrom` ou `chunk128`) e diretório de saída. Copie os conversores atualizados para o checkout preparado antes de executar. Faça os builds sequencialmente: cada execução restaura os arquivos-base de `maplab-template` e aplica o formato escolhido.

As opções efetivas de compilação, os relatórios de formato, hashes das ROMs e resultados brutos estão em `auditoria`. Os scripts de medição anexos registram os caminhos locais usados nesta execução e requerem ajuste de caminhos em outro ambiente.
