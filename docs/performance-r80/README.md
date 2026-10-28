# R80 — projeto de desempenho, pronto para análise e implementação

**Comece por [PROJETO.md](PROJETO.md).** O pedido ao agente está em [PROMPT.md](PROMPT.md).

Este branch contém o repositório completo a partir da R79 aceita e os materiais de revisão. Pode implementar candidatos em um branch derivado. A R79 base permanece a referência; SH1/SH2 não entram no build R80.

## Início rápido

```sh
git clone --branch exp-chatgpt-r80-performance-20261027 https://github.com/bollux78/MD-DOOM64KB.git
cd MD-DOOM64KB
git switch -c exp-seuagente-r80-ofs
```

Leia o projeto e os flags antes de alterar código. O arquivo [`scripts/lab/apply_r80_performance.py`](../../scripts/lab/apply_r80_performance.py) é o ponto de implementação: ele roda **depois** dos patches R72…R79 numa cópia de build. O hook inicial é inerte, sem otimização ou ganho alegados. Faça uma transformação por experimento, com pré-condições e testes.

Mantenha os fontes originais e os patches R72…R79 intactos para que controle e candidato sejam comparáveis. Novos helpers podem ser acrescentados e ativados pelo hook R80. Arquivos gerados pelo build, como `r22_pixel4.h` e tabelas, podem ser recriados pelo fish: altere o gerador ou a etapa de injeção adequada, em vez de depender de uma edição temporária que será sobrescrita. Não edite `reference-prepared/`: é referência de leitura, não a entrada de compilação.

## Fontes, evidências e controles

- Os fontes originais completos estão na raiz do repositório. O código da referência foi fixado no commit `31807c0355298f35ec36ab0c42a847a2493d92e4`.
- [`reference-prepared/src/`](reference-prepared/src/) reúne os principais arquivos para leitura depois de aplicar a cadeia R79; o restante está em `src/`. Use os flags para selecionar os caminhos ativos de `#if`.
- [`control-build/`](control-build/) contém os manifests, flags, tamanhos e hashes dos controles R79. As ROMs e ELFs ficam no [artefato original do GitHub Actions](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40597005254/artifacts/12776668748), disponível enquanto a retenção do Actions permitir.
- Para obtê-los pelo terminal, com `gh` autenticado: `python3 docs/performance-r80/tools/fetch_control_build.py`. O helper confere SHA-256 das ROMs antes de copiar os controles. Um agente com conector GitHub também pode baixar o artefato pelo ID `12776668748`. GitHub Actions exige autenticação para baixar artefatos.
- [`evidence/`](evidence/) preserva resultados enviados pelo usuário, proveniência e a diferença de preparação dos fontes. Os históricos R70/R71 completos continuam em `docs/`.

## Preparar uma cópia local de build

Em checkout limpo e descartável, com as dependências do projeto disponíveis:

```sh
python3 scripts/lab/prepare_r80_performance.py --variant control
# ou: --variant candidate
python3 scripts/lab/build_r71a12mul_hud.py
```

A preparação deve rodar uma única vez. Ela aplica a cadeia R79, chama o hook somente no candidato e seleciona apenas dois builds sem shadow. O controle mantém `r79-base-pf/pl`; o candidato usa `r80-perf-pf/pl`. O builder R79 sem esta preparação geraria seis ROMs: não usá-lo diretamente para esta revisão.

A compilação requer MarsDev/SGDK, fish, os geradores Python e os assets de entrada previstos no projeto. O workflow abaixo utiliza o runner existente e restaura o WAD local já fixado por SHA-256. Não há SDK nem WAD de entrada incluídos nesta pasta.

## Rodar no runner existente, quando o experimento estiver pronto

O [workflow R80](../../.github/workflows/r80-performance.yml) aceita `control` ou `candidate`. Gera PERF/PLAY, confere ROM ≤4 MiB, BSS ≤57.920, ausência da flag de shadow e faz smoke de 800 frames em cada ROM. Isso não é benchmark completo nem prova equivalência do mundo renderizado.

Pode ser despachado manualmente quando o GitHub listar esse workflow. Para iniciar a partir de um branch experimental mesmo que o workflow ainda não apareça na interface, crie ou altere `.github/triggers/r80-performance.trigger` com apenas uma linha:

```text
candidate
```

Use `control` para o controle. Faça commit e push no branch `exp-...-r80-...`. Somente essa alteração explícita do trigger inicia o evento de push do workflow novo; publicar código ou documentação comuns não o inicia. Para repetir a mesma variante, mantenha a primeira linha e altere uma segunda linha de comentário, por exemplo `# rodada 2`. Também pode usar dispatch quando disponível. Não lance builds duplicados sem necessidade.

Não criar esse arquivo antes de concluir o experimento e seus testes. Nenhum novo build R80 foi disparado durante a publicação inicial deste projeto.

## Aceitação e retorno

Mesmos samples, lógica, áudio, viewport e clock. Sem regressões de menus, HUD, H32/H40, tintas e telas nativas. Perfil parcial até 10.000 frames automatizados; o helper [run_bounded_diagnostic.py](tools/run_bounded_diagnostic.py) usa 8.000 por padrão. Scripts históricos têm defaults maiores: usar o wrapper.

A promoção exige evidência de ganho no DEMO3 completo, no mesmo ambiente. Devolva análise, patch/commit, testes realizados, BSS/ROM e medições com suas limitações. Os percentuais históricos R71 são pistas, não perfil atual da R79.
