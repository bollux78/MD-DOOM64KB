# Handoff para Werk — menu in-game Mega EverDrive X7 (Down + Start)

**Data:** 2026-11-17  
**Status:** SOLUÇÃO VALIDADA NO HARDWARE NO TILE PALETTE STUDIO; AINDA NÃO APLICADA AO DOOM.  
**Escopo:** tornar o menu in-game e save/load state do Mega EverDrive X7 acessíveis nas ROMs de DOOM MD sem regressão de 35 Hz, render, input, timing, SGDK/SCD ou suporte ao hardware real.

## Evidência experimental

O usuário confirmou que o menu X7 **não abria** nas ROMs anteriores do Tile Palette Studio (nem nas ROMs DOOM); o LED do X7 nem acendia ao pressionar **Baixo + Start**. O atalho funciona na maioria dos jogos comerciais no mesmo hardware.

Duas ROMs de diagnóstico do Studio (estática e com scroll) foram compiladas e testadas no X7. O usuário confirmou: **o menu aparece e Save State e Load State funcionam**. Os dois testes possuem: (1) VBlank IRQ do VDP habilitado, vetor autovetorizado nível 6 funcional, SR com interrupções permitidas após inicialização; (2) polling normal de controle 3 botões nas duas fases TH, incluindo fase TH=0 que expõe Start/A, executado no VBlank. A combinação é **confirmada funcional**, mas o experimento **não isolou qual mudança individual é necessária**.

Referências de implementação:
- https://github.com/bollux78/tile-palette-studio/blob/main/rom_test.py (ROM estática)
- https://github.com/bollux78/tile-palette-studio/blob/main/scroll_loader.S (ROM scroll)
- https://github.com/bollux78/tile-palette-studio/tree/experiment/x7-controller-poll/diagnostics/x7 (binários validados)
- https://github.com/bollux78/tile-palette-studio/blob/main/tests/test_rom.py
- https://github.com/bollux78/tile-palette-studio/blob/main/tests/test_scroll_rom.py

## Sequência de controle 3 botões que funcionou

Endereços do Mega Drive:
- **0xA10009:** registrador de direção do controle 1; bit 6 = TH como saída (valor 0x40).
- **0xA10003:** dados do controle 1; bit 6 = TH.
- **0xC00004:** status/control VDP, lido no ISR para reconhecer VBlank.

Na inicialização, configurar direção TH saída e deixá-lo alto:

```asm
move.b #0x40,0x00a10009
move.b #0x40,0x00a10003
```

Na ISR de VBlank, *apenas como referência* do protótipo validado:

```asm
vblank_irq:
    move.l %d0,-(%sp)
    move.b #0x00,0x00a10003  /* TH baixo: fase Start/A */
    nop
    nop
    move.b 0x00a10003,%d0
    move.b #0x40,0x00a10003  /* TH alto: fase D-pad/B/C */
    nop
    nop
    move.b 0x00a10003,%d0
    move.w 0x00c00004,%d0    /* acknowledge/status */
    move.l (%sp)+,%d0
    rte
```

A ROM estática usa as mesmas fases de polling no handler nível 6, com `MOVE.B` imediato e leitura do porto; não é necessário replicar os opcodes exatos no DOOM. **Não inserir cegamente este ISR no DOOM.** O DOOM já possui sistema próprio de input, tarefas e interrupções.

## Observações sobre o DOOM real

Na branch `exp-werk-scd-subport-s1s2`, o arquivo `src/boot/sega.s` tem vetor de V-Int apontando para `_VINT` e inicialização `_Entry_Point` com `move #0x2700,%sr` durante o boot. `_VINT` gerencia `task_lock`, troca de contexto e caminhos `no_user_task`. Portanto:
1. Verificar se V-Int permanece **habilitada no registrador 1 do VDP (bit 5)** em jogo e no menu, e se a máscara SR volta a permitir IRQ nível 6 (por exemplo SR 0x2000, quando apropriado). `0x2700` no boot **não é por si só um bug**; o que importa é o estado depois da inicialização.
2. Auditar o driver de controle **realmente usado** pelo DOOM. Confirmar que faz leitura de TH=0 (Start/A) e TH=1 (direções), na frequência adequada, e que não mantém TH fixo em alto. Verificar eventual comportamento de controle de 6 botões, multitap e periféricos: não degradar compatibilidade.
3. Se já existe polling correto no driver, **não duplicá-lo** na ISR; verificar se o X7 consegue reconhecer o atalho com a cadência atual. Se necessário, adicionar polling no local correto do sistema de entrada, sem interferir no task scheduler.
4. Não remover nem substituir `_VINT`, `_trap_0`, `task_lock`, `hintCaller` ou callbacks SGDK; não colocar trabalho pesado dentro do VBlank.
5. Verificar se o retorno do menu X7 e de save/load state preserva os registradores do VDP, IRQ, SRAM/RAM e estado do motor; evitar escrita em registradores reservados ao X7.

## Plano de execução

- [ ] Identificar driver de joystick e configurações VDP/SR em todos os modos (MD nativo, Sega CD presente/ausente, menu e jogo).
- [ ] Adicionar instrumentação mínima para registrar polling TH=0/TH=1 e frequência de V-Int, sem alterar o render.
- [ ] Aplicar a menor correção possível ao driver de input e/ou configuração V-Int.
- [ ] Compilar ROM MD nativa e Sega CD, validar boot, 35 Hz, tics sem perda, menu/pausa, render e performance.
- [ ] Testar em BlastEm para regressões (o emulador **não** valida a interface física do EverDrive X7).
- [ ] Entregar ROM para teste no **X7 real**: pressionar Baixo+Start, confirmar menu, Save State, Load State, saída do menu e continuação do jogo.
- [ ] Registrar resultado e commits; só marcar como resolvido após confirmação em hardware.

## Critérios de aceitação

1. Menu do X7 aparece em jogo e, quando aplicável, no menu DOOM.
2. Save/Load State e retorno ao jogo funcionam no cartucho.
3. Não há regressão de desempenho, estabilidade, inputs, VBlank, 35 Hz ou caminho sem Sega CD.
4. O jogo continua funcional em Mega Drive real sem EverDrive.

**Nota:** a correção confirmada é a **combinação** VBlank IRQ + leitura TH em duas fases. Atribuir causalidade exclusivamente ao polling TH, ou exclusivamente ao VBlank, exigiria testes separados.
