# Handoff para o Werk — rodada de otimização C7 (CONTROL, AI6, AI6S)

Branch `exp-dread-c7-optimization-matrix-20261123`, commit `826d575` ou mais novo. Leia primeiro o `README.md` desta pasta (revisão, evidências e regras de decisão). Nada foi rodado em CI: os commits levam `[skip ci]` de propósito.

## O que mudou desde a última versão

- **Rodada com 3 ROMs:** CONTROL, AI6 (IA a 6 Hz, desacelera os monstros) e AI6S (IA a 6 Hz com passo alongado para manter a velocidade média; passo limitado a 16 unidades). GEO_SAFE, ALL, AI4, TEX2, TEX4 e GEO_STEPS saíram da rodada. Continuam suportadas em `variant.sh`.
- **Por que saíram:** no WAD do Doom 1 shareware (E1M1–E1M9, 2000 vistas por mapa, no host), GEO_SAFE remove 0 segs em 7 dos 9 mapas e ≤0,12% do trabalho de colunas nos outros; GEO_STEPS muda 5–14% das vistas em 8 mapas e a colisão; TEX não reduz os dados que os escalonadores leem.
- **Bugs corrigidos no GEO_SAFE** (PVS da geometria reduzida, folhas sem segs): `tools/conv.py`, `tools/map_reduce.py`, `tools/build_map.sh`. O CONTROL não muda (o `mapdata.c` tem o mesmo SHA-256).
- **Benchmark MAME:** agora registra histograma de VBlanks por quadro, `vblanks_per_frame_mean` e `visual_hash`.

## O que rodar

1. **Compilar e medir a matriz** (workflow `.github/workflows/dread-c7-optimization-matrix.yml`, `workflow_dispatch`). Só rode se o Cláudio ou o usuário pedirem; o push já não dispara. Compila no runner self-hosted, mede no MAME e monta `DREAD-C7-OTIMIZACOES.zip`.
2. **Mesma medição em outro emulador** (GPGX ou BlastEm) para o CONTROL e as duas de IA, com a mesma rota E1M1 de 312 quadros. MAME sozinho não basta.
3. **Repetir cada modo pelo menos duas vezes** para medir o ruído (o workflow roda uma vez por modo).

## Como ler o resultado (regras de decisão)

1. **A IA importa?** `render_fps / combat_fps − 1` no CONTROL. Se for menor que 5%, AI6 e AI6S não podem render mais que isso: o resultado é "descartar".
2. **Combate não é comparável entre variantes de IA** (os monstros agem diferente e a rota diverge). O CSV marca `combat_comparable = False`. Compare o render (modo 1) e olhe a IA separadamente.
3. **Não use só o FPS médio.** Entregue também `vblank_histogram` e `vblanks_per_frame_mean`: AI6 e AI6S podem trocar média por quadros longos.
4. **Classes de IA são trade-offs de jogo,** não otimização de graça. Só são promovidas por decisão do usuário, depois de jogar, em BlastEm e no console.

## O que o AI6S precisa de teste humano

Foi compilado no host só para sintaxe; ninguém jogou. Na prática, olhar se imp, baron e caco chegam na mesma velocidade do CONTROL e se o movimento em saltos incomoda. O demon fica um pouco mais lento (passo de 20 limitado a 16).

## Regras do projeto (não mudar)

- O jogo roda sem SRAM. Sem mapper ou SSF na versão principal.
- Não publicar WAD nem ELF. Entregar ROMs em zip em `/home/dan/Projetos/Personal/dread-md/`.
- Toda ROM de teste: nome no cabeçalho, tela preta com a fonte do SGDK mostrando o nome, o que testa e "aperte START ou aguarde 15 segundos", e jogável.

## O que devolver

- Run/artefato usado e commit.
- Tabela por variante e por modo: FPS, repetições, `vblanks_per_frame_mean`, histograma, SHA-256 da ROM.
- O valor de `render_fps / combat_fps − 1` do CONTROL (decide se a IA importa).
- Qualquer falha do MAME (Lua: `screen:width()`/`screen:pixel` e o hash visual ainda não foram executados em MAME).

## Fora desta rodada (próxima fase, no README, seção 5)

Segundo estágio do laço de colunas, menos nós e folhas visitados na BSP, ajuste da PVS e custo da IA. Exigem compilar e medir em ROM.
