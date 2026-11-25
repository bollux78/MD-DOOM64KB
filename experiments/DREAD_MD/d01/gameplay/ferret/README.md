# C7, nove mapas, backend derivado da Ferret

Preparação de 25/11/2026. Base C7: `114a4147073c7c7ce3aa314d2ad93b57d2a15bae`, com a otimização de grades. Branch experimental `exp-ferret-episode-20261125`.

**Estado: compilação autorizada em 25/11/2026, com recuperação automática em andamento.** A primeira ROM Ferret excedeu 4 MiB; ainda não há ROM Ferret validada ou FPS medido. Não existe alegação de velocidade igual à Ferret ou de conclusão da validação do jogo.

## O que mudou

- Novo desenho de paredes, com projeção e recorte frontal/lateral, interpolação de profundidade inversa, seleção afim/perspectiva segundo o erro e escaladores diretos MOVE/DBRA derivados do modelo reconstruído da Ferret.
- Adaptação ao framebuffer da C7, em 160x72 ou 80x72 colunas/linhas lógicas. O modo de 80 colunas duplica os bytes de saída, com as mesmas coordenadas de textura e projeção vertical. Os modos 144 linhas e H32 ficam indisponíveis nesta experiência; o menu normaliza a seleção para os dois modos H40 suportados.
- Coordenadas U em unidades do WAD, textura com todas as colunas originais e pegamento vertical da C7. Uma porta de 128 unidades consulta a textura de 128 pixels uma vez. Não há ampliação de texturas C7 já reduzidas.
- Paredes, objetos e frames de inimigos são regenerados do WAD shareware em largura e altura originais. A conversão conserva o mapeamento de cores para a paleta Mega Drive da C7; isto não significa cores RGB originais do PC. O campo histórico `w2` de MapSprite passa a conter a largura inteira quando DREAD_SOURCE_PIXELS está ativo, e a projeção usa essa mesma convenção.
- Colunas de textura comprimidas sem perda e deduplicadas entre os nove mapas. O buffer de descompressão de 512 bytes e o cache de grupos de PVS (até 1408 bytes) reutilizam a arena ColRec de 1920 bytes, que este backend não usa. Dois ponteiros de cache são novo estado persistente. O modo de 80 colunas duplica a saída depois do mesmo escalador de bytes, compartilhando o código entre os dois modos.
- Segmentos de desenho com comprimento máximo de 256 unidades, para limitar os produtos de perspectiva. Linhas de colisão, setores, especiais e topologia BSP não são simplificados.
- Mantidos setores mutáveis, lógica, animações, armas, música, progressão, saída secreta e grades da C7. A integração desses sistemas está escrita, mas precisa dos testes reais de ROM abaixo.

**Distinção importante:** não é o executável Ferret transplantado. O desenho de paredes é uma implementação nova e adaptada a partir da reconstrução. A travessia de visibilidade continua BSP/PVS da C7, e o desenho/ordenamento de sprites e grades continua C7, agora com recursos de largura completa. As listas de visibilidade específicas da E1M1 Ferret não foram generalizadas para os nove mapas. Portanto não se deve chamar esta implementação de caminho inteiro e idêntico da Ferret.

O projeto não precisa da ROM Ferret para converter ou compilar. O WAD shareware é a fonte dos mapas e imagens.

## Verificações já executadas localmente

- Conversão de E1M1 a E1M9, dificuldade easy e quatro buckets de luz.
- Verificação de dimensões originais de todos os sprites convertidos e das texturas, limites dos segmentos e round-trip byte a byte do codec de todas as colunas utilizadas, incluindo padding vertical.
- 576 vistas no programa host (32 vistas x 2 modos x 9 mapas) com AddressSanitizer, sem erro de memória. PVS de teste conservador, todos visíveis; céu simplificado e atores estáticos. Isso verifica o caminho escalar de referência, não as rotinas 68000, a IA ou as portas em movimento.
- Verificação sintática com GCC 68000, incluindo os defines de combate. Sem linkedição e sem ROM.
- Sintaxe Python, Bash, estrutura YAML e `git diff --check` dos fontes (o patch externo conserva o whitespace do contexto original).

Os gráficos regenerados em bruto somaram 9.755.392 bytes de textura nos nove mapas, antes de compartilhar colunas e comprimir. O banco compartilhado comprimido com dicionários locais, compressão sem perda e seus ponteiros ficou em **1.361.053 bytes**. Sprites compartilhados: **484.122 bytes**. Há 554 escalas distintas para 2048 seletores; o deslocamento das instruções MOVE é também a tabela de offsets no 68000, evitando outra cópia das tabelas. Esses valores não são o tamanho final da ROM. O pipeline rejeita resultado acima de 4 MiB; SSF permanece desligado. O tamanho e a margem de RAM finais só serão conhecidos após a linkedição.

`preflight-20261125.json` registra a auditoria dos dados. O log `host-probe-20261125.txt` registra as 576 vistas. Nenhum número do tempo do computador host deve ser apresentado como FPS do Mega Drive.

## Pipeline reservado para “compilar”

Workflow `.github/workflows/dread-c7-optimization-matrix.yml`, somente `workflow_dispatch` nesta branch:

1. Compilar CONTROL, FERRET160 e FERRET80 separadamente, sempre a partir do WAD e sem reutilizar caches de imagens reduzidas.
2. Preparar Genesis Plus GX instrumentado, com commit fixado e patch incluído.
3. Verificar inicialização e imagem dos nove mapas, elevadores, paredes mascaradas, projéteis em grades, autoaim, saídas normais/secretas e final. Falhas são preservadas nos logs e impedem considerar o resultado validado.
4. Medir o mesmo DEMO3 E1M7 em MAME `genesis` NTSC, sem IA e com IA, mantendo VBlanks brutos. A conversão usa 59,9227434 Hz. O emulador pode repetir uma execução de benchmark que falhou; o primeiro log é preservado. Imagens diferentes são esperadas, pois resolução, escala e recursos mudaram; hashes iguais não são requisito nem prova de correção.
5. Consolidar ROMs, ELFs, imagens, logs e relatório comparativo. Em falha, conservar artefatos de diagnóstico; não promover a branch a estável.

Não foi disparado esse workflow nesta preparação. Possíveis erros de link, inicialização, RAM, desempenho, artefatos nas junções de paredes e regressões de gameplay ainda devem ser resolvidos e medidos quando a compilação for autorizada.

## Primeira compilação e recuperação

O controle compilou com o hash conhecido `bada47a0c028fb70f4f76ddbdd495ea1c0fd6b9797c101b54cb1b064ffc5ad56`. O teste de teleporte mantinha bench_req ativo e ignorava o movimento por controle; a preparação foi corrigida, e o teste passou na mesma ROM.

A primeira ROM Ferret linkou, mas foi rejeitada por exceder 4 MiB (5.373.952 bytes após alinhamento). Para preservar a resolução dos gráficos: dicionário por coluna quando menor que PackBits, compartilhamento dos escaladores entre 160/80 colunas, remoção dos escaladores legados de 144 linhas nesta variante e grupos de PVS comprimidos sem perda. Os conjuntos de visibilidade de referência foram decodificados e comparados byte a byte. A próxima compilação verificará o tamanho final e a execução.

## Validação do código nativo

A ROM de recuperação coube em 4 MiB e iniciou os nove mapas; mecanismos e progressão passaram. A medição ainda não terminou no limite inicial de 145 segundos emulados: o roteiro continuava avançando lentamente, e não estava travado. O profiler apontou 54% de uma cena no decodificador de colunas. Foram adicionados três slots no mesmo espaço de 512 bytes e decodificação de dicionários com deslocamentos constantes. Isso não altera pixels nem aumenta a resolução por interpolação.

O código nativo dos escaladores tinha DBRA com deslocamento 2, que alcançava o RTS; foi corrigido para 4. O novo verificador examina todas as linhas das rotinas no binário linkado, e não apenas o gerador ou a referência C. A distância mínima também passou a 41 em unidades de quarto de mapa: com 40, a profundidade inversa podia chegar a 65536, fora do quociente DIVU de 16 bits. Os testes e o benchmark serão repetidos após recompilar.
