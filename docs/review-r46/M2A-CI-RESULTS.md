# R46 M2A — resultado de compilação e próximo teste manual

**Registro de referência:** A R46 M1B foi aprovada pelo usuário no BlastEm (DEMO3 de 2.134 quadros, **11,80 FPS / 180,82 s**, mínimo 4,3, máximo 22,0; memória livre SGDK 1386 B; `m1b-play` com gráficos e áudio corretos). Essa é a base de regressão para M2A.

## R46 M2A compilada

[GitHub Actions #39410704916](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39410704916) **SUCCESS**, [artefato 12258624070](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39410704916/artifacts/12258624070).

- `doom-md-r46-primary-perf.bin` — controle R39f 8×8.
- `doom-md-r46-m2a-perf.bin` — controle 8×8 + kernels M1B 4×4 + dados/projeção 76×44 originais co-linkados.
- `doom-md-r46-m2a-play.bin` — versão jogável, ainda usando exclusivamente 8×8 como geometria ativa.
- Os dados X→ângulo do R22 possuem **77 entradas (76 colunas mais 1 borda)**; a tabela de ângulo→coluna tem **2032 entradas**. Teste host comparou 77 bordas e todos os **4096 ângulos finos**, aprovado.
- ROMs lineares `2.752.512` bytes, símbolos vinculados verificados via `m68k-elf-nm`, as três inicializaram por 300 quadros no BlastEm, código de apresentação VDP da M1B permaneceu inativo.

### Orçamento do executável (CI)

| Métrica | Controle | M2A |
|---|---:|---:|
| Text | 2.674.580 B | 2.677.396 B |
| Data | 452 B | 452 B |
| BSS | 57.724 B | **57.692 B** |
| ΔBSS | — | **−32 B** |

A diferença negativa na BSS não significa que o código custe memória negativa; decorre de composição, otimização e layout do link. **Nenhuma segunda tabela de projeção foi alocada em BSS**, e sim na ROM.

## Testes humanos pendentes

Executar `primary-perf` e `m2a-perf` até DEMO3 2134 quadros. Esperado **11,80 FPS / 180,82 s**, porém ainda não medido pelo usuário na M2A. Testar `m2a-play` para assegurar áudio e gráfico 8×8 sem regressão.

## Próximo estágio real

A M2A resolveu **apenas as tabelas horizontais 76×44 em ROM**. Ainda são necessários os caminhos separados de escala vertical, BSP/clipping, visplanes, projeção de sprites e arma, reaproveitamento seguro de buffers e só depois um dispatcher de geometria. A M3 cuidará de troca VRAM/CRAM/ISR; M4 habilitará o toggle no menu. Não alegar que o 4×4 já desenha em runtime.
