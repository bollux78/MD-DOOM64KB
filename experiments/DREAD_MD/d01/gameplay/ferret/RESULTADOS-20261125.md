# C7 Ferret — nove mapas: resultado de 25/11/2026

**As três ROMs compilaram e o pipeline terminou com sucesso. O experimento Ferret ficou mais lento que a C7 de controle. A versão estável foi preservada.**

Abra as ROMs da pasta `ROMs/` em um emulador Mega Drive. Todas têm 4.194.304 bytes (4 MiB), sem SSF. FERRET160 começa com 160x72 colunas/linhas lógicas; FERRET80 começa com 80x72 e duplica a saída horizontal. As duas mostram uma área de 320x144 pixels físicos. Os modos 144 linhas/H32 não integram este experimento.

## Desempenho medido

Mesmo DEMO3 E1M7, 312 frames de jogo, MAME `genesis` NTSC a 59,9227434 Hz. O primeiro modo desliga a IA, mas mantém o roteiro; o segundo usa IA. São FPS de tempo emulado, não velocidade do computador que roda o emulador.

| Versão | FPS sem IA | FPS com IA | Velocidade sem IA versus controle |
|---|---:|---:|---:|
| CONTROL | 3.6487 | 3.3547 | +0.00% |
| FERRET160 | 1.3549 | 1.3514 | -62.87% |
| FERRET80 | 2.1323 | 2.0453 | -41.56% |

A redução de 160 para 80 colunas melhorou este experimento em 57,38% sem IA e 51,34% com IA. Ainda assim, nenhuma versão Ferret superou a C7 de controle. A comparação envolve ROMs completas: recursos mais detalhados, projeção e caminho de desenho diferentes. Não isola apenas a troca do algoritmo de renderização.

## O que foi implementado

Desenho de paredes derivado da reconstrução da Ferret, com coordenadas de textura em unidades corretas do WAD, sem duplicar a textura de uma porta de 128 unidades. Paredes, objetos e frames de inimigos foram extraídos novamente do WAD shareware em suas dimensões originais, mantendo a conversão para a paleta Mega Drive da C7. Nenhuma imagem reduzida da C7 foi ampliada para preencher os bancos novos.

A visibilidade ainda usa BSP/PVS da C7. O ordenamento de sprites e grades também continua integrado à C7. Portanto este é um port híbrido experimental, não o caminho completo e idêntico do executável Ferret original.

Para caber em 4 MiB, o novo conjunto usa colunas comprimidas sem perda, deduplicação entre mapas, escaladores compartilhados e PVS em grupos comprimidos. Isso preserva pixels, mas tem custo de CPU. Em uma amostra pontual da ROM final de 160 colunas, o decodificador de colunas consumiu aproximadamente 41% do tempo de CPU observado; não se trata de uma média de todo o roteiro. A adaptação atual não demonstrou ganho de FPS no Mega Drive.

## Validação concluída

- Inicialização e resposta aos controles nos nove mapas, nos dois modos Ferret.
- Testes automáticos de elevador, parede mascarada, teleporte, autoaim, projéteis em grade, saídas regulares/secretas e lógica de final/progressão.
- 39.888 linhas dos escaladores verificadas no código 68000 linkado, incluindo o salto DBRA e os destinos de escrita.
- 576 vistas da referência C com AddressSanitizer; dimensões das fontes e round-trip dos codecs conferidos. Os testes de computador não substituem os testes da ROM, que também foram executados.
- Dois benchmarks completos por ROM, com logs e contagens brutas de VBlanks.

São testes por cenas e fixtures automatizadas, não uma afirmação de que cada metro dos nove mapas foi jogado manualmente. As imagens são capturas de teste; alguns fixtures usam invulnerabilidade e posições de câmera preparadas.

## Arquivos

`ROMs/`: três ROMs. `ELFs/`: símbolos para estudo/profiler. `Dados/`: resultados e logs. `Imagens/`: capturas das verificações. `resultados.json`: dados consolidados e hashes. `SHA256SUMS.txt`: checksums das ROMs.

Pipeline: https://github.com/bollux78/MD-DOOM64KB/actions/runs/45612848296

Código compilado: https://github.com/bollux78/MD-DOOM64KB/commit/9f65f780b77b084079436586812604ff0d6d384a

Branch e instruções: https://github.com/bollux78/MD-DOOM64KB/tree/exp-ferret-episode-20261125/experiments/DREAD_MD/d01/gameplay/ferret
