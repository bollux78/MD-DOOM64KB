DREAD GAMEPLAY C4 — candidato para teste no console

Doom shareware, E1M1–E1M9, sem SRAM/mapper/Sega CD.
A: tiro; B: uso; C+A: troca arma; C+direcionais: strafe; START: pausa.

Mudanças: caixa de sombra na abertura com texto branco; créditos id Software -> créditos novos do autor -> final shareware. CHEATS na pausa: IDDQD (invulnerabilidade) e IDKFA (inventário completo; ao desligar restaura inventário anterior). Barris sólidos, destrutíveis, explosão e reação em cadeia; decoração sólida identificada nos dados originais. Clarão de tiros/explosões apenas na paleta do cenário. Morte: cenário vermelho, grito, câmera no chão, aguarda novo botão para reiniciar a fase. Não há checkpoints.

Corrigida referência de altura na colisão de escadas/pisos móveis. Projéteis usam abertura real do portal, não colisão circular do jogador; passam por grades. Mira vertical por altura na interseção de cada parede; foguetes também ganham inclinação automática.

Verificações: seis modos de vídeo; créditos; cheats liga/desliga; barril destruído; descida da área inicial e subida dos degraus E1M8; entrada e subida no elevador E1M2; tiro em inimigo mais alto; bola de imp atravessando parede de duas faces bloqueadora E1M9; morte/espera/respawn; saídas normais e secretas. Testes com poses/estado controlados no Genesis Plus GX, sem SRAM. Não equivale a campanha completa jogada manualmente nem validação de hardware.

Powerups: invulnerabilidade 30s com inversão das cores não pretas, traje 60s verde, invisibilidade 60s com arma pontilhada e menor precisão dos monstros, visor 120s com iluminação máxima, Berserk +10x soco e saúde até100 (até fim da fase), vermelho desaparecendo em20s. Filtros de powerups afetam cenário e arma, preservam HUD; preto preservado para manter bordas. Piscam nos últimos4s. O clarão de tiro/explosão afeta somente cenário.

Invulnerabilidade e Berserk não aparecem nos THINGS de dificuldade média do WAD shareware usado: esses estados foram validados por injeção controlada dos contadores; invisibilidade também por pickup real da E1M3. Os efeitos visuais são aproximações adaptadas às paletas do Mega Drive, não reproduções pixel a pixel da paleta VGA.

Reproduzir: GDK e DREAD_COPY_SEGA_S=1, gameplay/build.sh doom1.wad DIRETORIO; QA usa DREAD_TEST_ROOT, DREAD_TEST_CORE (GPGX instrumentado), DREAD_TEST_NM, DREAD_TEST_WAD e DREAD_GAME_VARIANT. ELF e WAD permanecem locais, não publicados.
