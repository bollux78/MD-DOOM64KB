# R46 M1B — próximo estágio preparado para compilação

## Origem e referência (usuário, 20/10/2026)

A R46 M1A foi aprovada: `doom-md-r46-primary-perf` e `doom-md-r46-m1-perf` fecharam a DEMO3 de **2134 quadros a 11,80 FPS / 180,82 s**, com mínimo 4,3, máximo 22,0. `r46-m1-play` teve gráficos e som corretos. M1A já reúne o renderer R39f 8×8 e as rotinas R44 ASM 4×4 na mesma ROM, usando o buffer `_s_screen[38*28]` de **2128 bytes**, sem segundo framebuffer. A M1A aprovada está na branch separada `r46-dual-m1-engine`, CI [#39363640958](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39363640958).

**O runner será desligado até amanhã.** Esta branch `r46-m1b-video-prep` foi criada para deixar código e workflow prontos. Não declarar compilação/benchmark M1B concluídos antes do resultado de CI.

## O que a M1B adicionou

`src/r46_pixel4_vram.c/.h` contém o segundo estágio de coexistência: funções C efetivas de empacotamento 4×4 em padrões e índices de tiles, usando **a mesma representação do R22 original**, compiladas ao lado do R39f 8×8:

- `R46_P4_TileAt(bank,x,row)` — índice do tile sólido 0–15 ou índice dinâmico; bancos 0/1, mapa nas linhas 1–21, colunas 0–37.
- `R46_P4_MapRow(bank,row,output[38])` — preenche somente uma linha de **76 bytes fornecidos pelo chamador**, sem alocar `r22_map[798]` extra na WRAM.
- `R46_P4_PatternRows(x,row,output[8])` — produz as oito palavras de 32 bits (32 bytes) do tile, com quatro linhas para cada metade de 2 pixels amostrados na vertical.
- `R46_P4_VramOps()` fornece a tabela de funções; `R46_P4_VramValidate()` verifica os endereços e a presença das funções **sem acessar o framebuffer ativo nem escrever no VDP**.

O framebuffer 4×4 continua a ocupar 1672 bytes dos 2128 bytes já existentes; a ocupação não deve aumentar por uma nova matriz global. O primeiro tile dinâmico é 54 no banco 0 e 890 no banco 1; o último é **1687**, antes dos caracteres SGDK a partir de **1696**. Os primeiros 16 padrões são sólidos, e a primeira linha de VDP permanece reservada a texto/FPS.

**Sem escrever no VDP:** intencionalmente não se instalou um novo callback, upload de tiles, paleta, menu, mudança de projeção ou transferência DMA. As funções que leem `_s_screen` NÃO podem ser usadas durante renderização 8×8; nesta etapa só `R46_P4_VramValidate()` é chamada na inicialização. A geometria permanece 38×22 até M2.

## Testes e fluxo da compilação

A nova workflow `.github/workflows/r46-m1b-video.yml` contém:
- Teste host `python3 scripts/lab/test_r46_m1b_vram.py`: compila o C real com `cc` e compara dois bancos e 40 framebuffers (incluindo monocromáticos e multicoloridos), usando o formato original R22 como referência; testa mapa, padrão e ausência de escrita na RAM de origem.
- Preflight do código R46/M1A, testes de kernels ASM 4×4 e intermissão.
- ROM 8×8 controle: `doom-md-r46-primary-perf.bin`.
- ROMs 8×8 com M1A + M1B vinculadas: `doom-md-r46-m1b-perf.bin` e `doom-md-r46-m1b-play.bin`.
- Auditoria por `m68k-elf-nm` de `R46_P4_VramOps`, `R46_P4_TileAt`, `R46_P4_MapRow`, `R46_P4_PatternRows`, `R46_P4_VramValidate` e kernel asm `R46_P4_Wall`; comparação da `.bss`.
- Cabeçalho ROM linear, tamanho real ≤4 MiB, flags e smoke 300 frames no BlastEm.

O workflow está configurado para a **branch M1B** com push e execução manual: ao voltar o runner ele poderá processar o job enfileirado, se ainda não tiver expirado. Se a fila expirar, reexecutar ou disparar manualmente o workflow (uma alteração/commit na branch também o reaciona). Nenhum benchmark numérico M1B foi medido ainda.

## Critérios para considerar M1B aprovada

1. CI verde incluindo host oracle, cross-link e 300 frames em BlastEm.
2. `m1b-perf` terminar DEMO3 2134 frames com comportamento idêntico ao controle (meta de **11,80 FPS / 180,82 s**).
3. `m1b-play` preservar 8×8, Off/Checker/Vertical, menus, música XGM2, SFX e transição E1M1→E1M2.
4. Nenhuma nova alocação de 1596/1672 bytes; conferir tamanho `.bss` com comparação linkada.

## Engenharia posterior

**M2:** geometria de projeção e clipping independentes em 38×22 e 76×44 no mesmo ELF; verificar BSP, visplanes, escala de sprites, arma e hot loops. **M3:** transferência de propriedade de `_s_screen` após drenar DMA e desabilitar o antigo pipeline VBlank; inicializar/reconfigurar CRAM, VRAM, padrões, WINDOW e HUD sem ghosting. **M4:** permitir o toggle Render 8×8 / 4×4 com mapa/jogador preservados, medir DEMO3 em ambos.

O 4×4 original R44 ASM **3,88 FPS** é a referência posterior; preservar paleta original como padrão, cinza seletivo em chão/teto será pesquisado depois, com prioridade baixa.
