# S2a — primeira ponte visual: câmera sub → renderer MD

## Autorização e base

Z8 aprovada em hardware por foto: 2600 TICS AND REBIRTH PASS, requests12/errors0/bytes69151, hash0A1B0220 igual ao BlastEm. A foto comprova a simulação e prova separada de reinício; não comprova o fallback após START. Usuário autorizou iniciar a imagem a partir do estado sub.

**Aprovação posterior em hardware:** o usuário aprovou a S2a e autorizou prosseguir para S2b (câmera + setores/sides). Aprovação verbal nesta conversa, sem nova foto ou métricas adicionais; não inferir teste físico separado do retorno por START.

## Escopo exato

**Replay de câmera real, sem simulação MD durante a exibição. Não é snapshot completo do mundo, jogo interativo offloaded nem benchmark FPS.** O sub calcula os2600 tics primeiro, devolve27 poses; depois fica parado. O MD inicializa sua cópia de E1M1 uma vez e desenha26 poses (tics100–2600) com atores, portas e geometria dinâmica no estado inicial local. A pose0 é validada mas não exibida: antes do primeiro P_Ticker, viewz=1 por contrato do motor original.

Esse marco valida dados reais do sub chegando ao renderer. A câmera pode atravessar uma passagem aberta no sub que ainda esteja fechada no mapa MD; essa divergência é uma limitação explícita até a sincronização de setores/sides/atores.

## Wire e áreas de memória

- `s2a/camera_wire.h`: por pose, oito palavras32 big-endian `[magic,tic,x,y,z,angle,viewz,health]`, magic53324341. Usa valores/IDs fixos; nenhum ponteiro engine é transferido.
-27×32=864bytes em PRG-RAM0x7C400. Metadados em0x7C780: magic53324142, count27, stride32, hash FNV sobre as216 palavras.
- O checkpoint t=0 é observado dentro do primeiro P_Ticker real; os demais após cada100 chamadas naturais do G_Ticker sub. A prova controlada de rebirth da Z8 ocorre depois e não sobrescreve essas poses.
- Após conclusão, o MD pede o barramento e copia PRG-RAM banco3 de0x43C400 para Word RAM0x61A000 (912bytes incluindo gap/metadados). Metadados MD em0x61A380. A validação de câmera é adicional ao hash/trace/prova da simulação, não substitui o transporte WAD.
- O MD verifica magic/versão da família, sequência, contagem, tamanho e hash antes de usar as poses.

## Exibição

- Cópia descartável do R128 recebe `S2A_InitLocalMap` que chama G_InitNew real e `S2A_ClearMenus` que chama a rotina original local de menu. R_Init/P_Init/plataforma continuam no setup MD original.
- `S2A_Run` aplica posição, ângulo, viewz e saúde; remapeia subsector via R_PointInSubsector local. NÃO copia ponteiro subsector do sub.
- `S2A_Display` chama D_Display original, que chama o renderer e I_FinishUpdate. R20_StopVideo aguarda DMA pendente antes do texto sobreposto.
- Texto explícito: S2A CAMERA FROM SEGA CD / LOCAL ACTORS FROZEN / START EXIT.
-26poses por volta, pausa45VBlanks por pose, repete; START sai para ciclo de título original. O botão precisa estar liberado na entrada para não sair imediatamente.
- Relatório por frame em Word RAM0x61B000: índice/tic e valores efetivamente aplicados ao player MD. Nenhum BSS persistente de snapshot usa os64KiB principais do MD.

## Teste automatizado

1. `test_setup.py --visual`: exige a simulação G_Ticker sub, trace27, hash recalculado, movimento, controlled_rebirth_pass e heap. Encerra esse processo; não confunde prova de sub com captura visual.
2. `s2a/test_visual.py`: processo independente BlastEm, verifica hash das poses, põe breakpoints em G_Ticker/P_Ticker MD e I_Error, e captura S2A_MDFrameDone após exibição/DMA.
3. Exige26frames em ordem, pose efetivamente aplicada igual ao pacote do sub, ponteiro de framebuffer MD válido e mais de3 hashes de imagem distintos. Guarda pixels privados lendo o framebuffer postado r115_show; não usa o buffer de desenho seguinte.
4. Captura S2A_VisualDone ao fim de uma volta. Qualquer tick MD durante o replay reprova; nenhuma imagem/pose é inferida de uma execução MD de lógica.
5. Frames.bin, visual_report.json, ELF/ROM permanecem privados no runner. Não publicar WAD/ROM ou imagens protegidas no GitHub.

## Histórico

-5bfe819 / run42433046052: regressão Z8 PASS; build da ponte MD falhou por genesis.h antes de stddef/stdint e conflito de aliases SGDK. Corrigido para ordem já validada no S1b.
-60e1736 / run42433463410: headers/build e simulação sub PASS; teste visual bloqueado antes de execução porque LTO incorporou P_Ticker e eliminou o símbolo do breakpoint.
-d2c1429 / run42433796760: corpo original MD P_Ticker preservado, atributo noipa/noinline permite breakpoint direto; primeira reprodução26frames/zeroGTickerMD PASS.
-1c5b202: ressincroniza relógio de entrada usando R81_ResyncInput ao sair, e testa o retorno à rotina original MD. Flag volátil de depuração (padrão0) exercita a saída depois de uma volta; no console usa START.

## Resultado

**Build/link estrito PASS / BlastEm VISUAL PASS / hardware NOT TESTED.** Run [42434107386](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42434107386), commit `1c5b20277982a268d589b85cbc0dbc8208c28c61`. Workflow SUCCESS; regressões Z4/Z5/Z7/Z8 PASS.

- Sub S2a: payload82606bytes, `_end=0x739E0`; vetoreszero, heap/cache/trace dentro do orçamento.
- Simulação natural2600 / trace27 / controlled rebirth PASS. State hash **182C31E7**, first dead natural tic2249. O hash difere da Z8 por novo layout executável/endereços (R128 possui fase de visão por endereço); não confundir com prova de paridade. A causa de todas as diferenças MD/sub não foi isolada.
- WAD: requests12, bytes69151, errors0, timeouts0, stage5, marcador5A8D. Esse contador de bytes é do WAD; a cópia de912bytes da área de câmera pela janela PRG-RAM é adicional e não contabilizada como request WAD.
- Validação de pacote de27poses (magic/count/stride/hash), ordem100–2600, aplicação exata de x/y/z/angle/viewz/health no player MD: PASS.
-26quadros capturados após D_Display/DMA, hashes de imagem distintos verificados. Breakpoints em G_Ticker e P_Ticker MD não foram alcançados durante a reprodução. Zero lógica MD apenas DURANTE esse replay; após sair, G_Ticker MD foi alcançado como esperado.
- Saída de prova: flag de depuração1 após S2A_VisualDone, retorno a R81_ResyncInput/D_StartTitle/loop original MD: PASS. START físico ainda precisa ser observado no console.
- ROM privada: `/home/dan/Projetos/Personal/scd-subport-s2a-camera/run-42434107386-1/doom-md-scd-s2a-camera.bin`.
- Mesmo diretório: `visual_report.json`, `camera-frame-01.bin` … `camera-frame-26.bin`, `sub_trace.csv`, ELF e relatórios de link. Artefatos binários/imagens permanecem privados.

## Teste físico sugerido

Sega CD ligado/conectado. Abrir a ROM; aguardar diagnóstico S2A SUB CAMERA READY / TRANSFER PASS / STATE HASH182C31E7 /2600TICS AND REBIRTH PASS. START e soltar (ou aguardar15segundos). Após setup gráfico, deve aparecer E1M1 percorrida por câmeras em saltos, com rótulos CAMERA FROM SEGA CD e LOCAL ACTORS FROZEN. Não esperar controle de movimento, monstros/portas acompanhando o sub nem FPS representativo. Gravar alguns segundos/fotografar cenas e, depois, apertar START para verificar retorno ao título/menu normal.


## Próximos passos

Após a prova visual: sincronizar setores/sides/objetos/HUD com IDs estáveis e remapeamento de ponteiros no MD; migrar de replay em lote para entrada/estado por tic em Word RAM; medir orçamento de transferência e só então FPS/latência real. Preservar Z8 aprovada até validar nova execução no console.
