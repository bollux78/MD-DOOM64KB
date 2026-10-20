# R46 M1B — validação manual concluída, sem regressão

**Evidência:** usuário confirmou por capturas do BlastEm que os dois timedemos DEMO3 (NTSC 60 Hz) completaram 2134 quadros e que a ROM `m1b-play` funciona corretamente, inclusive áudio e gráficos.

| Medida | R46 primary controle 8×8 | R46 M1B 8×8 + módulos 4×4 |
|---|---:|---:|
| FPS médio | **11,80** | **11,80** |
| FPS min (janela 1 s) | 4,3 | 4,3 |
| FPS max (janela 1 s) | 22,0 | 22,0 |
| Quadros | 2134 | 2134 |
| Tempo | **180,82 s** | **180,82 s** |
| SGDK free / largest block | 1386 / 1386 B | 1386 / 1386 B |
| Copies/uploads | 2134 / 2134 | 2134 / 2134 |
| RAW free/errors | 1386 / 0 | 1386 / 0 |

O `m1b-play` também foi testado pelo usuário e aprovado.

### CI automatizada

[Run #39407114064](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39407114064), [artefato #12258156636](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39407114064/artifacts/12258156636) — SUCCESS:
- Oracle VRAM C em 40 framebuffers e dois bancos; skip-solid Q3
- Módulo ASM R44 e preparação de tile patterns 4×4 vinculados ao mesmo executável R39f 8×8
- ROMs de tamanho real 2.752.512 B, boot BlastEm 300 frames 3/3
- BSS controle 57.724 B; BSS M1B 57.692 B (**-32 B**, sem framebuffer adicional)
- Layout VDP comum **não** ativado; modo 8×8 ainda é o único ativo

### Conclusão

**M1B aprovada** sem regressão detectável de FPS, SGDK heap ou comportamento. R46 pode avançar à **M2 geometria/projeção**. Este documento é registro factual da execução M1B, não confirmação de modo 4×4 em runtime.
