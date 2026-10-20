# R45 — benchmarks e avaliação visual do usuário (DEMO3 completa)

**Confirmação:** as três ROMs PERF concluíram a DEMO3 de 2.134 quadros no BlastEm NTSC 60 Hz. A `r45-cell-play` foi confirmada funcionando. A variante R45 Gray foi considerada **correta segundo o pedido original**, mas o usuário **não conseguiu concluir que seja visualmente melhor** que a versão normal. A nova prioridade é a integração dual; a mudança de paleta não deve bloquear o desenvolvimento.

| ROM | FPS médio | FPS mínimo (janelas de 1 s) | FPS máximo (janelas de 1 s) | Tempo DEMO3 (segundos) | SGDK free / max block |
|---|---:|---:|---:|---:|---:|
| `doom-md-r45-cell-perf` | **11,80** | 4,3 | 22,0 | **180,82** | 1386 / 1386 |
| `doom-md-r45-asm-p4perf` | **3,88** | 2,1 | 5,5 | **550,30** | 856 / 856 |
| `doom-md-r45-gray-p4perf` | **3,86** | 2,0 | 5,5 | **552,75** | 856 / 856 |

**R45 gray comparada à ASM normal:** +2,45 s no mesmo timedemo, equivalente a ~0,445% mais tempo ou ~0,443% menos FPS efetivo. Não tratar essa única medição como penalidade significativa nem garantir igualdade bit a bit. A reserva de 4×4 AMS continua em 3,88 FPS sem regressão e o 8×8 mantém 11,80 FPS.

## Preferência de cor atualizada

> "gray OK mas nao sei dizer se é melhor. mas está de acordo com o pedido. o ideal é que chao e teto fossem cinzas paredes poderiam continuar como estavam. nao é prioridade."

**Decisão:** manter **paleta original R44 como padrão** e R43/R45 Gray como experimento opcional, sem promover automaticamente o cinza global à ROM dual.

A paleta 4×4 atual é compartilhada entre paredes, flats, sprites e arma; a LUT `r22_color[256]` não distingue material. No futuro, para dar preferência a cinza em **chão/teto** e preservar as **paredes anteriores**, considerar desenho especializado em `R_DrawColumnFlat` ou mapeamento condicionado por material, com a ressalva de que cores partilham apenas 16 slots e podem exigir revisão da distribuição da paleta. Antes de implementar, criar referência visual e validar que não recolore indiscriminadamente portas/inimigos. **Baixa prioridade.**

## Próximo objetivo de implementação

Começar verdadeira coexistência de 8×8 e 4×4 no **mesmo ELF/ROM**, seguida da geometria dinâmica, VRAM/CRAM, ISR e Options; não confundir as seis ROMs compiladas independentemente da R45 com uma ROM já capaz de alternar resolução em runtime. Preservar Off/Checker/Vertical no 8×8 e R44 ASM/intermissão no 4×4. Os números acima são controle de regressão para o futuro código dual.

**Fonte:** capturas do usuário nesta conversa. CI do pacote original: [#39360378906](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39360378906); [artifact #12237107601](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39360378906/artifacts/12237107601).
