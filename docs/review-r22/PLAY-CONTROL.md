# R22c — controle jogável 8×8

ROM: `doom-md-r22c-play-control.bin`.

Base de código: R22c `967a55f61d63c753ed37168f3b0bdf31ddfb1ab4`. Usa o backend de tiles8×8 de38×22 amostras, com as mesmas otimizações do `doom-md-r22c-control.bin`, mas sem TIMEDEMO. Música E1M1 habilitada. Não ativa DOOM_R22_PIXEL4, SOLID_TILES ou PAIR_LUT. Não aumenta a zona de memória nem muda cache, mapas ou alocador para este comparador.

Objetivo: jogar E1M1 até a saída e verificar intermissão e carregamento de E1M2. Se funcionar, confirmar que a fase2 de fato aceita movimento e renderiza, além de apenas mostrar a intermissão. Se falhar, guardar a mensagem e o ponto da transição.

O erro anterior em4×4 foi `Z_Malloc: failed to allocate2028B`; os campos seguintes ficaram cortados. O teste deste controle ajuda a distinguir um limite comum do jogo de uma diferença introduzida pelo backend4×4. Completar a DEMO3 não garante espaço para todos os mapas nem valida a transição.

O ZIP contém ROM, ELF correspondente, flags, log, SHA256SUMS, orçamento de heap SGDK, manifesto, versão da ferramenta e commit. A auditoria confere identidade, ausência de TIMEDEMO/PIXEL4, flags do controle8×8 e orçamento de boot/runtime. Ela não executa o jogo nem prova memória suficiente em E1M2.
