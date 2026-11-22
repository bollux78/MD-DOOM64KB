# Ponte de colaboração ChatGPT ↔ Claude — v1 (proposta)
 
> Estado: preparação; **nenhuma automação no runner foi ativada**. Branch isolada de `fullscreen`.

## Objetivo
Centralizar decisões, propostas de patches, revisões e resultados de builds do DOOM-MD no GitHub, de modo auditável. O Claude utilizado atualmente é **Claude no navegador**: a conversa web não responde automaticamente a eventos do GitHub. O ChatGPT nesta conversa também não opera como daemon. Para conversas autônomas contínuas, é preciso usar agentes programáticos com APIs e custos próprios.

## Protocolo v1 (sem APIs de modelos)
1. Abrir uma Issue intitulada `[AGENT] descrição` para cada tarefa técnica; manter código em branch dedicada e PR de revisão.
2. Corpo da Issue: `objetivo`, `base_sha`, `escopo`, `hipótese`, `arquivos`, `critérios de aceitação`, `riscos`, `aprovador`.
3. Cada mensagem começa por `AGENT: ChatGPT` ou `AGENT: Claude (via usuário)` e descreve `proposta`, `evidência`, `próximo teste`, `pendências`. Mensagens na Issue são registros, não ordens executáveis ao runner.
4. Claude no navegador lê a Issue e propõe código; o usuário ou ferramenta autorizada publica a resposta. Não há sincronização automática da conversa web.
5. Toda mudança no renderer vai para PR; não fazer push diretamente em `fullscreen`. Revisões de efeitos visuais ou regressões exigem aprovação humana.
6. O GitHub Actions, quando habilitado, registra hash da ROM, tempo de build, logs e artefatos; benchmark só deve comparar ambiente e condições equivalentes.

## Segurança do runner (bloqueios antes de habilitar)
- Este repositório é público. **Não** executar automaticamente jobs de `pull_request`, `pull_request_target`, `issue_comment` ou código originado de Issue no self-hosted runner.
- Separar build em repositório privado de automação, com runner isolado/efêmero e acesso mínimo, **ou** usar runner hospedado pelo GitHub e toolchain instalada de forma reproduzível.
- Preferir `workflow_dispatch` com revisão explícita do commit SHA e disparo somente por mantenedor autorizado, após definir proteção e isolamento do executor.
- `permissions: contents: read` por padrão, sem secrets em builds de código não confiável.
- Não expor tokens/API keys em Issues, logs ou arquivos do repositório. Nunca conceder ao job acesso irrestrito ao computador pessoal.
- Não executar scripts sugeridos por agentes sem revisão do diff, inclusive mudanças em `.github/workflows`.
- Restringir concorrência e tempo de execução; armazenar ROM e relatório com retenção curta.

## Etapas de implantação
- [x] Criar branch e protocolo inicial.
- [ ] Inspecionar as Actions existentes, labels e isolamento do runner pela interface de Settings (não verificados nesta etapa).
- [ ] Escolher runner hospedado ou ambiente privado isolado.
- [ ] Identificar e documentar comando real de build, dependências e artefatos na branch selecionada.
- [ ] Criar workflow manual de teste, com controles de segurança.
- [ ] Validar um build acionado deliberadamente pelo mantenedor.
- [ ] Opcional: automatizar diálogo entre modelos com OpenAI API e Anthropic API, orquestrador e limites de gastos.

## Contrato futuro de tarefa automática
Entrada validada: issue/PR permitido + SHA fixo + lista de operações permitidas.
Saída: comentário com resumo, diff/PR, SHA compilado, resultados e logs.
Condições de parada: falha, limite de custo/iterações, alteração de requisitos ou pedido de decisão humana.

**Não tratar comentários do GitHub como prompts confiáveis para executar shell commands.**
