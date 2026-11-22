# Handoff — aplicar as descobertas da Ferret à nossa engine Dread D01

## Missão autorizada pelo usuário

Voltar à ROM D01 completa, que já é relativamente rápida, e aplicar nela as melhorias sugeridas pela engenharia reversa da Ferret. Entregar ROM de controle, variantes isoladas e uma combinação das mudanças aprovadas para comparar desempenho e imagem. Não continuar usando o protótipo independente de2 FPS como base do jogo.

O usuário pediu este handoff para outro agente dar continuidade. Não é uma solicitação para abandonar a investigação: ela vira referência técnica da otimização. A autorização para criar/compilar/testar ROMs experimentais e preservar tudo no GitHub já foi dada. Não precisa pedir novamente para começar os testes.

## Repositório, branches e bases exatas

Repositório: https://github.com/bollux78/MD-DOOM64KB

|Referência|Branch / commit|Uso|
|---|---|---|
|D01 completo corrigido, última base verificada neste chat|`exp-werk-dread-exato-input-vblank` / `42f17f26b1e3187ad7995799891cb50bd090e66c`|Ponto de partida do trabalho no jogo|
|Base de Cláudio e handoff|`exp-dread-md-d01-claudio` / `2e11bb8dc8ada06c0f9290858c745d0df7cdd5f6`|Histórico; inclui a base do laço de colunas `0681cb0`|
|Investigação Ferret, até a v03 navegável|`research-ferret-alpha2-reconstruction` / `56813b088369cee0ccc23257abd04e704c0a277f`|Referência de dados, testes e mecanismos; não é a base de desempenho do jogo|

Os três heads acima foram consultados no GitHub ao preparar este handoff. Se aparecer uma base D01 posterior, inspecionar as diferenças e preservar as correções antes de escolher o controle. Não usar apenas o nome “mais recente” sem registrar SHA/flags/hashes.

Criar uma branch experimental própria a partir da base D01 escolhida, por exemplo `exp-dread-ferret-optimizations`. Não alterar main nem a branch de Cláudio. Buscar a branch de pesquisa para consultar seus arquivos; não fazer merge integral da pesquisa na engine do jogo.

Links essenciais:

- [Handoff da correção de imagem e input no VBlank](https://github.com/bollux78/MD-DOOM64KB/blob/42f17f26b1e3187ad7995799891cb50bd090e66c/experiments/DREAD_MD/d01/HANDOFF-CLAUDIO-EXATO-VBLANK.md)
- [Pesquisa: pipeline, SRAM e endereços](https://github.com/bollux78/MD-DOOM64KB/blob/56813b088369cee0ccc23257abd04e704c0a277f/research/ferret-alpha2/README.md)
- [Pesquisa: formatos, projeção e scalers](https://github.com/bollux78/MD-DOOM64KB/blob/56813b088369cee0ccc23257abd04e704c0a277f/research/ferret-alpha2/PHASE2.md)
- [Pesquisa: seleção espacial e navegação](https://github.com/bollux78/MD-DOOM64KB/blob/56813b088369cee0ccc23257abd04e704c0a277f/research/ferret-alpha2/PHASE3-NAVEGAVEL.md)

## O que preservar na D01

O controle deve manter os mapas shareware E1M1–E1M9, menus, música, HUD, arma, atores, tiro e clipping dos sprites pelas janelas das paredes. Variantes menores de E1M1 podem acelerar a investigação, mas precisam ter controle próprio idêntico e não substituem a entrega final integrada.

Preservar especialmente:

- Amostragem vertical exata em16.16, incluindo origem fracionária, arredondamento e caminho mascarado. Uma aproximação anterior produzia distorções em ângulos fechados. Recuperar FPS removendo a correção não é uma otimização equivalente.
- Registros sequenciais de coluna e saltos para scalers que já existem. Não apresentar sua mera presença como novidade.
- Orçamento de VBlank compartilhado entre framebuffer, HUD e arma; nenhuma publicação antes de terminar todas as transferências necessárias.
- Correção da tela preta nas trocas H40/H32 e linhas/colunas. Testar todos os modos suportados, ou delimitar claramente uma variante experimental sem remover as opções do controle.
- Leitura de controle no VBlank quando usada para conter os glitches de VSRAM. Não reintroduzir JOY_update bloqueando H-int na área visível sem medir imagem.
- Funcionamento sem SRAM e sem Sega CD. Nenhuma dependência nova silenciosa de SRAM16.

Uma paleta no cenário é o controle inicial. Não incluir o experimento multipaleta neste pacote de otimizações: ele tem outro custo, outro resultado visual e não foi aprovado como substituto. Não trocar simultaneamente as cores e a arquitetura do render.

## O que realmente aprendemos na Ferret

Referência local: `E1M1-alpha2.bin`, tamanho1.441.792, SHA256 `47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267`. A ROM original não está publicada na pesquisa. Scripts operam sobre uma cópia local do usuário.

### Fatos confirmados

1. **Visibilidade pré-processada por célula.** A BSP localiza a posição; um stream de tokens produz uma lista ordenada de paredes e referências de setores/atores. Há runs comuns para reduzir repetição. No binário examinado:430 nós,431 folhas/células,642 slots de parede,32.460 referências quando todas as condições de visibilidade são habilitadas. As células não são os setores Doom do WAD.
2. **Registros sequenciais de coluna.** Um exemplo executado lê8 bytes seguidos: ponteiro do destino e recorte empacotado. As bordas avançam por ADD/ADDX em registradores. A preparação das paredes continua contendo MULS/DIVS/DIVU; não chamar o frame de “sem divisões”.
3. **Scalers desenrolados com entrada ajustada ao recorte.** A tabela em `06D4AE` seleciona por bucket de escala. A rotina de pixel usa um deslocamento de textura já preparado, com retorno indireto. A Ferret usa SP como destino; em acesso byte pós-incrementado, A7 avança2 bytes automaticamente.
4. **Buffer intercalado deliberadamente.** Endereço do pixel lógico: `(x/2)*144+(x&1)+y*2`. Cada byte representa um par de pixels físicos. O formato combina com o incremento especial de SP e com a conversão para tiles.
5. **Duplicação vertical física.**72 linhas no buffer tornam-se144 ao repetir as escritas, sem H-int de duplicação. São11.520 bytes de entrada e23.040 bytes de tiles. Dois bancos VRAM,720 tiles cada, em0200–5BFF e5C00–B5FF.
6. **Dois caminhos conforme a SRAM.** Sem SRAM utilizável, conversão/escrita CPU direta no banco oculto do VDP. Com SRAM16, conversão em20A600 e quatro DMAs dos pixels. A SRAM8 testada cai no caminho sem SRAM. SRAM opcional não significa SRAM nunca utilizada.
7. **Uma paleta no viewport observado.** PAL0 para o cenário; PAL2 para a arma em sprites; HUD principalmente PAL1 e alguns tiles PAL3. PAL1/PAL3 quase duplicadas. Não usar a captura de64 slots CRAM como prova de64 cores no cenário.
8. **Escolha entre kernels de textura linear e de perspectiva.** O setup possui um teste de erro. Não reduzir isso à afirmação de que todas as paredes usam somente uma soma sem correção. Um caso precisou preservar os flags N/V da comparação16-bit para escolher o kernel correto.

Endereços/trechos comentados estão em `research/ferret-alpha2/disassembly/`; os modelos independentes estão em `reconstruction/visibility.py`, `projection.py` e `raster.py`. Eles ajudam a especificar o algoritmo; não são implementações rápidas para copiar para o jogo.

### Validações e seus limites

-32 listas de visibilidade iguais às capturadas,4.032 transformações e655 despachos de desenho conferidos.
-239.568 comparações dos bytes escritos pelo modelo de paredes sem divergência. Isso era uma comparação mascarada, não prova de imagem completa.
-A v02 prendia a câmera ao stream da célula29, inadequado para as coordenadas renderizadas. A consulta espacial retorna131 nessa posição. A v03 corrigiu a seleção e preenchia a imagem inteira nos32 ângulos do teste do spawn. Não transpor IDs/índices desses dados para a D01, que tem outra conversão.
-O protótipo v03 é navegável, mas continua C escalar, sem atores/portas funcionais, com interface estática, e mede cerca de2,07 FPS. **Não é uma otimização bem-sucedida do jogo.** Não substituir a D01 por ele nem anunciar equivalência com a Ferret.
-Nem toda a física, todas as variantes, todas as condições do stream ou todas as vistas foram verificadas. Não tratar o protótipo como especificação completa do original.

## Trabalho a executar, por ordem

### 0. Estabelecer o controle

Ler os AGENTS/handoffs do checkout. Compilar o D01 com `tools/build_exact_tests.sh` e usar os flags exatamente como o script os define. Escolher e registrar um controle corrigido, preferencialmente com input no VBlank para testar a apresentação estável. Fazer um build limpo com o mesmo toolchain de todas as variantes.

Perfilar esse controle. Separar setup de paredes, avanço/desenho de colunas, percurso da cena, sprites, transferências, esperas e interrupções. Não transportar percentuais históricos da Ferret como se fossem os do nosso motor.

### 1. Reduzir o custo do laço de colunas

Comparar o assembly gerado/atual em `src/colasm.s` com os exemplos de ADD/ADDX da pesquisa. A D01 já tem registros de12 bytes por coluna; avaliar empacotamento, ponteiros incrementais e manutenção das bordas em registradores sem recarregar vetores/estado global. Não exigir8 bytes se isso eliminar informação necessária aos quatro modos.

Prioridade: reduzir leituras, preparação repetida, chamadas e cálculo de origem/recorte **sem alterar os resultados16.16**. Avaliar parâmetros pré-calculados por parte/trecho e entrada direta nos scalers. Uma recorrência candidata precisa reproduzir a multiplicação/rounding atual nos casos de recorte e extremos; validar antes de removê-la. Não repetir o erro de6c8c512.

Entregar essa mudança isolada como variante A, antes de acrescentar outro caminho gráfico.

### 2. Comandos de visibilidade pré-processados no conversor

Avaliar lista/stream por célula no conversor D01, usando a geometria e os índices dela, conservando PVS e ordem front-to-back. Não copiar os índices extraídos da ROM Ferret e não calcular uma lista apenas para o spawn.

Medir custo ROM: referências compartilhadas de16 bits e runs comuns podem ser muito menores que listas com ponteiros/estruturas duplicadas. Incluir memória temporária e tempo do conversor no relatório. O exemplo Ferret de32.460 refs ocupa cerca de65 KiB somente para índices; isso não é uma estimativa automática para nossos nove mapas.

Uma ordem calculada no centro de uma célula não está automaticamente provada para todos os pontos dela. Verificar as condições dos planos, posições perto das fronteiras, portas e áreas de degraus. Manter fallback BSP onde não houver ordem conservadora garantida.

**Sprites:** o D01 captura janelas de recorte por subsetor. A lista não pode eliminar esses eventos. Incluir marcadores/comandos para preservar o momento do snapshot e a ordem dos atores, ou adaptar o clipping com validação explícita. Comparar cenas com monstros parcialmente atrás das paredes/portas.

Entregar como variante B isolada. Se não ficar correta a tempo, entregar A com controle e registrar B como pendência; não esconder glitches em uma “ALL”.

### 3. Alternativa de buffer/apresentação sem H-int

Experimentar somente como variante C independente, após contabilizar CPU, RAM, VRAM e bytes de transferência. A Ferret provar que funciona não prova que esse caminho é mais rápido no nosso motor.

O controle usa uma apresentação que economiza pixels/transferência ao duplicar linhas por VSRAM. O caminho Ferret expande para23.040 bytes e pode custar mais em CPU/barramento do que as interrupções que elimina. A conversão/escrita direta custou aproximadamente60 ms na referência sem SRAM. Avaliar antes de propor como solução padrão.

Possibilidades: buffer intercalado compatível com os scalers, expansão em WRAM seguida de DMA, ou escrita direta no banco oculto. Verificar se cabe um scratch de23 KiB com os buffers existentes, atores e stack real; não concluir que cabe apenas porque o linker passou. Validar máximos de DMA, espera, publicação, pausas e modos.

No caminho com tabela de atributos pronta, reutilizar/alternar dados estáticos em ROM quando possível. A Ferret atualiza o conteúdo da name table; reg2 permanece fixo. A implementação não precisa reproduzir a mesma escolha de registrador se outro arranjo for correto e mais barato.

SRAM16 fica **opcional e separada**, se investigada. O episódio D01 ultrapassa2 MiB e a janela SRAM pode sobrepor ROM; usar uma ROM pequena de E1M1 e documentar o mapeamento. Não pressupor SRAM16 física no Everdrive X7 do usuário. O build principal continua funcionando sem ela.

### 4. Combinações e integração

Somente combinar variantes corretas e medidas. Produzir ALL com A+B ou A+C etc, especificando os componentes. Confirmar se os ganhos se somam; não somar percentuais teoricamente. Se C perder desempenho, preservar o controle/ganhadoras e explicar o resultado.

Integrar a melhor alternativa no episódio completo, mantendo menus, conteúdo e controles. A aprovação visual final é do usuário no console; o agente deve fazer todos os testes disponíveis antes de entregar.

## Benchmarks: condições que não podem ser misturadas

|Referência histórica|Resultado|Condição|
|---|---:|---|
|D01 corrigido 01|~3,58 FPS|Percurso E1M1,312 imagens, passo fixo|
|D01 corrigido rápido02|~3,62 FPS|Mesmo percurso e imagem amostrada|
|D01 corrigido input VBlank03|~3,57 FPS|Mesmo percurso, diferença de apresentação/input|
|Giro do03|~5,98 FPS|1500 quadros de vídeo, cadência afeta a trajetória angular|
|Ferret sem SRAM, parado|~5,91 FPS|Janela curta, atores ativos|
|Ferret SRAM16, parado|~8,26 FPS|Janela curta, outro caminho gráfico|

Esses números são referências históricas, não metas garantidas nem substitutos de medir o novo controle.

O run44763244095 realmente marcou4,55 FPS, mas fazia161 imagens, outro viewport e movimento dependente do tempo do quadro. O passo fixo foi introduzido por `ccfa0b06f93014450423e1b9f8da91db5c8792fc`. Não comparar seus4,55 diretamente aos3,57 atuais.

Para cada variante nova:

1. Mesmo emulador, versão, região, toolchain e flags; mesma resolução, viewport, paleta, música, atores e limites. Medir inicialmente H40 linhas, largura total, sem SRAM/Sega CD e sem limitador.
2. Usar o benchmark do menu, com passo fixo e312 imagens. Bench comum não executa IA ativa como bench_req2; não misturar os dois. Confirmar o código do benchmark na base escolhida.
3. Comparar framebuffers nas imagens1,20,45,70,95,120,150,250,312. Para mudanças que devem ser exatas, exigir igualdade de bytes. Se o layout mudar, decodificar para índices de cor/coordenadas comuns antes de comparar.
4. Acrescentar vistas em ângulos fechados, portas, escadarias e oclusão de sprites; nove hashes não provam tudo. Testar E1M2 e E1M8, depois o episódio e modos de detalhe.
5. Usar giro/fixed views como medida complementar, indicando se a trajetória depende do FPS. Separar custo de CPU e tempo entre apresentações.
6. **Eventos de apresentação dependem da arquitetura.** Na Ferret, contar mudanças de reg2 dá zero; a apresentação foi identificada pelo DMA dos atributos emE100. Ajustar o método se a variante mudar o flip. Não confundir60 Hz do VDP com FPS do jogo.
7. Não chamar somente o ponto que dispara DMA de “lógica de CPU”: o profiler pode cobrar nele o stall do barramento. Tempos entre entradas/saídas de rotina incluem interrupções e transferências.

## Entrega esperada ao usuário

Um ZIP com `00-Controle.bin`, `01-Colunas.bin`, `02-Visibilidade.bin`, `03-Apresentacao.bin` quando implementadas e corretas, e `04-ALL.bin` com a combinação relevante. Não publicar variantes inexistentes sob esses nomes; adaptar a numeração ao escopo real. Incluir:

- FPS e ms/imagem por cena, VBlanks, número de imagens e condições;
- hashes de ROM e comparações de imagem;
- RAM/stack/ROM/VRAM e volume transferido quando houver mudança de layout;
- screenshots das mesmas vistas, sem alterações cosméticas simultâneas;
- commit/branch, comandos de reprodução e limitações específicas.

Preferir link direto ao ZIP e às ROMs no GitHub, que o usuário quer para histórico/auditabilidade. Não publicar WAD, ELF ou a ROM original Ferret. Não enviar mensagem ao Cláudio ou terceiros: o usuário compartilha o link do handoff.

## Ambiente anterior, se ainda existir

Raiz `/workspace/scratch/908cd7aa2f56`:

- `dread-reference`: D01 corrigido, HEAD local61c6e8f, mesma árvore do publicado42f17f2.
- `dread-reference-builds/`, `dread-reference-delivery/`: resultados e ROMs corrigidas.
- `ferret-research/research/ferret-alpha2/`: pesquisa e modelos.
- `r128-local-sgdk`: toolchain/SGDK local.
- `pixel4-control/scripts/doom1.wad`: WAD shareware local, não publicar.
- `upload/E1M1-alpha2.bin`: referência local, não publicar.
- `dread-sram-emu/genesis_plus_gx_libretro.so`: core instrumentado; os patches estão publicados na pesquisa.

Esses diretórios são conveniência, não fonte de verdade persistente. Recuperar o código pelos commits publicados. Os commits criados pela API GitHub podem não existir como objetos no checkout local; fazer fetch antes de usar seus SHAs em git. Não misturar o patch multipaleta WIP com este trabalho.

**Primeira ação do próximo agente:** compilar e medir o D01 de controle, identificar o custo do laço de colunas e implementar a variante A mantendo a imagem exata. Depois investigar a lista de comandos por célula. A migração completa do pipeline Ferret não é pré-requisito para entregar um primeiro teste útil.
