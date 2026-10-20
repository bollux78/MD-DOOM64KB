# R44 ASM — usuário confirmou ROM jogável, troca de fase, intermissão e desempenho

**Origem da evidência:** capturas e confirmação explícita do usuário nesta rodada de testes do BlastEm. A ROM `doom-md-r44-asm-p4play` funciona durante a partida; troca de fase e textos foram aprovados visualmente.

## DEMO3 NTSC — 2.134 quadros

| ROM | FPS médio | FPS mín. (janela 1 s) | FPS máx. (janela 1 s) | Tempo total |
|---|---:|---:|---:|---:|
| `doom-md-r40ci-p4perf` | 3,01 | 1,8 | 3,9 | **709,67 s** |
| `doom-md-r44-asm-p4perf` | **3,88** | **2,1** | **5,5** | **550,30 s** |

**Comparação entre renderizadores 4×4:** +28,96% em throughput de quadros e redução de ~22,46% no tempo total de execução (159,37 s); mesmo número de quadros. R44 continua em 76×44 amostras independentes. Em relação à R42 ASM de 550,32 s e 3,88 FPS, a alteração na intermissão é neutra na precisão das medições disponíveis.

## Validação funcional do usuário

- `r44-asm-p4play` **aprovada**: gameplay, troca de fase e textos corretos na intermissão. O usuário informou: "tudo certo na r44 play, troca de fase, textos. tudo ok".
- Layout de intermissão corrigido: 38×22 posições de caracteres de 8×8, independentemente de o renderer 3D trabalhar em 76×44 amostras.
- Teste anterior da tela E1M1 com títulos, Kills/Items/Secret e Time/Total/Par demonstrou que o texto está legível e corretamente centralizado. Anti-flicker/ghosting da R40b preservado.
- Todos os 2.134 quadros da DEMO3 terminam e permanecem na mesma faixa de desempenho da R42 ASM.
- **Ainda não foi confirmada pelo usuário, nesta rodada, a aparência da paleta cinza R43.** Não confundir a aprovação da R44 com aprovação de qualquer remapeamento cromático.

**Consequência:** a R44 ASM é a referência 4×4 aprovada funcional e quantitativamente. A correção da intermissão deve ser carregada para a branch de integração dual e para eventuais testes posteriores de paleta, sem substituir nem apagar as bases aprovadas.
