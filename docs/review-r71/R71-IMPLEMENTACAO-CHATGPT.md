# R71 — implementação e compilação conduzidas pelo ChatGPT

**Data:** 2026-10-26. **Responsável:** ChatGPT. **Cláudio:** análise independente de partida, sem dependência de implementação/execução.
**Branch:** `exp-chatgpt-r71-implementation-20261026`.
**Run:** [40390696153](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40390696153). **Estado deste registro:** cinco builds concluídos; capturas DEMO3 ainda em execução. O estado final deve ser lido no workflow; não presumir ganhos antes do comparador.

## O que foi implementado
- `DOOM_R71_OFS=1`: dois vetores `static const uint16_t` em **ROM** (22 offsets de linhas de 152 bytes e 76 offsets de colunas), usados no cálculo do endereço `R22_PixelByte` para paredes `R42_DrawPackedWall` e flats `R_DrawColumnFlat`. Sem BSS adicional. `src/r22_video.inc`.
- `DOOM_R71_B1B=1`: `R71_DrawColumnWallFast` para paredes, chamada somente via `R20_WALL_DRAW` do `R_DrawSegTextureColumn` e caminho COLPAIR `R_RenderSegLoop`. Requisitos de clipping físico/R57, estado `r64a_ctx`, LUT padrão efetiva e contagem ≥2. Se qualquer predicado falha, chama **a rotina original R42**. O céu ainda invoca a rotina original; fracstep/source/colormap reais são usados, inclusive quando `R_DrawSky` alterou `dcvars`. Preserva kernel `R60_WallColumn`.
- `scripts/lab/build_r35_linear.fish`: apenas reconhece as novas flags e valida configuração R60/R64A. Ambas inertes por padrão.
- `scripts/lab/build_r71.py`: cinco builds isolados, não instrumentados, H40/crop H16/V16: `r66-perf`, `r70a12`, `r71ofs`, `r71b1b`, `r71both`. Compila, audita flags/BSS e gera manifesto/hashes.
- `scripts/lab/test_r71_host.py`: força bruta de 3344 pixels e comparação da **função R42 extraída do arquivo real** contra a nova função B1b sob dois modos, com sanitisers; o kernel R60 é simulado no host, e a validação efetiva do m68k exige capturas BlastEm.
- `scripts/lab/check_r71_inert.py`: remove só blocos condicionais R71/R70 e compara os dois fontes do renderer com R66.
- `scripts/lab/r71_mul_callsites.py`: Rodada 0 de `__mulsi3`; extrai chamadas estáticas reais do `R_Subsector` em ELFs R66/A12, não confundir contagens estáticas com frequência dinâmica.
- `.github/workflows/r71-build.yml`: workflow **ativado por push restrito à alteração deste arquivo na branch R71**, além de `workflow_dispatch`; executa em `x360-linux`; consome WAD shareware local verificado por SHA sem publicá-lo; compila e testa, baixa artifact R66 histórico e usa `cmp` para provar controle idêntico, mede pixels e timing. Artifact final previsto: `doom-md-r71-round1`.

## Regras
- R66 é controle aprovado inalterado, ROM SHA256 `2c93cdbb78c72eabcdd2f816db6849f6dd877420a59c44424fae6b7a4ae7ca36`; R70-A12 referência rápida, não confundir referência com promoção em hardware.
- Nenhum resultado de FPS é válido antes de capturar a DEMO3 inteira no BlastEm stock clock.
- 0 diferenças de bytes por tic é obrigatório; comparar ganho não só frente à R66, mas também frente à A12.
- BSS ≤57920 bytes, ROM ≤4 MiB, não misturar R70-D (abandonada).
- Comparador só chama de *fastest* uma variante estritamente mais rápida e com framebuffer pixel-idêntico.
- Demais linhas B2/B3/C1/MUL (otimização)/W continuam fora da primeira rodada; MUL neste workflow é **só diagnóstico de calls**.

## Incidentes e correções
- A primeira run [40389798195](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40389798195) falhou no **harness de viewport antigo**, que extraía a rotina R42 sem o novo auxiliar OFS: corrigido com `#if DOOM_R71_OFS` local nas duas chamadas.
- A segunda run [40390125736](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40390125736) passou pelos oráculos antigos e falhou por colisão de nome `mode_t` no **harness nativo novo** com `sys/types.h`: corrigido para `r71_mode_t`.
- A terceira run [40390696153](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40390696153) passou no host e compilou cinco ROMs; a R66 também foi comparada byte a byte com o artifact histórico antes das capturas. Consultar workflow para o resultado final.

**Importante:** não modificar a R66 original nem gerar uma conclusão de desempenho a partir das porcentagens esperadas no handoff. Ganhos serão somente os medidos.
