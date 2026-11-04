# R129 — Preservação do DOOM-MD: desenvolvimento público + binários privados

**Preparado pelo Werk (04/11/2026), para o Cláudio.** Branch de trabalho: `exp-claudio-r121-e1m7-20261103`.
**Decisão expressa do usuário:** quase tudo deve ficar no GitHub; somente ROMs, WADs, ELFs com recursos incorporados e demais dados proprietários devem ficar privados. As demos utilizadas são públicas e podem ser compartilhadas **somente depois de verificar a licença/condições de redistribuição e atribuição**.

## 0. Estado real
- Este documento e o preparador local `scripts/lab/r129_archive_private.py` ficam no GitHub **público**.
- O repositório público `bollux78/MD-DOOM64KB` não muda de visibilidade.
- **`bollux78/MD-DOOM-PRIVATE` foi criado pelo usuário e verificado como PRIVATE pelo Werk em 04/11/2026.** O README privado está inicializado; o upload de ROMs ainda NÃO foi configurado.
- Nenhum upload de ROM/WAD/ELF ao GitHub privado foi realizado ainda. Até implementar e validar a sincronização, o runner local é a única cópia dessas builds.
- Não fazer merge na `main` nem alterar as políticas de upload público sem aprovação do usuário.

## 1. Matriz de visibilidade
| Público (MD-DOOM64KB) | Privado (MD-DOOM-PRIVATE) |
|---|---|
| fontes C/ASM, conversores, scripts e workflows | ROMs `.bin`, ELF de builds com dados incorporados, arquivos WAD |
| handoffs, decisões, commits, documentação | dumps/reproduções privados que possam incorporar assets proprietários |
| métricas, logs sanitizados, hashes SHA-256, parâmetros e manifestos SEM caminhos confidenciais nem credenciais | arquivos de entrada privados necessários para recompilar |
| demos públicas apenas após verificar permissões/atribuição | demos que não possam ser redistribuídas |
| receitas de build reproduzíveis | credenciais NUNCA no repositório (nem privado) |

O código do jogo pode ser público; **não** colocar WAD, ROM ou ELF no histórico público nem em artefatos/logs públicos. Repositório privado não equivale a autorização de redistribuição; garantir acesso restrito.

## 2. Esquema de arquivo privado sugerido
```
MD-DOOM-PRIVATE/
  README.md
  builds/
    r126b/run-41882892479-1/
      c-early/*.bin
      c-early/*.elf
      c-control/*.bin
      c-control/*.elf
      MANIFEST-PRIVATE.json
    r128/run-<runid>-<attempt>/
      c-control/{*.bin,*.elf}
      c-stairs/{*.bin,*.elf}
      c-corpses/{*.bin,*.elf}
      c-sight/{*.bin,*.elf}
      c-far/{*.bin,*.elf}
      c-all/{*.bin,*.elf}
      MANIFEST-PRIVATE.json
  input-assets/
    doom1.wad
    ...outros necessários (se legalmente cabíveis)...
```
O arquivo de manifesto deve indicar `source_repo`, `source_commit`, `workflow`, `run_id`, `attempt`, `variant`, `sha256`, `size`, `status` e ferramentas/versões. Usar nomes de caminho relativos, **não** nomes de diretórios da home, tokens ou informações privadas em relatórios públicos. Os hashes e commits podem ser publicados.

## 3. Integração no runner (implementação do Cláudio)
1. **CONCLUÍDO:** usuário criou `bollux78/MD-DOOM-PRIVATE` com visibilidade PRIVATE; Werk verificou `visibility=private` e permissão de escrita em 04/11/2026.
2. Configurar credencial **de escopo mínimo** no runner para escrever exclusivamente nesse repositório privado: preferir chave SSH deploy key com escrita, guardada fora do checkout público, permissões 0600. Nunca imprimir chave/token ou copiá-los para `dist/`; não reutilizar `GITHUB_TOKEN` do repositório público (por padrão não acessa outro repo).
3. Validar a visibilidade privada via API/UI antes de qualquer push; se não for privada, **falhar fechado e não fazer upload**.
4. Fluxo de backup seguro: após build e gates de ROM/BSS/Z80, copiar binários para `/home/dan/Projetos/Personal/.../` e executar `r129_archive_private.py` para um staging local **fora de `GITHUB_WORKSPACE` e fora do checkout público**; comparar SHA-256; só então sincronizar com o repositório privado. Para WADs, arquivar separadamente com checksum, nunca via artifact público.
5. **Não usar `actions/upload-artifact` para ROM/WAD/ELF** no workflow público. Subir apenas relatórios e manifestos sanitizados, como já acontece.
6. Upload privado idealmente acionado somente em workflows de branches experimentais autorizadas, sem `pull_request` de forks e sem segredos acessíveis a código não confiável. Runner self-hosted executa código: revisar proteções de branches e quem pode disparar.
7. Para volume/histórico grande, avaliar Git LFS no repo privado, custos/limites e retenção. Guardar pelo menos todas as versões aprovadas e cada candidata de benchmark decisivo; não depender apenas dos 90 dias do GitHub Actions.
8. Fail-safe: se o backup privado falhar, **não apagar** originais locais. Mostrar `::warning` claro e um status de arquivo; não declarar versão arquivada sem checar `git ls-remote` e conteúdo/hash remoto.
9. Adicionar um manifesto público de **catálogo** (sem bytes privados) indicando versão, commit público, run, hashes, resultados, backup privado verificado ou ainda pendente.
10. Separar retrobackup: inventariar `/home/dan/Projetos/Personal/r*/run-*/` sem excluir nem renomear, priorizar R122 Layout, R126b run 41882892479-1, R128 e versões aceitas anteriores. Verificar os hashes antes/depois.

## 4. Helper já preparado
`scripts/lab/r129_archive_private.py` prepara cópias locais de `.bin`/`.elf` e um `MANIFEST-PRIVATE.json` em um diretório que precisa ficar FORA do repositório público. Não faz push nem manipula credenciais. Uso ilustrativo:

```fish
python3 scripts/lab/r129_archive_private.py \
  --run-dir /home/dan/Projetos/Personal/r128-claudio-simplify/run-<runid>-1 \
  --stage-dir /home/dan/Projetos/Personal/md-doom-private-stage/builds/r128/run-<runid>-1 \
  --source-commit (git rev-parse HEAD) \
  --workflow r128-claudio-simplify.yml \
  --run-id <runid> --attempt 1
```
A saída **não** significa backup remoto completo; precisa confirmar push/recuperação privados separadamente.

## 5. Gates de aceitação do R129
- O repo novo está PRIVATE (UI/API) e acessível somente ao usuário/colaboradores autorizados.
- As ROMs/ELFs dos dois primeiros runs amostrados foram recuperadas da cópia privada e os SHA-256 batem.
- A página pública do Actions continua contendo somente relatórios, sem ROM/WAD/ELF.
- Existe um teste de recuperação local do código (SHA do commit + inputs privados + ferramentas).
- O backup não altera renderer, lógica, áudio Z80 (< 2 MiB), `.data`, `.bss` nem desempenho dos jogos.
- Antes de declarar "protegido contra perda de SSD", manter também uma segunda cópia independente (outro armazenamento físico/nuvem). Um repositório GitHub privado sozinho não substitui backup completo.

## 6. Implementação do Cláudio (04/11/2026)
- **`scripts/lab/r129_push_private.py`:** envia um stage do `r129_archive_private.py` para `bollux78/MD-DOOM-PRIVATE` e confere o resultado.
  - **Falha fechado:**
    - se a API anônima do GitHub enxergar o repositório (HTTP 200 = público), aborta sem enviar nada;
    - aborta se a deploy key não existir (`$R129_KEY`, padrão `~/.ssh/md_doom_private_deploy`) ou não estiver com permissão 0600;
    - nunca sobrescreve um arquivo já arquivado com conteúdo diferente.
  - **Verificação:** depois do push, faz um fetch novo e compara o blob id remoto de cada arquivo com o local. Só então grava `remote_backup_verified: true` no `MANIFEST-PRIVATE.json`.
  - Opcionalmente gera um catálogo público com hashes e ids, sem caminhos e sem binários.
  - Não apaga os originais nem o stage.
- **`.github/workflows/r129-claudio-backfill.yml`:** arquiva R119 both, R122 layout e R126b early, usando as pastas privadas do runner:

  | Item | Caminho |
  |---|---|
  | stage | `$P/md-doom-private-stage/builds/<nome>/run-…` |
  | clone do repositório privado | `$P/md-doom-private-repo` |
  | `$P` | `/home/dan/Projetos/Personal` |

  O commit de origem vem da API do run. No repositório público sobe só o artefato `r129-private-catalog`.
- **Passo único do usuário, na máquina do runner:**
  ```fish
  ssh-keygen -t ed25519 -N "" -C md-doom-runner -f ~/.ssh/md_doom_private_deploy
  chmod 600 ~/.ssh/md_doom_private_deploy
  cat ~/.ssh/md_doom_private_deploy.pub
  ```
  No GitHub: **MD-DOOM-PRIVATE → Settings → Deploy keys → Add deploy key**. Colar o `.pub`, marcar **Allow write access** e salvar. A chave só vale para esse repositório.
- **Como disparar** (Werk): `date -u > .github/triggers/r129-claudio-backfill.trigger`, depois commit e push.
- **Volume:** cada run arquiva `.bin` e `.elf` de todas as variantes, cerca de 8 MB por variante (pl + pf). Arquivar só runs aprovados ou decisivos. O Git LFS fica para quando o repositório passar de ~1 GB.
- **Segunda cópia:** continua necessária. O GitHub privado sozinho não substitui um backup físico.
