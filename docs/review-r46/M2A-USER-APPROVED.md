# R46 M2A — aprovação manual DEMO3 (20/10/2026)

O usuário testou as **três ROMs R46 M2A** no BlastEm e confirmou que todas funcionam corretamente, inclusive a jogável. As capturas das duas ROMs de timedemo mostram **2134 quadros em NTSC 60 Hz**, sem regressão detectável.

| Medida | doom-md-r46-primary-perf | doom-md-r46-m2a-perf |
|---|---:|---:|
| FPS médio | 11.80 | **11.80** |
| FPS mín. 1s | 4.3 | **4.3** |
| FPS máx. 1s | 22.0 | **22.0** |
| Total de quadros | 2134 | **2134** |
| Tempo total (segundos) | 180.82 | **180.82** |
| SGDK free / largest block | 1386 / 1386 | **1386 / 1386** |
| SGDK PTR16 / header | 59460 / 2131 | 59460 / 2131 |
| Free before / after | 3516 / 1386 | 3516 / 1386 |
| Copies / uploads | 2134 / 2134 | 2134 / 2134 |
| Raw free / errors | 1386 / 0 | 1386 / 0 |

**Play:** usuário confirmou: "tres roms aceitas e funcionando corretamente".

## Conclusão
M2A foi **aprovada pelo usuário**. As tabelas de projeção da geometria 76×44 coexistem no ELF com o kernel 8×8 sem custo adicional observado no timedemo. O 4×4 **ainda não é o renderer ativo em runtime**.

A próxima fase M2B deve tratar de escala vertical, slopes de piso e teto, arrays de clipping e projeção de sprites mantendo o orçamento de memória. A passagem efetiva entre modos, incluindo reinicialização de tiles, CRAM, DMA/ISR, continua para M3/M4. Preservar as referências: 8×8 **11.80 FPS / 180.82s**, 4×4 ASM R44 **3.88 FPS / 550.30s**, paleta 4×4 original como padrão.

Build validada em CI: [#39410704916](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39410704916), [artifact 12258624070](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39410704916/artifacts/12258624070).
