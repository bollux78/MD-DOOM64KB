# Ferret Alpha 2 — engenharia reversa e reconstrução

**Continuação:** [Marco 2: geometria e paredes calculadas no 68000](PHASE2.md). O texto abaixo descreve o primeiro checkpoint.

Primeiro checkpoint reproduzível. ROM de referência fornecida pelo usuário; não está incluída. Não altera o motor D01 existente. Código experimental em `reconstruction/`; modelo independente em `tools/repack.py`.

## Resultado principal

A mesma Alpha 2 contém **dois caminhos gráficos** selecionados pela capacidade da SRAM:

1. **Sem SRAM utilizável / SRAM de 8 bits:** conversão de um buffer na WRAM e escrita direta pela CPU no VDP, com duplicação física das linhas. Não há DMA de pixels do cenário nesse caminho observado.
2. **SRAM de 16 bits:** a mesma conversão escreve 23.040 bytes em `0x20A600`, e quatro DMAs enviam o resultado para a VRAM. Existe uso real de SRAM nesta Alpha 2, embora o jogo também funcione sem ela.

Isso não contradiz “não requer SRAM”: SRAM é opcional, não inexistente. A versão com SRAM tem uma arquitetura de transferência diferente; não se deve estimar sua velocidade simplesmente multiplicando um fator de acesso à memória.

**Ainda não reconstruímos o motor 3D.** A ROM compilada deste checkpoint é uma prova estática do caminho gráfico: recebe uma cena capturada e implementa independentemente o reempacotamento e a saída no VDP. Não navega, não projeta paredes e não executa IA. Seu FPS não é comparável ao original.

## Referência e ferramentas

- Arquivo: `E1M1-alpha2.bin`, 1.441.792 bytes.
- SHA256: `47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267`.
- Genesis Plus GX, commit `2499cd3e3d1d8b7d0130d8b2825adb4cc608b2c0`, com patch de instrumentação preservado em `tools/`. Sem Sega CD. Sem overclock solicitado.
- Região NTSC verificada pelo core: oscilador 53.693.175 Hz; 262 linhas ×3420 master cycles =896.040 por quadro de vídeo (~59,92 Hz).
- Disassembler: GNU m68k-elf-objdump, modo `m68k:68000`. Há disassembly linear que pode confundir dados com código; os trechos documentados foram extraídos com endereços de entrada explícitos e confrontados com execução.
- Compilação da ROM parcial: GNU m68k as/ld/objcopy; não depende do renderer D01 nem do SGDK para rodar.
- BlastEm existe no ambiente anterior; não foi executado neste checkpoint. O antigo erro de RSP não foi resolvido aqui. MAME/Ghidra não foram necessários para as medições já realizadas. Não há validação em console desta ROM parcial.

## Métricas observadas

Jogador sem entrada de movimento no spawn de E1M1. Atores continuam ativos, podem atacar, disparar e alterar o HUD/paleta. Não é uma cena com simulação congelada. O início da janela curta é o frame de vídeo 380 do processo após sequência documentada de menus. “Spawn” aqui significa posição inicial do jogador, não o primeiro tic após carregar o mapa.

FPS medido pelos intervalos entre **DMAs da name table do viewport**, destino `0xE100`, 1152 palavras. A base do plano permanece `0xE000`; contar alterações do registrador 2 daria zero e seria um método errado para esta ROM.

| Configuração | Janela de vídeo | FPS por publicação | Tempo médio por imagem |
|---|---:|---:|---:|
| Sem SRAM | 300 quadros (~5 s) | 5,9107 |169,183 ms|
| SRAM de 8 bits, lane ímpar |300|5,9107|169,183 ms|
| SRAM de 16 bits |300|8,2554|121,133 ms|
| SRAM de 16 bits, giro à esquerda controlado |300|9,6350|103,788 ms|

Outra execução de 1500 quadros (~25 s), iniciada mais tarde, resultou em 5,7951 sem SRAM e 7,7410 com SRAM16. Ela inclui mais mudanças de estado dos inimigos e morte/dano; **não usar como equivalência de cena congelada**, nem misturar esses números com o benchmark de percurso D01. O valor histórico ~7,64 não foi reproduzido exatamente; ~7,74 apareceu nessa janela longa, sob as condições acima.

### Custos por etapa, janela curta, câmera parada

Tempos medidos entre entradas/saídas de funções, em master cycles emulados. **Inclusivos:** interrupções e DMA podem suspender a CPU dentro de uma rotina. Não são tempos puros de aritmética, e não somar categorias pai/filhas.

| Etapa | Sem SRAM |SRAM16|
|---|---:|---:|
| Lista de visibilidade / preparação de candidatos |7,706 ms|9,031 ms|
| Paredes |64,281 ms|71,906 ms|
| Sprites do mundo |3,413 ms|3,572 ms|
| Cena completa, incluindo as três etapas |75,423 ms|84,528 ms|
| Conversão + escrita direta ao VDP |59,748 ms|—|
| Conversão para buffer intermediário na SRAM |—|20,604 ms|

No perfil de instruções cobrado pelo emulador, a conversão direta ocupa 34,72% no caminho sem SRAM; a conversão para RAM ocupa 16,47% no caminho SRAM16. A instrução que dispara DMA em `0x07F420` responde por 6,41% nessa última execução: seu custo inclui suspensão de barramento, não é “lógica lenta” do programa. O laço de espera de VBlank em `0x0859DA–0x0859E4` representa 5,48% no teste sem SRAM e zero amostras no intervalo SRAM16. Esses percentuais são do somatório do profiler, não uma divisão perfeita de todo o tempo real: busca de opcode, refresh e entrada de interrupções não têm atribuição completa por esse método.

O cenário NÃO é invariável a 7 FPS nas condições medidas: há variação com ângulo e estado do jogo. Min/max, eventos e amostras por PC estão no pacote de resultados.

## Estado gráfico confirmado

- Saída 320×224; viewport 320×144, linhas 16–159.
- Buffer 11.520 bytes na WRAM: 80 tiras de quatro pixels ×72 linhas ×2 bytes. Isso equivale a 320×72 pixels físicos de 4 bpp; a quantidade de informação horizontal independente e os pares de cor ainda precisam de análise das texturas/scalers. Não confundir 320 pixels físicos com 320 raios independentes.
- Cada par de tiras fornece uma linha de tile de 8 pixels. A linha é emitida duas vezes; 72 linhas tornam-se 144 na VRAM. **Não depende de H-int nem de scroll por linha** nas capturas realizadas.
- VDP reg0=0x04: H-int desabilitada. VSRAM, registradores e dumps completos preservados.
- VRAM: dois bancos de 720 tiles, `0x0200–0x5BFF` e `0x5C00–0xB5FF` (23.040 bytes cada).
- A/B apontam para `0xE000`. Isso não prova duas camadas distintas de geometria: estão usando a mesma tabela nas capturas.
- Viewport na name table: começa em `0xE100`, 18 linhas, stride64. Seu DMA cobre 2304 bytes, incluindo padding de 24 entradas por linha. A publicação alterna os índices dos tiles via duas tabelas prontas em ROM (`0x11A1FC` e `0x11AD7C`), sem alterar reg2.
- SAT em `0xF000`; DMA de 56 palavras (112 bytes) nas amostras. Arma como sprites PAL2. Plano e HUD possuem dados distintos e prioridades que ainda precisam de descrição completa.
- Todos os 720 tiles visíveis do cenário usam PAL0. HUD principalmente PAL1 e pequenos trechos PAL3. PAL1/PAL3 quase duplicadas; organização detalhada já foi medida no handoff anterior. Não há evidência de quatro paletas simultâneas na geometria.
- No caminho CPU direto, mais de 100 mil escritas longas ao VDP ocorreram nas linhas ativas durante a janela curta; não é transferência restrita ao VBlank. Os dois bancos de tiles permitem escrever no banco oculto.
- Com SRAM16, quatro DMAs de pixels por publicação, total 11.520 palavras/23.040 bytes; comprimentos dos blocos variam com o orçamento disponível naquele VBlank. Os inícios dos DMAs foram registrados nas linhas reais 226–250, dentro do VBlank; os de pixels no teste parado, nas linhas 228/229/235/241. O arquivo `dma-scanlines.json` registra cada início; não é uma medição independente do término de cada DMA. Há também DMAs de atributos, SAT, CRAM e atualizações de HUD. Não confundir o total de todos os DMAs com somente o viewport.

## Endereços e fluxo confirmado

|Endereço|Observação|
|---|---|
|`0x0770B6`|Preparação/projeção de parede; transformações com MULS, shifts e DIVS/DIVU; coordenadas de vértices cacheadas. Não é livre de divisão na preparação.|
|`0x077402`|Interpreta stream de visibilidade; tokens de 16 bits; referências de parede com stride28 e de outro tipo com stride14; produz lista em WRAM `0xFF01E4`.|
|`0x07751E`|Percorre candidatos e chama o setup/desenho das paredes.|
|`0x06FF16–0x06FF3E`|Exemplo de avanço encadeado ADD/ADDX e leitura sequencial de registro de coluna de 8 bytes: ponteiro de destino e long de recorte. SP é reutilizado como ponteiro de escrita. Sem DIV neste trecho do laço.|
|`0x06F6E6`|Exemplo do caminho de sprites: posts, recorte e salto para scaler por tabela. Usa SP como destino e retorno em registrador.|
|`0x086C70`|Dispatcher da cena: chama `0x07E150`, `0x07E132` e termina em `0x07E140`.|
|`0x07E150 / 0x07E160`|Entrada/retorno do estágio da lista visível.|
|`0x07E132 / 0x07E13E`|Entrada/retorno do estágio de paredes.|
|`0x07E140 / 0x07E14E`|Entrada/retorno do estágio de sprites.|
|`0x07E0C6`|Inicializa 160 registros de coluna, passo8 bytes, altura72, a partir de tabela de offsets.|
|`0x07E368 / 0x07E3E8`|Entrada/retorno da conversão com saída CPU direta no VDP.|
|`0x07E3EA / 0x07E444`|Entrada/retorno da conversão com saída em RAM.|
|`0x08B6C8 / 0x08DD1C`|Chamadas ao conversor CPU direto, selecionando tilebase736 ou16.|
|`0x08D974`|Chamada ao conversor para RAM. Destino observado SRAM `0x20A600`.|
|`0x081CC0–0x081E22`|Trechos do teste dos lanes par/ímpar da SRAM; padrões 5A/A5/C3/3C. Não é mera leitura do cabeçalho.|
|`0x07F420`|Disparo de DMA; custo por instrução pode incluir stall completo do DMA.|
|`0x0859DA`|Polling do bit3 do status VDP, espera de VBlank.|

A origem do buffer observada é `0xFF42F2` sem SRAM e `0xFF4AF2` com SRAM16. A entrada do conversor recebe o ponteiro em stack+4 e o destino em stack+8. São parâmetros do binário específico, não constantes da futura engine.

### Fato versus interpretação

**Fatos:** formatos e bytes da saída conferidos; destinos reais; laços executados; SRAM16 versus8; tempos; pares de linhas duplicadas; lista de tokens executada; registro sequencial de coluna; instruções MUL/DIV no setup.

**Inferências fundamentadas:** o stream pré-processado reduz o percurso da cena; rotinas de interpolação/scalers foram escritas ou geradas para o 68000; wrappers e partes de jogo parecem C compilado. Sem símbolos/fontes não é possível provar a linguagem original.

**Ainda a decodificar:** formato completo do mapa/lista e seleção pela posição; escalas e empacotamento de todas as bordas; amostragem de textura e iluminação; visibilidade/ordem exata; custos separados de pisos/tetos/sky dentro das variantes de parede; demais resoluções/menus e caminho Sega CD. Não há reconstrução de navegação ou prova de equivalência de desempenho da engine.

## Reconstrução parcial validada

`tools/repack.py` é um modelo novo e curto do formato observado. Para a primeira transferência completa medida, seus 23.040 bytes coincidiram integralmente com o VDP original (sem SRAM e8bits) e com o buffer na SRAM (16bits). Checks em `repack-validation.json`.

`reconstruction/display.s` é uma ROM standalone escrita nesta investigação. Inicializa VDP, carrega o estado gráfico capturado de interface e monta o viewport a partir do buffer de tiras, com duplicação por software. Não inclui código de máquina extraído do executável Ferret. O uso de assets capturados não torna isso uma reconstrução 3D.

No mesmo Genesis Plus GX, ambos os bancos VRAM coincidiram byte a byte com o modelo. Comparação da imagem com `spawn-nosram/first-published/screen.png`: **zero pixels diferentes no viewport**, 16 pixels diferentes no rosto (x149–151,y168–175). A diferença no rosto pode ser decorrente de cache/estado de sprites entre a leitura de memória e a linha já exibida; causa ainda não confirmada. Não declarar imagem inteira perfeita.

## Reprodução

1. Obtenha uma cópia local da ROM cujo hash está acima.
2. Prepare Genesis Plus GX no commit informado. Aplique `git apply --ignore-space-change tools/genesis-plus-gx-instrumentation.patch` na raiz desse core; `make -f Makefile.libretro -j4`. O patch completo foi verificado com `git apply --check` sobre checkout limpo. Não altera ciclos das instruções para “acelerar” o jogo; usa contadores e cópias de diagnóstico. Os handlers SRAM mudam a disponibilidade dos lanes para os testes.
3. Instale Python, numpy e Pillow. Execute, a partir de qualquer diretório:

```bash
python tools/capture.py --rom /copia/local/E1M1-alpha2.bin \
 --core /copia/local/genesis_plus_gx_libretro.so --out /tmp/ferret-nosram --frames 300
python tools/capture.py --rom /copia/local/E1M1-alpha2.bin \
 --core /copia/local/genesis_plus_gx_libretro.so --out /tmp/ferret-sram16 --frames 300 --sram 0
python tools/capture.py --rom /copia/local/E1M1-alpha2.bin \
 --core /copia/local/genesis_plus_gx_libretro.so --out /tmp/ferret-sram8 --frames 300 --sram 2
python tools/repack.py /tmp/ferret-nosram
python reconstruction/build.py --capture /tmp/ferret-nosram \
 --prefix /toolchain/bin/m68k-elf- --out /tmp/ferret-proof
python tools/validate_proof.py --build /tmp/ferret-proof --core /copia/local/genesis_plus_gx_libretro.so
```

`capture.py --turn` segura libretro Left=6 somente durante a janela medida. O jogador permanece parado nas capturas sem essa opção. Há 60 quadros sem entrada entre `spawn` e `still-plus-60`. `first-published` espera uma conversão cuja entrada e saída foram ambas observadas, mais um quadro de vídeo; não captura uma conversão iniciada antes do trace. O repack rejeita buffers vazios.

Os dumps `.bin` usam ordem lógica big-endian de palavras. `cram.bin` usa bits de CRAM do hardware; `cram-packed.bin` conserva o formato interno de 9 bits do emulador. `vsram.bin` contém os 80 bytes endereçáveis; o array interno possui padding. Screenshot é 320×224, sem redimensionamento. Imagens de planos são decodificação do estado, sem composição final por prioridades/sprites; não substituem a captura final.

`analyze.py DIRETORIO_RESULTS` produz `measurements.json`. As funções de captura leem registradores do 68000; snapshots no fim do quadro de vídeo podem cair dentro do renderer, inclusive com USP/SP temporariamente apontando para pixels. Isso não indica automaticamente corrupção de stack.

## Continuação obrigatória

1. Decodificar o stream lido em `0x077402` e as estruturas em `0xFF1008–0xFF101C`, partindo de ROM local + snapshot WRAM. Não copiar o renderer D01 existente nem prometer equivalência com só um replay.
2. Extrair geometrias/texturas e parâmetros da vista do binário local com scripts; definir um formato independente que preserve as relações observadas.
3. Reconstruir projeção, geração da lista, recorte e scalers da cena inicial. Medir cada estágio; uma vista estática não valida navegação.
4. Reproduzir ao menos uma rotação controlada, comparar framebuffer antes de empacotar e a imagem final no mesmo frame. Só depois declarar engine equivalente e começar otimizações.
5. Medir baseline sem SRAM em todas as comparações; oferecer caminho opcional16bits somente quando o hardware permitir. Sem depender de SRAM16 para cartucho comum.
6. Submeter ROMs jogáveis ao console do usuário. Manter branch isolada e nenhuma substituição da main.

## Arquivos e persistência

- `tools/`: captura, profiler, análise, modelo e patch do emulador.
- `disassembly/`: trechos com endereços confirmados (não dump linear integral da ROM).
- `results/measurements.json`: resultados agregados com método e custos inclusivos.
- `artifacts/ferret-alpha2-checkpoint.zip`: dumps completos, PNGs, perfis/eventos, validação e ROM parcial. Não contém ROM original, WAD, ELF nem core compilado.
- Capturas curtas finais usam o core SHA256 `d16685dd9522af92b2ba31005ceabad6d46070946be8cf13a986f9ac52341afa`. As execuções longas foram feitas antes dos últimos hooks de captura; cada pasta registra seu core hash. Não tratar todos os hashes como um único binário.
