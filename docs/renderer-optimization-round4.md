# DOOM MD — Rodada 4: tamanho do cache de colunas

## Referência comprovada

O melhor resultado da DEMO3 a 7,67 MHz (BlastEm divisor 7),
NTSC, **sem VSync** e com 2.134 quadros é **9,05 FPS**,
mínimo 4,1, máximo 14,8, tempo 235,77 s, com **Fast DIVU + Color LUT +
cache de 8 entradas**. O usuário confirmou em uma instância isolada.

A rodada 4 **não altera** o motor geométrico, a resolução 38×28,
as texturas, o SGDK compartilhado nem a ROM funcional. Não utiliza
SRAM externa; o objetivo é localizar primeiro o melhor custo/benefício
dentro dos 64 KB principais.

## A arquitetura testada

Cache de **colunas de texturas compostas** em `R_ComposeColumn()`.
As texturas simples não passam por esse cache. A pesquisa da
rodada 3 mostrou um ganho com 8 slots sobre os 4 originais.

Cada slot ocupa 128 bytes para pixels e 2 bytes para a tag.
Mantém-se o algoritmo de hashing e o limite **fixo de quatro sondagens**
por procura, assim a comparação mede o aumento de capacidade
sem ampliar o limite de busca. O tamanho é potência de dois.

| Slots | Bytes cache + tags | Diferença vs. 8 | Nome para benchmark |
|---:|---:|---:|---|
| 8 | 1.040 | — | `doom-md-r4-cache8-perf.bin` |
| 16 | 2.080 | +1.040 | `doom-md-r4-cache16-perf.bin` |
| 32 | 4.160 | +3.120 | `doom-md-r4-cache32-perf.bin` |
| 64 | 8.320 | +7.280 | `doom-md-r4-cache64-perf.bin` |

## Como coletar desempenho E dados do cache

A mesma execução do workflow gera **8 ROMs** em um único ZIP:

- As quatro ROMs `*-perf.bin` têm **contadores desativados** e servem
  para comparar FPS em condições justas.
- As quatro ROMs `*-stats.bin` têm contadores ativos; a tela final
  mostra `CACHE SLOTS`, `CACHE HITS`, `CACHE MISSES`,
  `CACHE EVICTIONS` e `HIT RATE %`.
  **O FPS da ROM stats não serve para comparar desempenho**, pois
  as incrementações de 32 bits têm custo no 68000.

O que significam os dados:

- Hit: tag da coluna solicitada já coincide no cache.
- Miss: coluna precisa ser recomposta e copiada para o cache.
- Eviction: um miss sobrescreve uma tag anterior não vazia.
- O contador de substituição é um subconjunto dos misses; misses
  iniciais em slots vazios não são substituições.
- Estatísticas reinicializadas no início do TIMEDEMO. A memória do
  cache não é invalidada, reproduzindo o comportamento da ROM normal.
- Estes números não são estatísticas gerais de todas as texturas do
  Doom, mas **apenas das colunas compostas**.

## Como executar

1. Inicie seu runner `x360-linux`.
2. Em GitHub Actions, execute manualmente
   [Renderer optimization - Round 4 (cache sizes)](https://github.com/bollux78/MD-DOOM64KB/actions/workflows/renderer-optimization-round4.yml)
   na branch `main`; o workflow faz checkout de
   `exp/68k-renderer-round4`.
3. Baixe o único artefato `doom-md-renderer-round4-cache-lab.zip`.
   Confira os 8 arquivos `.bin` e `SHA256SUMS`.
4. Faça primeiro os quatro testes `perf` na DEMO3, BlastEm,
   divisor 7, uma instância por vez, relógio normal, 2.134 quadros.
   Registre FPS médio/mínimo/máximo e tempo total.
5. Execute as ROMs `stats` e envie capturas das telas finais dos
   quatro tamanhos. Ignore seu FPS; compare a taxa de acertos e
   o número de recomposições evitadas.
6. Verifique visualmente texturas compostas e sprites. Não promova
   a alteração se houver regressão gráfica.
7. Se uma ROM falhar na compilação por falta de RAM, pode haver um
   artefato parcial com as ROMs produzidas antes da falha. Veja logs.

**Critério de escolha:** maior ganho de FPS repetível e visual
idêntico, com o menor custo em RAM. Se 16/32/64 não superarem o
cache de 8, retornar ao cache de 8.

## Identificação automática das ROMs

Ao gerar cada variante, o workflow define exatamente um identificador
`DOOM_BUILD_ID`, por exemplo `doom-md-r4-cache8-perf`. O script
`scripts/set_rom_identity.py` prepara duas partes no checkout de Doom:

- `src/rom_header.c`: os campos *domestic title* e *overseas title*
  do cabeçalho do cartucho recebem esse identificador.
- `src/doom_build_identity.h`: a tela final da DEMO3 mostra exatamente
  o mesmo identificador, no lugar de `DOOM MD - TIMEDEMO 3.0`.

O arquivo também é salvo como `DOOM_BUILD_ID.bin`. O workflow confere
automaticamente os títulos nos offsets `0x120` e `0x150` da ROM
gerada; não aceita um arquivo cujo cabeçalho permaneça `SAMPLE PROGRAM`.

O processo usa `src/rom_header.c`, ponto oficial de personalização
do SGDK, sem modificar nenhum arquivo da toolchain compartilhada.

**Aplicável aos novos builds**: arquivos ZIP produzidos por execuções
anteriores não mudam. É necessário executar novamente o workflow para
receber ROMs com os novos identificadores no cabeçalho e na DEMO3.

## Etapa posterior

Só depois de escolher o tamanho do cache interno, investigar SRAM
externa do EverDrive como área para dados de acesso esporádico.
Não mover o framebuffer ou tabelas de cores do caminho crítico.
