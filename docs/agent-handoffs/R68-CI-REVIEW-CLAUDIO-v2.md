# R68 CI — revisão estática final (v2) do Cláudio

Alvo: `docs/agent-handoffs/proposals/r68-prof-build.reviewed-by-chatgpt.yml`
(branch `exp-chatgpt-r68-ci-review-20261025` @ eb8ce1b). YAML válido (parse ok).
Nada executado/ativado; branch do ChatGPT intocada. R68 é diagnóstico; R66 (7,21 FPS) segue baseline.

## Veredito
**Quase pronto, com 1 bloqueio (D1) e 2 ajustes pequenos (D2, D3).** Resolvidos os itens A1–A3 da v1.

## Itens da v1 — conferidos
- A1 OK: passo 1 exige `GITHUB_REF == refs/heads/exp-claudio-r68-profiling-20261025`, `merge-base --is-ancestor f5a9daa… HEAD` (com `fetch-depth: 0`), grava ENV.txt (branch, SHA, uname, uptime, nproc).
- A2 OK: `timeout-minutes: 45` no passo de captura; `--timeout 120` aceito (`type=float`). Nota: em `RSP.recv` o timeout é **por resposta**, não total — não limita a captura inteira; o limite total são os 45 min + `-b 10000`.
- A3 OK: `cmp` duro entre R66 reconstruída e controle original; SHA-256 das duas ROMs em `ROM-SHA256.txt`.
- Sem download de WAD, sem pip: OK. B1 OK (bloco morto removido).
- `if: always()` no upload: OK; `original-control/` também sobe (≈4 MiB, aceitável).

## Pontos pedidos
- **WAD**: caminho absoluto `/home/dan/Projetos/doom-md/assets/wads/doom1.wad`, tamanho 4.196.020 e SHA-256 `1d7d43be…cac771` validados e copiados para `scripts/doom1.wad` (gitignored). Correto, e acontece **antes** de gen_r22/gen_r49/build (único passo anterior que poderia lê-lo seria os oráculos r47/r48, que não usam WAD). Obs.: o build usa `scripts/doom64.wad` gerado por `wad_from_header.py`; `doom1.wad` só é exigido por `gen_sfx.py` (modo SFX). Manter o passo é inofensivo e conforme a decisão.
- **CachyOS**: `fish -n`, `python3`, `tar`, `git archive`, `find -executable -print -quit` (GNU), `sha256sum`, `cmp` — tudo compatível. NumPy 2.5.4 está acima do mínimo do código (≥2.2); o passo agora só verifica.
- **R66/R68**: build via `build_r68.py` (variantes `r66-perf` e `r68-prof-perf`, flags idênticas exceto `-DDOOM_R68_PROF`); nomes de ROM/ELF/MANIFEST batem com o que o workflow lê; BSS ≤57.920 e ≤ controle+8.
- **Controle**: artefato `doom-md-r66-cl-approx-colpair-perf-play` do run 40231459814 **existe e não expirou** (expira 2027-01-23, 16,5 MB; consultado por leitura via API). `actions: read` presente.
- **10.000 quadros**: 1 único BlastEm (`-b 10000`), flag explícita. Cobre ≈55–60% do DEMO3; registrar.
- **Publicação em falha**: `always()` + `if-no-files-found: warn`. OK.
- **Sintaxe/argumentos**: argumentos de `r68_capture.py` conferem (`--blastem --rom --elf --out --max-emulated-frames --timeout`).

## Correções restantes
- **D1 (bloqueio) — `workflow_dispatch` sozinho provavelmente não dispara.** GitHub só registra/permite despachar workflows cujo arquivo existe na branch padrão (`fullscreen`). Verificação (leitura): `r64a`/`r66` não existem em `fullscreen` e a API de workflows não lista nenhum deles; por isso os workflows existentes usam `on: push` com `branches` + `paths` restritos ao próprio arquivo (ex.: `r66-colpair-build.yml`). Opções: (a) seguir a convenção: `on: push: branches: [exp-claudio-r68-profiling-20261025]; paths: ['.github/workflows/r68-prof-build.yml']` **mantendo** `workflow_dispatch`; o disparo ocorre quando o arquivo é commitado na branch R68 — logo esse commit/push é o ato que precisa de autorização explícita sua; (b) colocar o arquivo na `fullscreen` (merge — fora do protocolo). Recomendo (a). O passo 1 continua válido (`GITHUB_REF` num push é `refs/heads/<branch>`). Caveat: comportamento do GitHub conferido por inferência e pela API, não por execução.
- **D2 — Fixar o BlastEm.** `command -v blastem || find ~/Projetos …` pode escolher outra versão se houver várias. Usar `exe=/home/dan/Projetos/blastem64-1.0.0/blastem; test -x "$exe"` (sem fallback), e `"$exe" -h 2>&1 | head -n1 >> dist/r68/ENV.txt` se imprimir versão.
- **D3 — `concurrency` com push:** manter `cancel-in-progress: false` (já está); o grupo próprio evita cancelar outros.

## Pronto para ativação?
Após **D1(a) e D2** sim: ficaria pronto para você autorizar **um** push do arquivo na branch R68 (que dispara um único run). Até lá, não. Independente disso, para o profiling cobrir o DEMO3 todo seria preciso outra autorização (§5 do AGENTS.md).

## Checklist do runner (já confirmado por você)
fish/python3/git/tar/cmp/sha256sum, NumPy 2.5.4, MarsDev, BlastEm 1.0.0, WAD local, ~2,8 GB livres (suficiente: dist/r68 ≈ 30 MB; `/tmp` do build usa algumas centenas de MB).
