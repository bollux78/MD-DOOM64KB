# R26 — abertura e timedemos comparáveis

Base R25 validada pelo usuário: todas as fases jogáveis, músicas corretas e
transição E1M1 → E1M2 funcionando.

## Jogáveis

- doom-md-r26-episode-play.bin: episódio completo 8×8.
- doom-md-r26-episode-p4.bin: episódio completo 4×4.

A imagem de abertura aparece primeiro com a música Intro. Aguarda Start para
abrir o seletor E1M1–E1M9; A confirma e abre a dificuldade. Start durante o
jogo continua abrindo o menu normal. Ao fechar o seletor, volta à abertura.

## Timedemos

- doom-md-r26-control.bin: arquitetura antiga 8×8, WAD antigo.
- doom-md-r26-episode-perf.bin: arquitetura do episódio completo 8×8.
- doom-md-r26-play-control.bin: controle jogável antigo, para referência.

DEMO3 contém E1M7 no cabeçalho. O WAD antigo tinha E1M7 como cópia exata de
E1M1: todos os nove lumps foram comparados. O WAD completo tem E1M7 real,
por isso R25-perf e control mostravam cenários e resultados diferentes.

R26 mantém os bytes de DEMO3 e força E1M1 apenas nos builds TIMEDEMO, em
ambas as arquiteturas. Assim gravação, dificuldade, geometria, objetos e
sequência de comandos ficam alinhados. Os mapas jogáveis não são remapeados.
As músicas E1M1 são os arranjos de cada arquitetura, como nos controles R25.
Use as duas ROMs R26 na comparação; não misture resultados de R25-perf.

Inclui ELF, flags e relatórios. As músicas e a arquitetura SRAM da R25 são
mantidas. Validar visualmente abertura/Start e comparar os timedemos no mesmo
hardware a 7,67 MHz.
