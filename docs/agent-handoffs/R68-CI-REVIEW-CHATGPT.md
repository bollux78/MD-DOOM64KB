# R68 CI — revisão independente (ChatGPT, 25/10/2026)

**Estado:** PROPOSTO; **nenhum workflow novo ativado ou executado**.  
**Responsável por esta revisão:** ChatGPT.  
**Branch:** `exp-chatgpt-r68-ci-review-20261025` (derivada de `exp-claudio-r68-profiling-20261025 @ 6a4b650`).  
**Controle:** `exp-r66-claudio-colpair @ f5a9daa7a0bd7225bbc227630defc73c67c34f1e`.

## O que já existe

Cláudio publicou `scripts/lab/build_r68.py`, `scripts/lab/r68_capture.py` e testes em host, além de `docs/agent-handoffs/proposals/r68-prof-build.workflow.proposal.yml`. R68 ainda não tem build m68k nem captura BlastEm publicada. A proposta utiliza o runner `[self-hosted, linux, x64]`, faz controle R66 + ROM R68 instrumentada, confere BSS, baixa artifact R66 do run `40231459814`, compara binários e tenta captura de no máximo 10.000 frames emulados.

## Revisão de segurança e confiabilidade

1. **Permissão faltante:** `actions/download-artifact@v4` consulta artifact de outra execução usando `github.token`; o workflow original só concedia `contents: read`. Acrescentar **`actions: read`**.
2. **WAD:** o workflow original permite baixar automaticamente WAD de mirrors externos se não estiver no runner. Em runner self-hosted, preferir **falhar se o WAD pinado não estiver disponível**, evitando rede externa e alterações inesperadas. A proposta revisada faz isso.
3. **Credenciais do checkout:** definir `persist-credentials: false` para minimizar credenciais persistentes no workspace.
4. **Artefatos em falha:** usar `if: always()` no upload para reter logs/manifesto parciais quando etapas de build/captura falharem.
5. **Reprodutibilidade:** o `cmp` com artifact R66 anterior é um gate importante, mas confirmar que `download-artifact` encontra o arquivo no diretório esperado; não ignorar mismatch.
6. **Risco de `NumPy` remoto:** a proposta ainda instala NumPy via pip caso ausente. Preferir ambiente já provisionado no runner; se faltar, solicitar autorização antes de permitir instalação dinâmica.
7. **Captura diagnóstica:** `R68` tem overhead de instrumentação; o relatório não é benchmark de FPS. Os 10.000 frames emulados não cobrem necessariamente os 2.134 quadros de jogo do DEMO3.
8. **Limite de memória:** o script de build impõe BSS <= 57.920 B e R68 <= R66 + 8 B; conferir ELF e mapa após build.
9. **Workflow manual:** manter somente `workflow_dispatch`, sem `push`, `pull_request`, cron ou `cancel-in-progress`; o grupo de concorrência é exclusivo.
10. **Proteção do runner:** não permitir disparo de código não revisado em branches arbitrárias; ativação e primeiro dispatch precisam de autorização humana. Antes do primeiro uso, conferir checkout/ref real e o SHA da R68.
11. **Escopo:** nenhuma modificação do código da R68, da baseline R66 ou das branches do Cláudio.

## Próximas etapas propostas

- Cláudio confirma o contrato de outputs de `build_r68.py` e `r68_capture.py` e comenta os pontos acima.
- ChatGPT e mantenedor revisam a versão final da proposta, inclusive a disponibilidade do WAD/NumPy e os passos de rede.
- **Somente após autorização adicional para ativar e executar:** mover o YAML revisado para `.github/workflows/r68-prof-build.yml` na branch experimental apropriada; configurar o gatilho manual, executar uma única vez e inspecionar logs.
- Publicar ROM/ELF, `MANIFEST.json`, BSS, `capture/report.md` e logs como artifact, sem declarar desempenho de R68.

## Status da proposta

O arquivo `docs/agent-handoffs/proposals/r68-prof-build.reviewed-by-chatgpt.yml` é um **rascunho de revisão, não um workflow executável**. Ele ainda exige inspeção humana e possível ajuste do ambiente NumPy antes de ativação.
