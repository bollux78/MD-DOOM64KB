# R128 E1M1 — Visibilidade e simplificação para render

Experimento de 18/11/2026 sobre os blocos nativos do teste anterior. Cinco ROMs com E1M1 shareware e benchmark no menu. Nenhuma substitui a R128 estável.

## Benchmark no emulador

Genesis Plus GX, NTSC, AI NORMAL, SHADOW OFF. Mesma demo, 2.134 frames; FPS = frames × 60 / VBlanks. São tempos emulados, não medição no console.

| ROM | VBlanks | FPS | Sobre controle original | Sobre blocos anteriores |
| --- | ---: | ---: | ---: | ---: |
| controle-original | 15.466 | 8,2788 | — | — |
| controle-chunks | 15.064 | 8,4997 | +2,67% | — |
| simplificada | 15.040 | 8,5133 | +2,83% | +0,16% |
| visibilidade | 14.966 | 8,5554 | +3,34% | +0,65% |
| combinada | 14.965 | 8,5560 | +3,35% | +0,66% |

A combinação economizou apenas um VBlank sobre visibilidade isolada. Não há evidência aqui de uma soma relevante dos ganhos. O ganho incremental sobre os blocos anteriores continua pequeno.

Para testar: abra a ROM, pressione Start e selecione `Benchmark E1M1`. Use as mesmas opções nas cinco versões. Start retorna do resultado ao menu. As ROMs também permitem jogar a E1M1; a progressão volta a ela.

## Visibilidade pré-calculada

O conversor divide o espaço do mapa em 950 células de 128 × 128 unidades. Para cada célula, gera bits de segmentos e regiões potencialmente visíveis. O runtime escolhe uma linha da tabela pela posição da câmera; fora da grade, desativa a rejeição pré-calculada.

Não são amostras pontuais de câmera. O descarte precisa valer para o retângulo inteiro da posição e o retângulo do segmento expandido em oito unidades. Há dois critérios: face traseira para a célula inteira, ou ocultação integral por uma parede permanentemente sólida. No segundo caso, testes de semiplanos verificam a sombra comum dos quatro cantos da célula. Portas e paredes de duas faces não entram como oclusores; não se congela o estado fechado de uma porta.

A compilação usa 302 paredes de uma face. As tabelas descartam aproximadamente 70,3% dos segmentos em média sobre todas as células, incluindo posições fora da área caminhável. Isso não representa a economia efetiva na demo: a BSP e os testes existentes já evitam boa parte deles.

Na variante combinada, a tabela ocupa 115.900 bytes em ROM. Na versão sem simplificação, 117.800 bytes. A nova seleção acrescenta uma referência em RAM; a tabela permanece na ROM.

A BSP mantém o percurso original. A rejeição evita geometria depois da coleta de sprites de cada região e evita projeções individuais antes de `R_AddLine`. Visitas a setores, projeção de sprites, colisão e visão dos monstros não usam essa nova tabela. Portanto, este teste ainda não elimina a travessia BSP nem implementa um render por portais.

## Simplificação

O render recebe uma lista contígua própria, com diretório de início e quantidade por região. Foram removidos 12 segmentos classificados de forma estática como sem efeito de render, reduzindo 732 para 720. O conversor tenta unir segmentos consecutivos colineares da mesma linha e lado, com continuidade exata de deslocamento de textura. Nenhum par da E1M1 passou nesses critérios: houve zero fusões.

Não foram unidas paredes de linhas distintas ou de regiões BSP distintas. Isso exigiria tratar a ordem do percurso, identificação das linhas e arredondamentos de textura. A redução geométrica obtida neste teste foi, portanto, limitada à retirada dos 12 segmentos ignoráveis.

A geometria de compatibilidade da visão continua nas páginas anteriores; a nova lista de render acrescenta cerca de 24 KB de ROM. As ROMs de visibilidade e combinada têm 3.276.800 bytes; as outras, 3.145.728 bytes. Não exigem mapper SSF.

## Validação

- Cada uma das três variantes reproduziu exatamente as 66 capturas do viewport do controle original: frames 32 a 2.112, de 32 em 32. A faixa superior de FPS e o HUD ficam fora do hash.
- A versão anterior de blocos também foi incluída nessa comparação.
- Um teste independente verificou 20.000 casos descartados pela tabela combinada. Sorteou posição dentro da célula e ponto do segmento; depois verificou diretamente face traseira ou interseção do raio com uma parede sólida. Zero descartes indevidos encontrados. Semente: 68000.
- A área de alocação permanece alinhada no mesmo endereço dos controles, preservando as fases da IA dependentes de endereço existentes na base.

Essas verificações cobrem a demo e os casos sorteados; não equivalem a validar todas as situações possíveis no console. Pair-V e a arma no viewport permanecem ativos.

## Código e auditoria

Branch: https://github.com/bollux78/MD-DOOM64KB/tree/exp-r128-e1m1-pvs-slim

Conversor novo: `scripts/lab/r128-shareware/visibility_format.py`. Teste de raios: `test_visibility_format.py`.

O build rápido usa o checkout R128 já preparado e os modos `chunkslim`, `chunkpvs` e `chunkall`. Copie os conversores atualizados para esse checkout. Execute os builds sequencialmente, pois eles restauram e modificam a mesma árvore preparada.

Em `auditoria` estão hashes das ROMs, relatórios de formato, resultados e scripts da execução. Os scripts de emulação anexos contêm os caminhos locais usados nesta execução; ajuste-os ao reproduzir em outro ambiente. Em `capturas` estão resultados e uma cena comum às cinco versões.
