# C7: experimentos inspirados na análise do Ferret

Base: 114a4147073c7c7ce3aa314d2ad93b57d2a15bae (grades por trechos opacos e scalers nativos).

- CONTROL: base, sem flags Ferret.
- CACHE2: cache de vértices com duas vias em 256 entradas, sem ampliar arrays em RAM. Um bit da chave da via 0 guarda a recência; índices precisam caber em 15 bits.
- SPARSE: prepara alturas e coordenadas apenas em runs de colunas abertas, no caminho nativo. Só ativa com pelo menos 16 colunas fechadas e no máximo 8 runs. Os demais modos mantêm os anchors originais.
- FERRET_ALL: ambas as alterações.

Não é cópia de código da ROM Ferret; são adaptações experimentais dos mecanismos estudados à C7. Não há promessa de ganho. O cache e a varredura dos runs têm custos próprios e podem regredir.

Preparação, compilação, benchmark e pacote são executados no Actions; o build usa o runner self-hosted e o WAD local. A versão estável não é alterada. O preflight exercita o código real de cache com endpoints colidentes e a equivalência modular dos reinícios de interpolação. Não substitui o teste do Assembly no emulador.

O MAME usa genesis (NTSC), com frequência medida pelo relógio emulado. Cada ROM executa os primeiros 312 quadros da DEMO3/E1M7, com e sem IA. A velocidade do host não é FPS do jogo. Comparar VBlanks e FPS somente dentro desta rodada, pois o benchmark histórico usava megadriv (PAL) com fórmula de 60 Hz.

O relatório registra os hashes visuais finais e um gate de imagem final. Isso não prova igualdade de todos os frames nem de todos os mapas, principalmente cenas com grades fora da DEMO3. As variantes não são promovidas automaticamente. Se um hash divergir, a variante deve ser investigada antes de ser chamada de exata.

As ROMs mantêm geometria, texturas, IA e otimização de grades da base. O benchmark em combate pode mudar de carga se houver dependências temporais na lógica; registrar essa limitação ao interpretar variações.
