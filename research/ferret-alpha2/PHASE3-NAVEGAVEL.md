# v03 — E1M1 navegável com o direcional

ROM experimental standalone da reconstrução. Cima/baixo deslocam o jogador; esquerda/direita giram continuamente. A corre; Start retorna à posição inicial. Não é um seletor de poses.

**Limitações:** sem monstros, itens, tiro, música, menu ou portas funcionais. HUD, rosto e arma são imagens estáticas. Ainda é o renderer C escalar, abaixo do desempenho da Ferret. Apenas testes em emulador foram executados nesta entrega; aprovação visual e de controle em console fica pendente.

## Arquivos

- `artifacts/Ferret-Reconstrucao-Navegavel-v03.bin`: ROM direta,768 KiB, sem SRAM e sem mapper.
- `artifacts/Ferret-Navegavel-v03.zip`: mesma ROM, código novo, instruções, hashes, capturas e resultados.
- Os checkpoints v01/v02 continuam preservados. A main e o motor D01 não foram alterados.

## Correção das vistas quebradas

A v02 usava o stream de visibilidade capturado da célula29 em todas as poses. A consulta à árvore espacial para a posição renderizada `(8448,-1280)` nas coordenadas internas retorna a célula131, cujo stream é diferente. Isso explica por que trocar somente os ângulos deixou regiões enormes sem desenho no protótipo.

A v03 consulta a BSP a cada deslocamento e escolhe a lista correspondente à célula atual. Não toma o ponteiro em cache do snapshot como verdade espacial. Isso é uma correção da reconstrução; não estabelece, por si só, um bug da ROM original, cujos estados são atualizados em contextos e tempos distintos.

Foram extraídos os430 nós da árvore,431 folhas/células,642 slots de parede e32.460 referências de visibilidade. As folhas não são os setores do WAD original: são células do formato convertido. Vértices, texturas, alturas, coordenadas de textura e scalers continuam compartilhados em ROM. Nenhum framebuffer capturado fornece os pixels3D deste build; os dois bancos de tiles do cenário são zerados no pacote de interface antes da compilação.

As condições de visibilidade foram habilitadas na extração. Isso amplia a geometria disponível nas listas, mas não reconstrói a lógica das portas e dos especiais. Não afirmar que todas as regiões do mapa são alcançáveis enquanto essa lógica não existir.

## Movimento e colisão

- Posição contínua em coordenadas de mapa com três bits fracionários.
- Rotação com256 ângulos, usando a tabela trigonométrica extraída da referência, ajustada para iniciar olhando na mesma direção do novo spawn.
- Entrada lida no VBlank, por protocolo de controle de três botões. O renderer usa esse estado sem trocar entre poses prontas.
- Velocidade ajustada ao número de VBlanks, limitado a30 por atualização; movimento dividido em passos de até cerca de quatro unidades para evitar atravessar paredes em quadros demorados.
- Colisão de raio16 contra os segmentos originais, com grade de128 unidades para selecionar candidatos. Há deslizamento por eixo quando o movimento diagonal encontra um obstáculo.
- Troca de célula e altura do olho baseada no piso local; degraus de subida acima de24 unidades são bloqueados. A regra de abertura das paredes considera uma altura mínima de56 unidades.
- Start reinicia posição e direção. Não abre menu nesta demo.

A colisão é uma implementação nova para navegar pela geometria reconstruída, não uma reprodução completa da física/portas da Ferret. Ainda pode haver diferenças em cantos, passagens e superfícies especiais.

## Apresentação

A conversão CPU→VDP continua duplicando cada linha fisicamente, nos dois bancos de720 tiles. A publicação dos atributos do plano agora usa DMA de2304 bytes em um novo VBlank, mantendo o stride64 da tabela. Um ISR simples conta VBlanks e lê o controle; não há interrupção de duplicação de linhas.

Foi corrigido um problema de inicialização: o status de blank permanece ativo com display desligado. Antes de esperar a próxima borda de VBlank para o primeiro DMA, o display precisa estar habilitado. A ROM publicada já contém essa correção.

## Validação executada

|Teste|Resultado|
|---|---|
|32 ângulos cobrindo uma volta no spawn|Modelo Python e C idênticos; zero bytes sem desenho em todas essas vistas|
|Caminhada frontal no modelo|Mudou por sete células e acompanhou alterações de piso|
|Ré prolongada no modelo|Parou em y=-208, diante do segmento sólido y=-224, respeitando raio16|
|Direcionais no Genesis Plus GX|Andar, girar para ambos os lados, recuar e resetar funcionaram pela entrada emulada do controle|
|Seis estados da ROM, incluindo caminhada, rotação e colisão|Framebuffer de11.520 bytes igual ao C do host, sem diferenças|
|Reset Start|Retornou ao spawn, célula131|

No teste da ROM, o ponto de parada em ré ficou em y=-205 unidades. Isso preserva uma distância de19 unidades da parede, dentro do intervalo esperado para o último passo discreto e raio16. O modelo com passos menores chegou a-208. Não exigir igualdade de posição entre sequências com tempos diferentes.

Esses testes demonstram consistência entre a implementação host e68000 e a navegação exercitada. Não demonstram equivalência da imagem de todo o mapa com a Ferret nem validam todas as variantes em todos os setores. Os testes v02 continuam úteis para os estágios de projeção e rasterização contra a referência.

### Desempenho

Genesis Plus GX instrumentado, NTSC, sem Sega CD e sem SRAM. No spawn, após180 quadros de aquecimento, medidos1500 quadros de vídeo:52 publicações, intervalos de29 VBlanks, **2,069 FPS a60 Hz nominais (~2,066 na frequência NTSC real)**.

A v03 desenha a célula correta e preenche toda a vista no spawn. O número não deve ser comparado como uma regressão direta do teste incompleto v02. Ainda não igualou a referência, mesmo sem monstros; os laços quentes continuam em C. Não apresentar este build como motor otimizado ou jogo completo.

## Reprodução

Requer a ROM Alpha2 local com o hash do README e a captura `results/geometry-still/geometry.npz` do checkpoint2. Não inclui a ROM de referência, WAD ou ELF.

```bash
python tools/export_navigable.py --rom /local/E1M1-alpha2.bin \
 --capture results/geometry-still --out /tmp/nav-assets
cc -O2 -shared -fPIC -Ireconstruction reconstruction/navigation_scene.c \
 reconstruction/navigation.c /tmp/nav-assets/navigation_data.c -o /tmp/nav-assets/navigation.so
python tools/validate_navigation_model.py --rom /local/E1M1-alpha2.bin \
 --capture results/geometry-still --host-library /tmp/nav-assets/navigation.so --out /tmp/nav-results
python reconstruction/build_navigable.py --assets /tmp/nav-assets \
 --capture /local/captura-etapa1 --prefix /toolchain/bin/m68k-elf- --out /tmp/nav-rom
python tools/test_navigation_inputs.py --build /tmp/nav-rom --core /local/core.so
python tools/validate_navigation_rom.py --build /tmp/nav-rom --core /local/core.so \
 --host-library /tmp/nav-assets/navigation.so
python tools/benchmark_navigation.py --build /tmp/nav-rom --core /local/core.so
```

A captura da etapa1 fornece somente a interface/registradores para o empacotamento; seus tiles3D são apagados. O exportador3D usa os dados do mapa/material e nunca amostra o framebuffer como entrada de cena. O core de teste e seu patch estão documentados nos checkpoints anteriores.

## Continuação

1. Testar esta ROM em console e anotar lugares de colisão/visibilidade incorreta com posição aproximada ou captura.
2. Reconstruir portas, especiais e sprites do mundo. Preservar os testes contra a referência.
3. Reproduzir o laço de colunas/scalers em assembly e medir por etapa, mantendo a nova seleção espacial e a navegação. A melhoria de velocidade ainda está pendente.
