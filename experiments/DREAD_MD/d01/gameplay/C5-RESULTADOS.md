DREAD GAMEPLAY C5 — candidato para teste no console

4 MiB, Doom shareware E1M1–E1M9; sem SRAM, mapper ou Sega CD.
A: tiro; B: uso / segurar com direcional para correr (2x); C+A: arma; C+direcional: strafe; START: pausa/retoma.
Pausa: VOLTAR A ABERTURA retorna à tela inicial.

Correções C5:
- Removido o clarão dos disparos no cenário; mantido o das explosões.
- Shotgun: clarão combinado com o quadro de disparo, antes de levantar para recarregar. Animação temporizada em VBlank, independente do FPS 3D. Uploads parciais não mostram pedaços de dois quadros simultaneamente.
- Soco e outras armas: base de recorte aumentada de168 para184 linhas do original, recuperando mãos/arma cortadas; bobbing sobe a partir da borda do HUD.
- HUD: branco da fonte tem entrada reservada; o antigo vermelho escuro foi remapeado ao vermelho mais próximo, evitando que a pausa embranqueça números.
- Reset: desativa H-int de duplicação, limpa rolagens/window e restaura tabelas antes da abertura. HUD/DMA antigos ficam desativados durante a abertura.
- Céu em altura completa: corrigido deslocamento de origem da coluna 72->144 linhas.
- A varredura lateral do modo de altura completa permanece, conforme autorizado, sem trocar o caminho de transferência por uma alternativa mais lenta.
- Intermission: fundo WIMAP0 do shareware, música Inter (arranjo já usado no projeto), nome completo da fase, mortes/itens/segredos/tempo e botão para continuar. Fundo armazenado em160x112, expandido2x2 na carga; texto em resolução nativa, sem RAM permanente adicional para a imagem.

Validação Genesis Plus GX NTSC, SRAM bloqueada: reset durante o jogo -> menu/seletor; seis armas e sequência shotgun; nenhum flash de cenário nos tiros; corrida medida2x; seis modos de vídeo; céu em três posições; filtros de powerups; botão real da saída E1M1 -> tela Hangar com música -> novo botão -> E1M2. As estatísticas usam os monstros/itens da conversão e os setores secretos visitados. Não é uma campanha completa jogada manualmente, nem validação no console.
