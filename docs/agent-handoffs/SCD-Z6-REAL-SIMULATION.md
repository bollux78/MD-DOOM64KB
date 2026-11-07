# Z6 — simulação real no Sega CD (07/11/2026)

## Aprovação recebida e escopo

O usuário aprovou a ROM Z5 no console e autorizou continuar a execução real no Sega CD. A tela de resultados enviada mostra o benchmark do fallback R128 no **Mega Drive**, com 2600 frames e média de 5,60 FPS; ela não é medição do ticker no sub. O cabeçalho usa Z5, não o número 25.

Z5 já executa P_SetupLevel inteiro no sub. Z6 adiciona uma etapa independente: P_Ticker original por 2600 tics usando a gravação privada DTE1M1 (Doom 1.9, E1M1, UV, um jogador, sem flags especiais), AI Normal, RNG reiniciado. A decodificação de comandos segue G_ReadDemoTiccmd. O harness chama P_MapEnd, P_Ticker e incrementa gametic; não executa G_Ticker completo e não deve ser descrito assim.

## Prova e limites

- P_Ticker, P_PlayerThink e P_MobjThinker devem existir no ELF estritamente linkado do sub. Nenhum símbolo é ignorado pelo linker.
- P_Ticker original mantém movimento, física, ataques, IA, thinkers, switches e especiais. G_ExitLevel permanece real; transição de nível/rebirth inesperados interrompem o teste, sem simular sucesso.
- O sub grava 27 checkpoints (0, 100, ..., 2600) de tic, posição XYZ, ângulo, saúde, contagem de mobjs e PRNG. Um hash é calculado pelo sub sobre esses registros.
- Trace reservado em PRG-RAM 0x7C000; linker exige _end inferior a esse endereço. A stack continua no topo de PRG-RAM e há espaço entre ela e o trace.
- Após o marcador exclusivo 0x5A7D, o MD solicita o barramento do sub e copia os 864 bytes do trace através da janela PRG-RAM banco 3 para Word RAM 0x61E000. O teste do BlastEm lê essa cópia, verifica os tics, exige movimento e recalcula o hash independentemente. CSV fica privado junto da ROM.
- Marcador de sucesso só é publicado após 2600 chamadas e leveltime/gametic iguais a 2600. Transporte esperado: DIR + demo + nove lumps do mapa (11 requests).
- Menu inativo é estado da plataforma sem interface; áudio continua silencioso no sub. P_UpdateAnimatedFlat original é linkado de r_plane.c. Nenhuma função de gameplay é substituída por stub.
- START/timeout ainda inicia o jogo R128 no MD. Ainda não há renderização alimentada pelo estado do sub, comparação MD/sub, medição de ganho de FPS ou integração completa de G_Ticker. S1e/S1 não estão concluídos só com este ensaio.
- Teste só de E1M1; não Run All.
- Uma falha de alocação JIT do BlastEm antes do handshake RSP pode reiniciar o processo até três vezes, apenas com a mensagem específica de displacement fora do intervalo. Falhas após iniciar a execução não são repetidas nem ocultadas.

## Histórico de desenvolvimento

- d703485: primeiro harness e instrumentação.
- 284e781: usa seletor R89 já presente em p_enemy2; não existe r89_ai.c independente.
- Run 42416577055: Z4/Z5 regressão PASS; Z6 link estrito falhou exclusivamente em _g_menuactive e P_UpdateAnimatedFlat. Nenhuma execução Z6 nessa rodada.
- 45ef51f: estado do menu na plataforma, função original de pisos animados e proteção contra falha de inicialização JIT.

## Resultado comprovado

**Build/link estrito PASS / BlastEm PASS / hardware NOT TESTED.** Run [42417494369](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42417494369), commit `04a66b641a2e7f8b9ed53fcc524ca5bb8b560a8d`.

- A primeira execução real (run 42417100122) alcançou tic 1791 e acionou I_Error, sem mensagem capturada. Não afirmar causa exata a partir desse ensaio.
- A variante final usa heap de **224 KiB** (só no ticker), com verificação de orçamento PRG-RAM no link. Também adiciona captura de mensagens I_Error pela janela PRG-RAM após parar a CPU sub.
- Final: stage=5, marcador=0x5A7D, served=11, bytes=63309, errors=0, timeouts=0, último tic=2600.
- 27 checkpoints, movimento do jogador e hash calculado no sub **0x182C31E7**, revalidado pelo teste a partir da cópia PRG-RAM → Word RAM. CSV privado `sub_trace.csv` junto da ROM.
- Último registro: x=16273485, y=-225441901, z=-524288, angle=1846485055, health=0, mobjs=34, prndindex=220. **O jogador terminou morto.** Isto não reprova a prova de simulação, mas impede apresentar o teste como demonstração de paridade, UV-Max concluído ou jogo offloaded validado.
- Fallback G_Ticker no MD PASS; regressões Z4 e Z5 PASS; workflow final SUCCESS.
- ROM privada: `/home/dan/Projetos/Personal/scd-subport-s1e-z6/run-42417494369-1/doom-md-scd-s1e-z6.bin`.
- Tela esperada: `S1E Z6 SUB P_TICKER 2600`, `2600 TICS PASS`, `TRANSFER PASS`, `STATE HASH 182C31E7`. A simulação acontece antes dessa tela, sem imagem 3D no sub. START/timeout → R128 no MD.

## Próximas etapas

1. Testar a Z6 no console físico e guardar aprovação separada da Z5.
2. Comparar trace MD com mesmo WAD/input/AI/RNG, localizar morte e primeira divergência (diferenças por layout/endereço do R128 são possíveis; não prometer bit identity).
3. Integrar G_Ticker completo e estados de jogo; depois conectar estado do sub à renderização e medir ganho real. A simulação Z6 isolada não mede FPS do jogo renderizado.


## Z6 no console físico — confirmação de 07/11/2026

Foto enviada pelo usuário confirma TRANSFER PASS / STAGE 5, REQUESTS 11 / ERRORS 0, BYTES 63309, AI NORMAL, STATE HASH 182C31E7 e 2600 TICS PASS. **Z6 hardware PASS para a simulação.** Hash igual ao BlastEm. A foto não confirma por si só o fallback após START. Continuação autorizada: captura independente MD/sub (Z7) e depois integração completa de G_Ticker.
