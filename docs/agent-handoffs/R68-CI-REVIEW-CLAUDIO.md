# R68 CI — revisão independente do Cláudio sobre a proposta do ChatGPT

Escopo: `docs/agent-handoffs/proposals/r68-prof-build.reviewed-by-chatgpt.yml`
(branch `exp-chatgpt-r68-ci-review-20261025` @ 8b25004). Revisão estática; nada foi
executado nem ativado. A branch do ChatGPT não foi modificada.
R68 é experimento de **profiling**, não novo baseline (controle: R66, 7,21 FPS).

## Veredito
**Quase pronto. Não ativar ainda**: 3 correções obrigatórias (A1–A3) e 4 recomendadas (B1–B4),
mais verificações no runner (C). Nenhuma delas muda o desenho; são pequenas.

## 1. O que está correto
- `workflow_dispatch` apenas, sem push/pull_request; concurrency `r68-prof-build`, `cancel-in-progress: false`.
- `permissions: contents: read` + `actions: read`: **correto e necessário** para `download-artifact` com `run-id` (o meu rascunho omitia `actions: read`).
- `persist-credentials: false`: compatível com `fetch-depth: 0` e com `git archive f5a9daa…` (tudo local, sem rede).
- Remoção do download de WAD por espelhos: correta (sem rede no runner; hash e tamanho continuam checados).
- `if: always()` no upload: correto — evidência parcial é útil numa captura que falha.
- Limite de 10.000 quadros emulados: **respeitado**. `r68_capture.py` cria um único `RSP(...)` → um único `blastem -b 10000`; o default do script também é 10000 e o passo repete explicitamente.
- Nome do artefato do R66 (`doom-md-r66-cl-approx-colpair-perf-play`, run 40231459814) confere com `r66-colpair-build.yml`; esse artefato sobe `dist/r66/` inteiro, que contém `doom-md-r60-r66-perf.bin`; `download-artifact` extrai plano em `path`, então o `cmp` em `dist/r68/original-control/doom-md-r60-r66-perf.bin` está no caminho certo.
- Nomes de ROM/ELF/MANIFEST (`doom-md-r60-r66-perf`, `doom-md-r60-r68-prof-perf`, `.bin/.elf`, `MANIFEST.json` com `rom`, `bytes`, `sha256`, `bss_bytes`) conferem com `build_r68.py`; verificação BSS ≤ 57.920 e ≤ controle+8 idêntica à do script.
- Caminhos de ferramenta (`~/mars/m68k-elf/bin/m68k-elf-{size,nm}`) iguais aos workflows existentes; `r68_capture.py` usa o mesmo caminho por padrão (`M68K_NM` só como override).
- Saídas suficientes para profiling: ROMs+ELFs, flags-*.txt, MANIFEST, BUILD.log, CAPTURE.log, `capture/{frames.jsonl,rings.json,summary.json,report.md}`, logs de teste/inércia.

## 2. Correções obrigatórias
- **A1 — Garantir que está rodando o commit certo.** `git archive f5a9daa…` só funciona se o dispatch for da branch R68 e o arquivo de workflow existir nela (ou o commit existir no clone). Adicionar passo inicial que registra `git rev-parse HEAD` em `dist/r68/SOURCE.txt`, falha se `f5a9daa7a0bd7225bbc227630defc73c67c34f1e` não for ancestral (`git merge-base --is-ancestor`) e, idealmente, se `HEAD` ≠ SHA aprovado pelo mantenedor (input fixo no YAML ou `github.sha` impresso para conferência). Sem isso um dispatch por engano a partir de outra branch “passa” medindo a coisa errada.
- **A2 — Timeout próprio no passo de captura.** `r68_capture.py` tem `--timeout` default 120 s (espera de leitura RSP). Passar `--timeout` explícito e colocar `timeout-minutes: 45` nesse passo, para não prender o runner compartilhado (o job inteiro tem 240 min).
- **A3 — Ordem e semântica do `cmp` do controle.** O `cmp` deve continuar *fail-hard* (não ignorar divergência), mas rodar **antes** da captura (já está) e o resultado precisa ficar no log/artefato (`sha256sum` de ambos, não só do reconstruído). Se o artefato do run 40231459814 expirou (retenção), o passo falhará no download: tratar como “controle não verificável”, **não** trocar silenciosamente por outro; avisar o mantenedor (ver C3).

## 3. Recomendadas
- B1 — Remover o bloco morto `if False:` com URLs de espelhos (código inerte com URLs externas em arquivo que o runner executa; confunde auditoria).
- B2 — Descoberta do BlastEm: usar o mesmo glob de `r66-colpair-build.yml` (`Path.home()/'Projetos'` + `glob('**/blastem')` + `os.access X_OK`) em vez de `find … | head -n1` sob `pipefail` (SIGPIPE pode derrubar o `$(…)`); imprimir o caminho e `blastem` versão no log.
- B3 — NumPy: o fallback `pip install` via venv é o mesmo dos workflows existentes; aceitável, mas é rede dinâmica no runner. Decisão do mantenedor: manter (consistente com R66) ou falhar com mensagem pedindo provisionamento. Se mantido, fixar versão exata.
- B4 — Registrar `uname -a`, carga (`uptime`) e `nproc` em `dist/r68/ENV.txt`: o runner é compartilhado e o profiling por amostragem de PC é sensível a carga (as contagens de PC são em quadros emulados, então o *perfil* é determinístico, mas a duração de parede não).

## 4. Limitações a registrar (não são bugs do workflow)
- 10.000 quadros emulados ≈ 55–60% do DEMO3 completo (~18.000 estimados em 7,21 FPS): o perfil cobre o começo da demo, não a demo inteira. Registrar isso no `report.md`/PR; cobertura total exige autorização explícita do mantenedor (AGENTS.md §5) ou segunda captura com `--start-tic`.
- ROMs contêm dados do WAD shareware; artefatos ficam retidos 90 dias no repositório. Mesmo padrão dos workflows existentes; só confirmar que o repo é privado.
- R68 mede com `ring` fixo de 128 e HInt a cada 48 linhas; é instrumentação (BSS +4 B), **não** deve ser comparado em FPS contra R66 como resultado de desempenho.

## 5. Pronto para ativação?
**Ainda não.** Após A1–A3 (e B1/B2 de preferência) o Cláudio considera pronto para o mantenedor autorizar um único `workflow_dispatch`. Quem aplica as correções: o ChatGPT na branch dele, ou o Cláudio numa cópia na branch dele — a definir pelo mantenedor. Nada foi movido para `.github/workflows/`.

## 6. Dependências a verificar no runner `x360-linux` (antes de autorizar)
- C1 — `fish`, `python3` (≥3.8), `tar`, `git`, `cmp`, `sha256sum` no PATH do serviço do runner.
- C2 — `~/mars/m68k-elf/bin/m68k-elf-size` e `-nm` executáveis (mesmo usuário do runner).
- C3 — Artefato `doom-md-r66-cl-approx-colpair-perf-play` do run 40231459814 ainda não expirado (conferir na aba Actions) e `GITHUB_TOKEN` com `actions: read` permitido pela política do repositório/organização.
- C4 — `scripts/doom1.wad` ou um dos candidatos (`~/Projetos/doom-assets/doom1.wad|DOOM1.WAD`, `~/Downloads/doom1.wad`) com SHA-256 `1d7d43be…cac771`, 4.196.020 bytes. Sem rede, é a única fonte.
- C5 — NumPy (≥2.2) já instalado, ou aceitar o fallback pip.
- C6 — `blastem` executável sob `~/Projetos/**` com suporte a `-b` e `-D` (GDB RSP); sem display (SDL dummy é setado pelo script).
- C7 — Espaço livre (≥ ~100 MB para dist/r68: 2 ROMs de até 4 MiB + cópia do controle + capturas) e nenhum outro job pesado simultâneo no runner.
- C8 — Branch de dispatch = `exp-claudio-r68-profiling-20261025` (head 6a4b650 ou o aprovado) — conferir antes de autorizar.
