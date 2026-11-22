# Marco 2 — visibilidade, projeção e paredes calculadas no 68000

**Atualização:** a [v03 navegável](PHASE3-NAVEGAVEL.md) substitui as poses pela consulta espacial e por movimento com colisão.

Esta etapa substitui o uso de uma cena pronta para o viewport por código novo que calcula paredes a partir da geometria. Não altera o D01 nem a main. Ainda é uma reconstrução parcial e não alcançou equivalência visual completa ou de desempenho.

## O que mudou

- `reconstruction/visibility.py`: intérprete independente do stream de visibilidade.
- `reconstruction/projection.py`: transformação 16-bit, recorte pelo frustum/near plane, projeção, escala e preparação de coordenada de textura.
- `reconstruction/raster.py`: modelo independente das variantes de parede, clipping de colunas, cores, texturas e céu.
- `scene.c`: versão C do modelo escalar, compilável para host e 68000. DIVS/DIVU nativos no 68k; divisão longa construída com dois DIVU quando o quociente excede 16 bits.
- `boot.s`, `runtime.c`, `scene.ld`: ROM standalone, sem usar o motor D01 ou seu frontend. A interface estática é carregada de um dump local, mas **os dois bancos do framebuffer capturado são zerados antes de gerar a ROM**. O framebuffer novo é criado do zero pela geometria a cada imagem.
- `tools/export_scene.py`: extrai vértices, materiais, coordenadas de textura, lista do setor do spawn, offsets numéricos dos scalers e panorama do céu. Não lê pixels de framebuffer como entrada para o render.

## Captura e validação

Foram capturadas 16 execuções no spawn sem movimento e outras 16 com giro à esquerda. SRAM bloqueada e sem Sega CD. Os hooks registram memória no início/fim da lista, após as paredes e os registradores antes da projeção e do despacho dos kernels.

| Verificação | Amostras | Resultado |
|---|---:|---|
| Lista ordenada de candidatos |32 listas ×126 paredes|Igual ao original|
| Transformação de paredes |4.032|Igual nos quatro componentes de vértices|
| Despachos de desenho|655|X, largura, escalas, passo, textura, escolha linear/perspectiva e parâmetros iguais|
| Aceitação/rejeição dos candidatos|4.032|Igual à presença/ausência do despacho observado|
| Bytes efetivamente escritos pelo modelo de paredes|239.568, em 32 estados|Zero divergências com os bytes correspondentes após as paredes originais|
| C do host versus modelo Python|16 poses diagnósticas|Framebuffer de 11.520 bytes igual em cada pose|
| C no 68000 versus C no host|Spawn e pose3, que inclui o caminho de perspectiva|Framebuffer igual, zero bytes diferentes|

**A comparação de bytes escritos não equivale a uma imagem completa igual.** Há regiões não preenchidas pelo modelo: 1.357 bytes no spawn e regiões maiores em alguns ângulos. No spawn, 116–147 bytes nessas regiões diferem dos dados remanescentes no buffer original; no giro, a diferença pode ser muito maior. Ainda não está demonstrada a origem de todas essas regiões. Não atribuir automaticamente toda diferença aos inimigos. Não usar os buffers originais anteriores para escondê-las.

As amostras de câmera parada exercitaram variantes 0,2,6,7,11. O giro acrescentou 4,5,15,17. O modelo contém uma interpretação das 18 variantes, mas as demais ainda não foram verificadas por execução nesta etapa.

## Formatos decodificados

### Stream de visibilidade

Entrada real do spawn observada: `0x0CC448`. Ponteiros de tabelas no estado capturado:

|Global WRAM|Ponteiro observado|Função|
|---|---|---|
|`FF1008`|`E0FF96BE`|Registros de setor de 14 bytes|
|`FF100C`|`0D01F6`|Árvore espacial, ainda a decodificar completamente|
|`FF1010`|`0BBEF8`|Runs comuns de tokens|
|`FF1014`|`0D41F6`|Registros de parede de 28 bytes|
|`FF1018`|`E0FF7606`|Vértices e cache de transformação, stride8|
|`FF101C`|`E0FF82AE`|Dados de coordenada de textura|

Tokens de 16 bits:

- `0000`: fim.
- `0001–7FFF`: referência a um run comum, em palavras relativas à tabela. O run termina no endereço indicado; seu começo é encontrado varrendo para trás até o separador zero. A implementação original mantém um retorno, sem pilha geral de recursão.
- `8000–BFFF`: referência de parede, índice `token-8000`, stride28. Emite `(flag16, ponteiro32)` na lista `FF01E4`.
- `C000–EFFF`: referência de setor, índice `token-C000`, stride14. Atualiza stamp e recolhe a lista ligada de atores ainda não marcados.
- `F000–FFFF`: grupo condicional. `flag=token-F000`; testa o byte em `FF1B84+(flag>>1)`. Quando desativado, pula até outro cabeçalho de grupo ou o fim.

O significado de cada condição de grupo e a geração da tabela de bits ainda não foram reconstruídos. A lista está validada para o estado do setor inicial, não para todos os setores do mapa. O interpretador Python conserva o comportamento dos runs encontrados; o caso de esgotamento do orçamento de atores ainda precisa reproduzir a saída antecipada exata do assembly.

### Parede, 28 bytes

|Offset|Campo observado|
|---:|---|
|0|Ponteiro da textura superior/sólida|
|4|Ponteiro da textura inferior|
|8,10|Offsets de dois vértices na tabela, não índices crus|
|12,13|Bytes de pares de cores para teto/chão|
|14,15|Variantes do desenho, selecionadas pelo bit0 do flag da lista|
|16,18,20,22|Quatro alturas usadas pelas variantes|
|24|Offset do registro de coordenadas de textura|
|26|Reservado/não interpretado nesta etapa|

Vértice: x16,y16,cache lateral16,cache profundidade16. Para transformar, coordenadas de mapa são multiplicadas por8 em 16 bits, subtrai-se a câmera e usam-se MULS com sin/cos Q14; os resultados selecionam a metade alta depois de shift2. É preciso preservar wrapping de 16/32 bits e truncamento de DIVS. Usar floats ou divisões com floor altera pixels de recorte.

O núcleo de projeção usa focal80 para 160 colunas lógicas. Recorta os dois lados e o near plane antes de projetar. O near observado é81, ou82 na variante4. Calcula escala `0x500000/profundidade`, interpola escala e escolhe entre textura linear e um caminho de perspectiva. Essa escolha não é simplesmente “corrigir a cada16 colunas”: há um teste de erro no setup que seleciona um kernel diferente.

Uma particularidade importante foi reproduzida: BGE após SUB.W observa N==V. Substituir a sequência por `abs(int16(a-b))` escolheu um kernel diferente em uma das amostras. A comparação assinada e o wrapping foram preservados.

### Layout e scalers

- O buffer é intercalado por pares de colunas: `offset=(x/2)*144+(x&1)+y*2`.
- Cada byte representa o par de pixels de uma coluna lógica. O 68000 incrementa A7 por2 em acesso byte com pós-incremento, e a Ferret explora isso usando SP como destino. Portanto os scalers escrevem naturalmente nesse layout, sem uma instrução ADD por pixel.
- A interpretação anterior como tiras físicas de quatro pixels continua válida, mas agora o motivo do entrelaçamento está confirmado.
- A tabela de scalers em `06D4AE` tem2048 referências. A seleção de escala é `(inv>>3)&1FFC`, equivalente a um bucket `inv>>5`. Cada linha do scaler tem12 bytes, incluindo MOVE.B deslocado, DBRA e retorno indireto.
- O exportador lê somente os operandos numéricos de amostragem dessas rotinas e produz `sample_offsets[2048][72]` (294.912 bytes). Todos os147.456 slots corresponderam ao opcode MOVE esperado. **A nova ROM não executa esses opcodes extraídos.** A lei geradora matemática exata dos offsets ainda pode ser reconstruída para remover essa dependência do extrator.
- O céu usa128 colunas de panorama repetidas, com um offset de início por vista. O protótipo já acompanha os offsets das16 poses de diagnóstico; ainda não reconstruiu a atualização contínua do yaw no jogo.

## ROMs e desempenho

No ZIP v02:

- `01-Geometria-Calculada-Spawn.bin`: calcula uma imagem no 68000 e fica nela. Serve à auditoria de pixels; não é o replay da etapa1.
- `02-Geometria-Continua-Poses.bin`: recalcula continuamente. Esquerda/direita selecionam16 poses capturadas de câmera, aplicadas à mesma geometria e ao céu. Não há deslocamento pelo mapa, colisão, IA, portas, menu ou troca de setor.

Ambas têm512 KiB, sem SRAM ou mapper. Arma/HUD/rosto são uma sobreposição estática capturada; sprites do mundo ainda não foram implementados. As duas regiões VRAM que continham pixels de cenário são zeradas na construção, tornando impossível que o novo viewport simplesmente reapresente esses pixels.

Medição da ROM contínua no spawn, após180 quadros de aquecimento e por1500 quadros de vídeo:71 publicações, intervalos de21 quadros; **2,857 FPS usando60 Hz nominais (~2,853 com a frequência NTSC exata)**. Essa é a implementação C escalar inicial, sem os atores e a lógica do jogo. **Não atingiu o desempenho da referência.** Não comparar como se tivesse a mesma carga; não apresentar a ausência dos inimigos como uma otimização concluída. O alvo permanece primeiro fechar a imagem, depois igualar a velocidade.

## Reprodução

Use o core no commit indicado no README, mas aplique `tools/genesis-plus-gx-phase2.patch` (patch completo sobre o upstream, substitui o patch da etapa1). Ele acrescenta os snapshots em limites de função. Não aplicar os dois patches em sequência.

```bash
python tools/capture_geometry.py --rom /local/E1M1-alpha2.bin --core /local/core.so --out results/geometry-still
python tools/capture_geometry.py --rom /local/E1M1-alpha2.bin --core /local/core.so --out results/geometry-turn --turn
python tools/validate_geometry.py --rom /local/E1M1-alpha2.bin results/geometry-still
python tools/validate_geometry.py --rom /local/E1M1-alpha2.bin results/geometry-turn
python tools/validate_projection.py --rom /local/E1M1-alpha2.bin --results results
python tools/export_scene.py --rom /local/E1M1-alpha2.bin --still results/geometry-still --turn results/geometry-turn --out /tmp/scene-assets
cc -O2 -shared -fPIC -Ireconstruction reconstruction/scene.c /tmp/scene-assets/data.c -o /tmp/scene-assets/model.so
python tools/validate_raster.py --rom /local/E1M1-alpha2.bin --results results --host-library /tmp/scene-assets/model.so
python reconstruction/build_scene.py --assets /tmp/scene-assets --capture /local/captura-etapa1 --prefix /toolchain/bin/m68k-elf- --out /tmp/scene-rom --hold 1
```

Para teste contínuo, omitir `--hold`. A captura da etapa1 está no ZIP do primeiro checkpoint, ou pode ser refeita com `capture.py`. Para auditar a perspectiva, construir com `--hold 1 --pose 3`.

```bash
python tools/validate_scene_rom.py --build /tmp/scene-rom --core /local/core.so --host-library /tmp/scene-assets/model.so
python tools/benchmark_scene.py --build /tmp/scene-rom-continuo --core /local/core.so
```

Não publicar WAD, ROM original, ELF ou core compilado. O exportador e os assets gerados localmente dependem da cópia da ROM do usuário; o pacote publicado contém os resultados e as ROMs experimentais novas, não o binário de referência.

## Próximo trabalho

1. Explicar e fechar as regiões ainda não preenchidas, capturando o estado antes/depois de cada kernel e do estágio de sprites. As comparações mascaradas não bastam para declarar uma vista completa equivalente.
2. Reconstruir os posts, ordenação e oclusão dos sprites do mundo; preservar as janelas de coluna.
3. Decodificar a seleção do setor/stream e as condições de visibilidade para deslocar a câmera e permitir E1M1 navegável.
4. Substituir as poses de diagnóstico por atualização contínua de sin/cos/yaw, com o céu correspondente.
5. Depois da fidelidade, transportar os laços quentes para assembly preservando os testes. O protótipo ainda faz trabalho escalar, limpa o framebuffer e consulta tabelas por pixel; isso não é o laço empacotado do original.
