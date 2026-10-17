# R20g — RAM, render e DMA: 36 ROMs

Base: R20f-all, 2134 frames, BlastEm 11,54 FPS / 184,90 s; mínimo 4,7 máximo 19,4. R20f-control 11,15 / 191,43; HUD 11,33 / 188,32. R20f-diag: erro 0/tic 0, pico 2368/2560, SGDK 3124/3124, zona 912/528, SP E0FFF716. A R20f ainda depende de confirmação no hardware. R20d-R2 segue como referência hardware em 193,87 s.

Todas as ROMs R20g mantêm S2/S3 iterativos, P2, M1, M3, R2, HUD/FPS sob demanda, Flat DBRA, cache16, 38x22, hand1, música E1M1, zona 43 KiB e sem espera explícita por VSync. R3 e R4 desligadas. Cada variante possui uma parceira diag-NOME, com as mesmas flags mais diagnóstico; seus FPS têm overhead.

| Sufixo após doom-md-r20g- | Única mudança sobre control, salvo combinações explícitas |
|---|---|
| control | Configuração R20f-all |
| color | S6: colorcell[256] em ROM, -512 B RAM |
| sprites | S6: sprtemp temporário na zona durante init e liberado; -638 B estáticos, +ponteiro |
| cache | S6: composição direto no slot de cache; -128 B e cópia removida no miss |
| ram | color + sprites + cache |
| r4b | Hash/tag/máscara de textura composta preparados por segmento/tier |
| r5 | Coluna de parede com ABI privado em registradores; cellmap selecionado por seg e atualizado se o céu mudar o colormap; mascaradas/sprites mantêm caminho antigo |
| r6 | Flat DBRA integrado ao seg loop; cor convertida uma vez por seg; sem R3 |
| m2 | Multiplicação decomposta apenas para tangentes de 32 bits; M1 continua no ramo de 16 |
| p3 | ADD/ADDX desenrolado para até 22 células; P2 original no fallback |
| s5 | DMA_initEx com fila32 e buffer2 KiB, alocação do buffer verificada |
| m4 | Clobber cc do helper mulu e fallback definido para coluna multipatch descoberta |
| v3 | DMA em lote: autoincremento e barramento Z80 configurados uma vez; DMA ainda imediata |
| ram-v2 | ram + snapshot de vídeo transferido no callback VBlank, usando SGDK DMA |
| ram-v2-v3 | ram + VBlank + DMA em lote |
| render | r4b + r5 + r6 + m2 + p3 |
| ram-render | ram + render |
| full | ram + render + V2 + V3; exploratória, não presumir melhor |

Total: 18 variantes, cada uma com diagnóstico = 36 ROMs. matrix.json e flags por ROM são auditados no build. Os diagnósticos dos builds são independentes: diag-control não valida outras ROMs.

## Ordem de teste

1. diag-control → control (referência da sessão, mesmo clock/divisor).
2. Para cada variante isolada color/sprites/cache/ram/r4b/r5/r6/m2/p3/s5/m4/v3: diag-NOME → NOME. Se diagnóstico travar ou marcar erro, guardar tela e nome.
3. diag-ram-v2 → ram-v2 → diag-ram-v2-v3 → ram-v2-v3.
4. Diagnóstico correspondente → render → ram-render → full. Comparar combinações com melhores isoladas; ganhos não são aditivos.
5. Hardware: testar primeiro as aprovadas no BlastEm, a 7,67 MHz. Informar FPS min/méd/max e tempo; observar paredes, chão/teto, sprites, arma, HUD, transições e som. Se V3 causar problema de música/PCM, informar mesmo que a demo complete.

## Particularidades do V2

Snapshot completo 38x28 = 2128 B adicionais (456 B a mais que a proposta de somente viewport). Isso isola o HUD de escritas do próximo quadro. Só as 22 ou 28 linhas necessárias são copiadas e enviadas. A paleta acompanha o mesmo snapshot. O render continua no framebuffer principal; só espera se já existe snapshot pendente.

A DMA só começa com V counter NTSC entre 224 e 232, reservando espaço no blank; callback tardio adia para o próximo. Um timeout de 180 VBlanks mostra erro, em vez de esperar indefinidamente. Resultados e setup de vídeo drenam a transferência antes de acessar o VDP; erro cancela a pendência antes do shutdown. V2 é experimental e não equivale a validar VBlank no hardware por testes de CPU.

S5 é isolada e não entra em full; sua mudança de alocações SGDK exige diagnóstico próprio. RAM liberada permanece no heap do SGDK, salvo o sprtemp de init, que é alocado/liberado na zona Doom. A reserva de pilha continua 2560 B: ganhar heap não aumenta a pilha automaticamente. Não se reduziram limites de drawsegs/openings com base apenas nesta demo.

## Verificações automáticas

- Cobertura real de todas as 6712 colunas compostas deste WAD, altura alinhada <=128. Build falha se outro WAD introduzir lacunas que tornem a composição direta diferente do buffer temporário.
- Wrapper R5 verificado para mudança de colormap pelo céu, reutilização, fallback e coluna vazia.
- Funções C reais de hash/cache comparadas em 507904 cenários de colisão.
- Publicador/callback de V2 em harness de host: 1000 snapshots, IRQ tardia, extensão do HUD, mudança de paleta e cancelamento. VDP e interrupções simulados; não mede timing real.
- Probe MC68000 compila os escritores P2/P3 reais, o kernel R5 com wrapper de registradores e o flat R6, compara colunas e regiões intocadas. Executado externamente em Musashi antes da entrega; arquivos .raw não são ROMs de jogo.
- Flags, ELF, layout de RAM, hashes e identificadores conferidos por ROM. Tudo isso não substitui a execução completa no console.
