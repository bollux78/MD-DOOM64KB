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

## Validação da entrega

Build c0e3eaeb1462c0cb374baaaac933f2ca11cdc764.
CI: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39133912270

Passaram os testes do fluxo de abertura/Start e do leitor real de cabeçalho
de demo em builds timedemo e jogável. A auditoria dos binários confirmou
DEMO3 e todos os nove lumps de E1M1 idênticos entre control e perf.
O diagnóstico MC68000 completou 18 carregamentos médio/difícil, sem erro
de heap e com ROM/SRAM alternando corretamente. Não é validação visual
do VDP nem reprodução completa do timedemo no hardware.

ROMs do episódio: 3.276.800 bytes; controles: 1.835.008 bytes.
Os seis hashes do artefato foram conferidos.
