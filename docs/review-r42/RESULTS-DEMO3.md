# R42 Q2 — Benchmarks DEMO3 fornecidos pelo usuário

**Data:** 20/10/2026 (execução local BlastEm, NTSC 60Hz). Todas as variantes terminaram a **DEMO3 de 2.134 quadros**. Captura apresentada pelo usuário na conversa. As três ROMs foram produzidas pelo mesmo commit do [CI #39354009419](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39354009419) ([artefato 12234372141](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39354009419/artifacts/12234372141)).

| ROM | FPS médio mostrado | Min FPS (1 s) | Max FPS (1 s) | Tempo total (s) | SGDK free/max block |
|---|---:|---:|---:|---:|---:|
| `doom-md-r42-control-p4perf` | **3.01** | 1.8 | 3.9 | **709.67** | 862 / 862 |
| `doom-md-r42-hoist-p4perf` | **3.82** | 2.0 | 5.5 | **558.00** | 860 / 860 |
| `doom-md-r42-asm-p4perf` | **3.88** | 2.1 | 5.5 | **550.32** | 860 / 860 |

## Ganhos baseados na duração para os mesmos 2.134 quadros

- **C hoist vs controle:** tempo **-21,37%**, FPS efetivo **+27,18%**, **151,67 s** economizados.
- **ASM vs controle:** tempo **-22,45%**, FPS efetivo **+28,96%**, **159,35 s** economizados.
- **ASM vs C hoist:** tempo **-1,38%**, FPS efetivo **+1,40%**, apenas **7,68 s** adicionais economizados.
- Os FPS arredondados mostrados na ROM geram variações mínimas em cálculos percentuais; os percentuais acima derivam de `2134 / tempo`.

### Conclusão técnica, sem extrapolação

A reorganização do caminho C das paredes (clipping fora do loop, salto de endereço constante de 38 bytes por scanline, escrita de nibble por paridade x) representa **a maior parte do ganho**. A implementação com `move.b/andi.b/or.b/move.b` ganha mais, mas marginalmente sobre o C otimizado. É compatível com o resultado da R41 Q1, que encontrou **46,3% das amostras em desenho de paredes**; não é uma medição de ciclos por instrução, e os dados de R41 foram obtidos por amostragem VBlank.

**A resolução permanece 76×44 amostras independentes.** Os kernels asm antigos do 8×8 `R20_REG_COLUMNS` e `FLAT_INLINE` não são utilizados no 4×4. Não extrapolar os ganhos deste microexperimento para sprite/flat/BSP nem prometer 5–6 FPS médio sem nova medição.

## Validação realizada e pendente

- ✅ Teste host C: **20.000 colunas** randomizadas equivalentes pixel a pixel para referência C versus C otimizado; 4.096 colunas/65.536 padrões do teste R22 original.
- ✅ As quatro ROMs R42 compilaram na CI e inicializaram em smoke de 300 quadros no BlastEm.
- ✅ As **três variantes PERF concluíram a DEMO3**, com FPS/tempos registrados acima.
- ⏳ **Pendente validação jogável:** `doom-md-r42-asm-p4play.bin` em E1M1 e E1M2, especialmente sprites/arma à frente de paredes, portas, texturas sobrepostas, HUD, `TITLEPIC/WIMAP0` e menus R40b (ghosting/flicker). Testar em CRT/console quando possível.
- ⏳ Pendente equivalência bit a bit específica **do assembly** em cenário real/framebuffer; o teste host não executa instruções M68k e, portanto, não constitui prova total do asm.
- ⏳ A otimização ainda não foi integrada ao dual-runtime R40c, que está no estágio M0 de backends compilados separadamente.

**Próxima decisão:** depois da validação visual do `asm-p4play`, preservar o kernel vencedor e considerar um experimento separado de `R22_DrawColumnFlat`, ou priorizar a integração dual 8×8/4×4 antes de mudanças adicionais.
