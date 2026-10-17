# R20e — pacote de testes para amanhã

Base de todas as ROMs: R20d R2 validada no hardware em 193,87 s. Mantidos S2/visada iterativa, Flat DBRA, P2/ADDX, M1/MULS, R2/memo, inlining natural, 38x22, cache 16, hand1, HUD levantado, E1M1, zona nominal 43 KiB, sem espera explícita por VBlank. R4 permanece desligada.

| ROM | Mudança sobre o controle |
|---|---|
| doom-md-r20e-control.bin | Nenhuma opção nova; configuração da R2 validada |
| doom-md-r20e-hud.bin | Recompõe barra inferior em RAM apenas quando necessário |
| doom-md-r20e-fps.bin | Formata/escreve FPS apenas quando muda ou a área é invalidada |
| doom-md-r20e-m3.bin | Produto exato seno×distância e recíproco normalizado, locais à escala das paredes |
| doom-md-r20e-s3.bin | BSP do render iterativo; a visada já era iterativa na base |
| doom-md-r20e-r3.bin | Flat desenrolado, sem alterar cálculo de destino das colunas texturizadas |
| doom-md-r20e-all.bin | Todas as cinco opções novas juntas; experimental |
| doom-md-r20e-diag.bin | all + sondas de pilha/heaps; FPS tem overhead |

## Ordem de amanhã

1. diag: fotografar pico/reserva, erro/tic, heaps e SP. Se travar ou marcar erro, guardar a tela e não assumir que a combinação é válida.
2. control: confirmar referência da sessão, no mesmo clock/divisor. Esperados 2134 frames.
3. hud → fps → m3 → s3 → r3: fotografar cada resultado e observar paredes, céu, arma, sprites e HUD. Cada nome isola uma alteração.
4. all: comparar com a melhor variante isolada, não apenas com control. Ganhos podem não somar.
5. Hardware: começar apenas pelas candidatas aprovadas. 7,67 MHz; manter a ROM R20d R2 como referência validada.

Referência BlastEm R2: 11,15 FPS / 191,43 s. Hardware: 193,87 s. Não comparar tempos entre plataformas para decidir ganho; usar o controle da mesma sessão/plataforma. Os FPS de diag têm overhead. A instrumentação altera layout e o diagnóstico de all não valida automaticamente cada ROM isolada.

## Verificações visuais adicionais

- HUD: saúde, armadura e munição mudam corretamente; entrar/sair de menus, automapa e telas de título/intermissão não deixa texto antigo.
- FPS: continua atualizando a medição; mensagens/limpezas na primeira linha não apagam permanentemente o número.
- M3: paredes mantêm escala/perspectiva, sem tremor ou desaparecimento em ângulos rasantes. A alteração não substitui FixedMul/FixedApproxDiv globalmente.
- S3: testar cenas abertas, oclusão, sprites e automapa. Consome 192 bytes de vetores estáticos.
- R3: observar teto/chão/cores sólidas e bordas. A tabela de linhas fica em ROM; o salto calculado depende do encoding do 68000.

## O que já foi verificado antes da entrega

Testes nativos compilam os helpers reais de M3 e comparam divisores 1..2^24-1, fronteiras e 2 milhões de divisores aleatórios; produto contra referência de 64 bits; função de escala original/candidata em 2 milhões de contextos com a tabela de seno real. O teste de vídeo compila as funções reais em harness de host e compara 1000 quadros RAM+VRAM para controle, HUD, FPS e ambos, com limpezas/textos/transições. Serviços SGDK/fontes/VDP são simulados nesse teste.

O arquivo evidence/math-probe.raw é um teste freestanding para o harness Musashi, não uma ROM de jogo. Ele usa código compilado para MC68000, expectativas calculadas no host e o flat writer extraído da fonte de produção. O campo tag de STOP representa a quantidade de divergências. ELF, flags, logs, hashes, teste e fontes de evidência acompanham o pacote.

Nenhum desses testes substitui a execução completa do jogo. all é uma combinação exploratória; a base validada não foi substituída.
