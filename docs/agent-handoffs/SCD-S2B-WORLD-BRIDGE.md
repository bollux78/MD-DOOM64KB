# S2b — câmera e estado visual de setores/sides sub → MD

## Base e escopo

O usuário aprovou a S2a em hardware e autorizou avançar. A S2b acrescenta o estado visual de setores e sidedefs à câmera calculada pelo Sega CD. O sub executa os 2600 tics primeiro; depois o MD reproduz as 26 amostras de tics 100–2600, sem G_Ticker/P_Ticker local. Os atores ainda são os locais congelados. Não é comunicação por tic ao vivo, jogo interativo offloaded ou medida de FPS.

## Contrato

`experiments/DOOM_SCD_SubPort/s2b/world_wire.h` define o stream big-endian sem ponteiros. Cabeçalho de 32 bytes: magic 53325742, versão 1, 27 frames, número de setores, número de sides, tamanho usado, checksum, reservado. Tabela de 27 offsets a partir do byte 32; registros começam no byte 256.

Cada frame tem tic, quantidades de setores/sides alterados, hash do mundo canônico e leveltime. Cada setor ocupa 16 bytes: índice, luz, alturas de piso/teto, flat de piso/teto. Cada side ocupa 12 bytes: índice, textureoffset, texturas superior/inferior/central e reservado. A amostra zero inclui todos os setores/sides; as demais só diferenças. Limites: 256 setores, 1024 sides, 32768 bytes totais.

Checksum do transporte: FNV sobre bytes de todo o stream usado, com o próprio campo de checksum tratado como zero. Hash canônico por frame: FNV sobre palavras numéricas, contagens, cinco valores de cada setor e quatro de cada side, na ordem dos índices. Valores assinados são estendidos para uint32. Os hashes são validação diagnóstica, não criptográfica.

## Memória e aplicação

- Sub: stream reservado em PRG-RAM 0x74000–0x7BFFF. O build bloqueia `_end >= 0x74000`; heap da S2b reduzido de 224 para 192 KiB. As variantes anteriores mantêm seu heap.
- MD: após o sub terminar e ceder o barramento, copia somente os bytes usados de 0x434000 (PRG banco 3) para Word RAM 0x600000. Essa área de transporte WAD pode ser reutilizada porque não há novos pedidos durante o replay. Câmera/trace/relatórios permanecem em suas áreas superiores separadas.
- Setores são escritos na representação MD; sidedefs usam os macros originais R23_GET/R23_SET para respeitar SRAM. Ponteiros, thinkers e listas de atores nunca são copiados.
- Cada volta aplica o estado inicial completo e depois os deltas na ordem. Recalcula o hash sobre os valores efetivamente aplicados no MD. Atualiza leveltime e chama apenas P_UpdateAnimatedFlat para apresentação. A lógica MD fica parada.
- Relatório por quadro em 0x61B020: hash esperado/aplicado, quantidades de setores/sides daquele frame e leveltime.
- START sai para o ciclo original do MD; uma saída instrumentada é testada após a volta completa. Não afirmar teste físico de START sem relato específico.

## Validação

O workflow mantém as regressões Z4/Z5/Z7/Z8/S2a e acrescenta build S2b, prova da execução no sub e teste visual independente. `s2a/test_visual.py --world` decodifica o stream em Python, reconstrói os 27 estados e seus hashes, exige alterações reais após a amostra zero, compara os valores efetivamente aplicados no MD por quadro e verifica 26 imagens, ausência de ticks MD e retorno ao ciclo original.

## Resultado validado — 2026-11-08

- Commit de implementação `22cd6de114551bb4faf4ca8b2f832ce37ae88c22`, Actions run `42438888747`, job `128603645468`: build e gate completos PASS, incluindo regressões Z4/Z5/Z7/Z8/S2a.
- Sub: payload 83930 bytes, `_end=0x6EF10`, abaixo da reserva 0x74000. 2600 tics, controlled rebirth PASS, hash natural `7EC065DD`, primeira morte no tic 920. A diferença de trajetória em relação às variantes anteriores é esperada pela fase de visão aproximada dependente de layout; o critério do usuário aceita isso.
- Transporte WAD: 12 requests, 69151 bytes, errors0, timeouts0, stage5, marcador5A8D. Os bytes da câmera e do stream de mundo são cópias adicionais fora desse contador WAD.
- Stream: 8924 bytes para 27 amostras de 85 setores e 273 sides. Após a inicialização: 8 alterações de altura, 61 de iluminação, 208 de side. São contagens de registros alterados entre amostras, não número de portas ou eventos distintos. Nenhuma troca de flat de setor foi exercida nessa demo; o formato suporta o campo, mas não se atribui cobertura dinâmica a ele.
- Python reconstruiu os 27 estados com checksum/hash válidos. Os 26 frames exibidos tiveram câmera exata e hash canônico aplicado no MD igual ao produzido pelo sub. Houve imagens distintas, nenhum G_Ticker/P_Ticker MD durante o replay e saída instrumentada para o G_Ticker MD original: PASS.
- Teste adicional local do decodificador com valores assinados e pacote corrompido: PASS.
- Console S2b: confirmado pelo usuário nesta conversa, com autorização explícita para prosseguir à S2c. Aprovação verbal; sem foto ou métricas adicionais, e sem relato separado sobre START.

ROM privada: `/home/dan/Projetos/Personal/scd-subport-s2b-world/run-42438888747-1/doom-md-scd-s2b-world.bin`.
Mesmo diretório: `visual_report.json`, frames brutos, `sub_trace.csv`, ELF e relatórios de link. ROMs, WADs, ELF e dumps de imagem ficam privados no computador do usuário.

## Teste físico

Com o Sega CD ligado e conectado, abrir a ROM. Esperado: S2B SUB WORLD READY, TRANSFER PASS, requests12/errors0, STATE HASH7EC065DD, 2600 TICS AND REBIRTH PASS. Apertar e soltar START ou aguardar o início automático. Deve aparecer E1M1 em câmeras por saltos com os rótulos S2B CAMERA AND WORLD FROM CD / ACTORS LOCAL FROZEN / START EXIT. As alturas/iluminação/sides acompanham as amostras do sub; monstros e objetos continuam congelados. Não esperar controle do jogador ou FPS representativo. Apertar START novamente para testar retorno ao título/menu original.

Próximo marco: snapshots dos atores com IDs e vínculo espacial local correto; depois comunicação por tic e entrada real. Preservar as ROMs já aprovadas.
