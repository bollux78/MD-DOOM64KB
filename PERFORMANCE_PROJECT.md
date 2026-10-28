# Projeto de desempenho R80

O projeto está em **[docs/performance-r80/README.md](docs/performance-r80/README.md)**.

- [Plano técnico e sugestões](docs/performance-r80/PROJETO.md)
- [Pedido ao agente, com autorização para implementar candidatos isolados](docs/performance-r80/PROMPT.md)
- [Hook de implementação](scripts/lab/apply_r80_performance.py)
- [Preparação de controle/candidato](scripts/lab/prepare_r80_performance.py)
- [Workflow com acionamento explícito](.github/workflows/r80-performance.yml)

Base: R79 aceita, sem shadow adaptativo. O hook inicial é inerte. A publicação deste projeto não executou novo benchmark nem iniciou build R80.
