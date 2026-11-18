# NeoDoom P0

Primeiro protótipo de um renderizador separado para Mega Drive, usando a E1M1 shareware. O objetivo deste teste é mudar a representação e o algoritmo de desenho. **A versão atual ainda não demonstra uma vantagem de desempenho sobre a R128.** Não é uma nova versão jogável da R128.

## O trabalho mudou

O conversor usa a BSP somente no computador, para reconstruir células convexas. Recorta os limites físicos e une células adjacentes do mesmo setor quando a união continua convexa. Exporta 197 salas, 1.081 arestas direcionadas e 734 portais direcionados, com planos, normais, materiais e ligações explícitas. A ROM não recebe nós BSP.

O runtime começa na sala da câmera. Projeta uma parede por vez, limita sua faixa horizontal, desenha teto/chão/paredes e encaminha somente as colunas ainda abertas à sala do outro lado do portal. Uma pilha de tarefas substitui a travessia BSP. Os limites verticais são interpolados entre as extremidades da faixa; essa aproximação evita repetir a projeção de alturas em cada coluna. As direções das colunas são calculadas uma vez por quadro. O teste não percorre todos os segmentos do mapa por coluna.

A primeira tentativa local usava raios por coluna e repetia testes de arestas; ela foi substituída pelo caminho de projeção de paredes antes desta entrega. Não é o antigo NEXUS com outro título. O leitor de WAD e a composição de texturas reaproveitam os utilitários daquele projeto; o render e o formato de salas/portais são próprios deste experimento.

## ROM e controles

ROM de 262.144 bytes, NTSC. Viewport de 288 × 160 pixels, com 72 × 40 amostras lógicas de 4 × 4 pixels. Usa 16 cores, 32 texturas reamostradas para 64 × 64 texels, chão e teto lisos. O Pair-V e a amostragem tonal da R128 ainda não estão integrados. Também não há arma, monstros, objetos, iluminação de setores, céu original, animação de portas, áudio ou simulação Doom.

- Esquerda/direita: girar.
- Cima/baixo: avançar/recuar, com checagem simples de sala e altura.
- A/B: alternar entre 16 posições de inspeção no mapa.
- Start: alternar texturas e paredes lisas.
- C: executar benchmark de 64 vistas: 16 posições × 4 direções, no modo visual atual.
- Qualquer botão: sair do resultado do benchmark.

As portas conservam suas alturas iniciais. As posições A/B permitem inspecionar regiões que não podem ser alcançadas sem abrir uma porta. A câmera não implementa toda a colisão Doom nem raio de jogador; não é um jogo completo.

## Medição no Genesis Plus GX

Mesma ROM, mesmas 64 vistas, NTSC. A unidade real do contador SGDK é 76.800 subticks/s; os dados abaixo usam essa constante. O texto da ROM mostra milissegundos inteiros aproximados.

| Modo | Desenho médio | Montagem média | Quadro completo | FPS do teste |
| --- | ---: | ---: | ---: | ---: |
| Texturas | 198,23 ms | 22,72 ms | 262,02 ms | 3,82 |
| Paredes lisas | 133,24 ms | 17,07 ms | 180,78 ms | 5,53 |

O quadro completo inclui espera de VBlank e transferências para o VDP. Tiles uniformes usam 16 padrões residentes em VRAM; somente tiles mistos são enviados. Existem dois bancos de apresentação, sem mostrar um quadro parcialmente carregado.

Em média foram testadas 171,59 arestas e encaminhadas 26,23 tarefas de portal por vista. Nenhum limite de pilha/percurso ou posição inválida foi registrado nas 64 vistas. Essas quantidades não equivalem a contagens da R128, que tem outras rotinas e critérios de descarte.

Este não é o benchmark de demo da R128: resolução, palette, amostragem, objetos e trajetória diferem. Portanto, não se deve usar esses FPS para calcular um percentual de ganho sobre os 8,28 FPS da demo anterior. Os números atuais não sustentam a expectativa de um motor mais rápido. O caminho de desenho continua caro mesmo sem jogo; há trabalho de implementação a resolver antes de integrar a simulação.

## Validação

Uma referência independente lança raios contra os SEGS originais do WAD, sem usar o grafo de salas. Compara somente a cobertura de chão, teto e paredes, não texturas ou cores. Nas 64 vistas:

- 184.320 amostras totais.
- 150.678 amostras fora de uma faixa de um pixel em torno das bordas da referência.
- 143 divergências nessa região: aproximadamente 0,095% das amostras selecionadas.
- Nenhum buraco nessa região selecionada.

Os pixels de borda excluídos continuam sendo diferenças possíveis; os valores completos estão no relatório. Isso não é igualdade de imagem com a R128. A interpolação de alturas, a quantização das salas em quartos de unidade e as texturas reamostradas introduzem diferenças visuais.

Também foram verificados todos os 734 portais direcionados recíprocos e a reconstrução de 32 quadros de tiles sólidos/mistos: 92.160 amostras lógicas, sem erros. O benchmark emula o executável 68000 real; não mede o renderizador compilado para PC. Os testes da referência e dos tiles usam a compilação para PC para inspecionar os dados.

## Reproduzir

Requer o WAD shareware Doom 1.9 original, Python 3 e SGDK. A conversão rejeita outros WADs por hash. Nenhum WAD completo é versionado aqui.

```bash
GDK=/caminho/sgdk DOOM1_WAD=/caminho/DOOM1.WAD bash build.sh
```

Testado com o SGDK/toolchain adaptado usado nos builds R128 deste projeto. O script reconhece a regra de cabeçalho desse SDK; outros ambientes SGDK ainda precisam de validação. Para executar os testes no computador, são necessários GCC, NumPy e Pillow:

```bash
gcc -O3 -shared -fPIC src/render.c src/map_data.c -o neodoom-host.so
python3 tools/check_structure.py . ./neodoom-host.so
python3 tools/check_reference.py . ./neodoom-host.so "$DOOM1_WAD" reference-output
```

A ROM exata medida está preservada em `results/neodoom-p0-e1m1.bin.gz.b64`. Para recuperá-la sem compilar:

```bash
python3 tools/extract_rom.py
```

O script verifica tamanho e SHA-256 antes de escrever `out/neodoom-p0-e1m1.bin`. Em `results` ficam os relatórios e contadores brutos. Os dados gerados completos do mapa ficam no pacote de teste; o código e o extrator permitem reproduzi-los.

Código e histórico: https://github.com/bollux78/MD-DOOM64KB/tree/exp-neodoom-p0/experiments/NEODOOM

Protótipo de fã baseado em dados de Doom shareware, com utilitários derivados do projeto MD-DOOM64KB/NEXUS. Doom e seus recursos pertencem aos respectivos titulares. A R128 estável permanece separada deste experimento.
