# R85: combinações sobre pré-composição

Todas usam R83 sprites + pré-composição conservadora R84.

| Nome da ROM | Mudanças adicionais |
|---|---|
| r85-control | Controle: somente pré-composição |
| r85-sram | Leitura tardia de sidedef |
| r85-reuse | Reutilização de coluna com MOVEP preservado |
| r85-all | SRAM + reutilização |

Cada conjunto gera `-pl.bin` e `-pf.bin`. O workflow r85-compare compara framebuffer por tic, vblanks no mesmo job, limites de ROM/BSS e diagnóstico parcial de pilha. As quatro combinações passaram pela aplicação local dos patches e conferência dos caminhos selecionados. Ganhos combinados ainda não medidos.

Reprodução: apply_r81.py; R80_EXPERIMENTS=P1+F1 apply_r80_performance.py; R83_CANDIDATE=sprites apply_r83.py; R85_CANDIDATE=control|sram|reuse|all apply_r85.py; build_r71a12mul_hud.py no ambiente do workflow. Cada build deve usar checkout descartável independente.
