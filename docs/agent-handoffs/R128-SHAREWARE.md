# R128 All Shareware para Mega Drive

Esta variante parte da R128 All, com as otimizações de escadas, cadáveres,
visibilidade dos monstros e sprites distantes. A campanha é **Knee-Deep in
the Dead**, com E1M1 a E1M9 vindos do Doom 1.9 shareware. O E1M1 tem 475
linedefs na origem. A fase secreta E1M9 continua retornando ao E1M4.

## Fonte e arte

O build recebe o `DOOM1.WAD` local com SHA-256
`1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771`.
Esse arquivo fornece os nove mapas, os efeitos sonoros, a fonte e o HUD.
A conversão reutiliza o pacote compacto de texturas e sprites que já faz
parte do port Doom64KB. O script registra os hashes de entrada e da
conversão e recusa IWADs diferentes. O manifesto em
[`assets/r128-shareware/manifest.json`](../../assets/r128-shareware/manifest.json)
identifica os exports de arte e os binários nativos usados no build.

A abertura usa a tela BOLLUX. Start, A, B e C abrem o menu principal.
A fonte branca fica sobre uma caixa de Shadow do VDP, e o seletor
continua em **Select Level**. Em **Credits** cada toque avança uma vez na
ordem DoomCREDIT10 → Disclaimer and Credits → EndMD2 → abertura. O
final do E1M8 também mostra EndMD2 após o texto.

## Build local

Execute a partir de um checkout deste ramo, com Fish, Python 3, Pillow,
NumPy, compilador C de host, Java, make, patch e um SGDK nativo com
`m68k-elf-gcc` no diretório `bin`. O diretório de saída deve ser novo.

```sh
bash scripts/lab/build_r128_shareware.sh /caminho/DOOM1.WAD /caminho/sgdk /caminho/r128-sw-build
```

O script prepara uma cópia do commit, executa a cadeia original da R128
All e depois aplica os patches em
[`scripts/lab/r128-shareware/`](../../scripts/lab/r128-shareware).
A saída inclui ROM, ELF, `MANIFEST.json`, `shareware-e1.json`,
`BUILD-INPUTS.sha256`, `SOURCE-COMMIT` e `audio-layout.txt`.
`SOURCE-COMMIT` identifica a revisão arquivada para o build.
A ROM usa endereçamento linear e cabe em 4 MiB.

A configuração local de referência usa GCC m68k 13.1 e SGDK 2.11.
Se usar uma cópia limpa desse SGDK, prepare as ferramentas de host e
aplique o patch de compatibilidade antes de recompilar `libmd.a`.
O exemplo pressupõe que `SGDK_DIR` aponte para a cópia privada, que o
cross-compiler e as ferramentas SGDK nativas estejam no PATH e que
`REPO_DIR` aponte para o checkout.

```sh
sed -i 's/\r$//' "$SGDK_DIR"/makefile.gen "$SGDK_DIR"/inc/dma.h \
  "$SGDK_DIR"/src/dma.c "$SGDK_DIR"/res/libres.res
patch -d "$SGDK_DIR" -p1 --fuzz=0 < "$REPO_DIR/scripts/lab/r128-shareware/sgdk211.patch"
make -C "$SGDK_DIR" -f makelib.gen EXTRA_FLAGS=-std=gnu11
R128_SGDK211_COMPAT=1 bash scripts/lab/build_r128_shareware.sh \
  /caminho/DOOM1.WAD "$SGDK_DIR" /caminho/r128-sw-build
```

A configuração SGDK 2.11 usa uma reserva DMA de 1 KiB, uma fonte de boot
sem compactação e o `memcmp` compatível fornecido pelo build. A margem
de BSS do wrapper é de 128 bytes em relação ao teto da validação R128
anterior. Isso mantém explícita a diferença da configuração local.

## Distribuição

O commit contém o código, a receita de build e os arquivos das artes
integradas. O `DOOM1.WAD` é fornecido pelo usuário no build. A
[licença reproduzida no pacote Debian](https://sources.debian.org/src/doom-wad-shareware/1.9.fixed-4/debian/copyright/)
distingue a redistribuição do arquivo shareware original da criação de
derivados. O uso desse IWAD como origem não confirma autorização para
publicar uma ROM modificada com os dados embutidos.

## Verificação local

- A conversão de nove mapas produziu o WAD intermediário com SHA-256
  `2133ff28cfd4565dbf311de9e3730df080f19258eacbb0f25e7bd289f2403108`.
- No Genesis Plus GX, o menu carregou E1M1 a E1M9. Em cada mapa foram
  confirmados o número de linedefs, a progressão dos tics e a resposta
  da câmera. Start, A, B e C abriram o mesmo menu. As telas de abertura,
  Shadow e créditos foram comparadas com a implementação anterior.
- A ação de encerramento do E1M8 foi acionada via RAM para verificar
  intermissão, texto e EndMD2. Esse ensaio cobre a transição visual.
- A ROM de referência tem 3.801.088 bytes, BSS de 58.030 bytes e SHA-256
  `a66d4820a72c63865a46033687d867cdba6164c5062d0fa9f0f36a0533adfc3b`.
  A auditoria confirmou zero bytes de áudio acessados pelo Z80 acima
  do endereço `0x200000`.
- O teste físico no Mega Drive continua pendente.
