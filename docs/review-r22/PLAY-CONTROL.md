# R22c — controle jogável 8×8

ROMs do pacote:

- `doom-md-r22c-control.bin`: controle8×8 TIMEDEMO3.
- `doom-md-r22c-play-control.bin`: controle8×8 jogável com música.

Base de código: R22c `967a55f61d63c753ed37168f3b0bdf31ddfb1ab4`. Usa o backend de tiles8×8 de38×22 amostras, com as mesmas otimizações do `doom-md-r22c-control.bin`, mas sem TIMEDEMO. Música E1M1 habilitada. Não ativa DOOM_R22_PIXEL4, SOLID_TILES ou PAIR_LUT. Não aumenta a zona de memória nem muda cache, mapas ou alocador para este comparador.

Objetivo: jogar E1M1 até a saída e verificar intermissão e carregamento de E1M8. Se funcionar, confirmar que a fase2 de fato aceita movimento e renderiza, além de apenas mostrar a intermissão. Se falhar, guardar a mensagem e o ponto da transição.

O erro anterior em4×4 foi `Z_Malloc: failed to allocate2028B`; os campos seguintes ficaram cortados. O teste deste controle ajuda a distinguir um limite comum do jogo de uma diferença introduzida pelo backend4×4. Completar a DEMO3 não garante espaço para todos os mapas nem valida a transição.

O ZIP contém as duas ROMs, ELFs correspondentes, flags, log, SHA256SUMS, orçamento de heap SGDK, manifesto, versão da ferramenta e commit. A auditoria confere identidades, TIMEDEMO somente no control, ausência de PIXEL4 nos dois e flags do controle8×8 e orçamento de boot/runtime. Ela não executa o jogo nem prova memória suficiente em E1M8.

A função I_R21_TextScreen foi movida para fora do bloco TIMEDEMO no backend8×8: a tela de erro também precisa dela na ROM jogável. A implementação e a política de memória são as mesmas.

Atualização do usuário: o Z_Malloc na transição já ocorre desde a R18. g_game.c contém uma regra explícita para E1M1: _g_wminfo.next=7, índice zero, portanto o destino é E1M8. O objetivo atual é testar E1M1→E1M8. A anterior referência a E1M2 no README do primeiro ZIP era uma suposição incorreta. Ainda não está identificado se a alocação falha por demanda da fase8, fragmentação ou liberação incompleta da fase1.
