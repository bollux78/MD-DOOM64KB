DREAD GAMEPLAY C6 — duas versões candidatas para console

NORMAL:4MiB, sem mapper/SRAM/CD, paleta e texturas compartilhadas da C5.
PALETAS SSF:10MiB, mapper Everdrive SSF, sem SRAM/CD, cenário/sprites/céu reconvertidos com paleta própria de cada fase.

As duas incluem:
- RESOLUCAO:160x72 ->80x144 ->80x72 ->160x144 (H40). H32 permanece disponível e adapta as larguras. O modo80x72 duplica linhas e colunas. HUD e armas são independentes da amostragem do cenário.
- Armas da folha guns_optimized_pal.png fornecida pelo autor. Sem redimensionar: recortes explícitos no gerador,15 cores MD com dithering e transparência. Clarão da shotgun ligado ao cano da pose de disparo.
- Correção do preto ao atirar: não descompactar quadros na interrupção; um bloco de arma por VBlank, adiando a transferência do cenário nesse VBlank. A CPU prepara quadros fora da interrupção. Não se esconde a arma durante a atualização.
- Bob vertical reduzido, base sobreposta ao HUD e bob zerado ao parar, evitando faixa vazia.
- IDKFA mantém munição enquanto ligado; desligar restaura o inventário salvo antes do cheat.
- Clarão do viewport: disparos do jogador e explosões de barris/foguetes; tiros de inimigos não o acionam.
- Música End na tela do texto final; FLOOR4_8 convertido com Floyd-Steinberg contra as cores reais da paleta MD.
- Intermission com música Inter, nome da fase e estatísticas; créditos, filtros de powerups, barris, grades, mira vertical e menus permanecem.

Controles: A tiro; B uso e, segurado com direcional, corrida2x; C+A troca arma; C+direcionais strafe; START pausa/retoma. VOLTAR A ABERTURA na pausa reinicia para o título.

Versão SSF:
Os2MiB inferiores mantêm código, música, SFX e interface. A janela0x200000–0x3FFFFF recebe um mapa por vez; quatro registros de512KiB mudam somente na carga da fase. Evita bank switching por coluna/pixel. Por isso o arquivo tem10MiB: usa bancos independentes por fase, com alinhamento e menos compartilhamento entre mapas, em vez do layout linear estimado em~6,4MiB. Cabe no limite de15MiB combinado para o X7.

Validação: Genesis Plus GX NTSC instrumentado, SRAM bloqueada. Quatro modos na ordem solicitada; seis armas e munição infinita; amostragem de100 quadros por arma para detectar o apagão grande da C5; música End com áudio medido; nove mapas e paletas conferidos na SSF; saídas normais e secretas; filtros de powerups. A faixa de atualização do cenário em altura completa permanece, conforme autorizado. Não equivale a campanha integral jogada manualmente ou validação no console.

Benchmark comparativo interno, mesma rota E1M1,313 quadros (ativação pela RAM inclui um quadro de transição), IA desativada, sem limitador:160x72=3,21FPS;80x144=3,41;80x72=4,09;160x144=2,52. O80x72 ganhou~27% sobre160x72 neste teste. Contagem usa VBlanks entre início e fim do teste, sem incluir navegação no menu; não comparar diretamente com outros protocolos históricos.

Build com SGDK e toolchain m68k-elf em GDK absoluto; Python/numpy/Pillow e Java. A partir do repositório:
GDK=/caminho/SGDK DREAD_COPY_SEGA_S=1 bash experiments/DREAD_MD/d01/gameplay/build.sh /caminho/doom1.wad /saida/normal
GDK=/caminho/SGDK DREAD_COPY_SEGA_S=1 DREAD_SSF=1 bash experiments/DREAD_MD/d01/gameplay/build.sh /caminho/doom1.wad /saida/ssf
Mapas preparados podem ser fornecidos em DREAD_PREPARED_MAPS; na SSF devem ter paletas próprias e PVS DREAD_OPEN_PVS. WAD/ELF não são publicados.
