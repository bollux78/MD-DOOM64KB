# HANDOFF — DREAD MD / otimização Ferret A1 (22/11/2026)

## Missão e restrições

Continuar otimizando o renderer da **DREAD D01 completa** no repositório `bollux78/MD-DOOM64KB`, aproveitando o estudo da ROM Ferret Alpha 2. Prioridade: **FPS no spawn da E1M1 com a câmera parada**, não rotas/giro como benchmark principal. Preservar aparência, paletas, texturas com origem vertical exata 16.16, HUD, arma, música, E1M1–E1M9, portas, atores, tiro, menus e **START durante jogo**. Nunca declarar uma variante melhor sem medir FPS e conferir pixels. Não alterar `main`, versões estáveis ou a branch de Cláudio; experimentos em branches isoladas.

O usuário considera a aparência e a jogabilidade da nossa ROM superiores à Ferret, mas a Ferret mais fluida na mesma área. Não substituir o jogo por reconstrução independente Ferret, que roda a ~2,07 FPS e é incompleta.

## Referências fundamentais

- Handoff da investigação Ferret: https://github.com/bollux78/MD-DOOM64KB/blob/6b9d2566e727a3f5535745234010c45ac93aa853/research/ferret-alpha2/HANDOFF-OTIMIZAR-D01.md
- Pesquisa Ferret: `research/ferret-alpha2/README.md`, `PHASE2.md`, `PHASE3-NAVEGAVEL.md` no commit `56813b088369cee0ccc23257abd04e704c0a277f`.
- D01 com textura exata e input no VBlank, controle historicamente medido: `exp-werk-dread-exato-input-vblank` / `42f17f26b1e3187ad7995799891cb50bd090e66c`; handoff `experiments/DREAD_MD/d01/HANDOFF-CLAUDIO-EXATO-VBLANK.md`.
- D01 histórico inicial, resolução fixa 128x112, benchmark BlastEm funcional: run `44760580581` / commit `d160a2000e1914aeb17d4c4ae61342f2789b4d29`; 4,34 FPS **em rota**, não spawn.
- Branch anterior com cinco variantes compiladas (`CONTROL/PATH/RAW/ALL/LEGACYSEG`): `exp-werk-dread-precalc-20261121` / `a06104e4aa54af0e0d27c6853c8c16a51d5d761f`, run de sucesso `44963655469`.
- Runner GitHub hospedado usa `ubuntu-24.04`; NÃO precisa ligar computador do usuário. WAD shareware via pacote Ubuntu `doom-wad-shareware`, em `/usr/share/games/doom/doom1.wad`. Marsdev/SGDK é compilado pelo script `scripts/lab/bootstrap_marsdev.sh`; lembrar que a versão atual do Marsdev exige inicializar Git submodules. Cache do Actions é por branch/escopo, pode falhar e recompilar todo Marsdev; o primeiro bootstrap é demorado.

## Trabalho em andamento: A1

**Branch dedicada:** `exp-werk-ferret-a1-20261121` (criada de `a06104e4`).
**HEAD no início desta nota:** `7c9b70335cf86e580d94e09755c6d9f0a35ef872`.
**Workflow:** `.github/workflows/dread-ferret-a1-20261121.yml`.
**Run atual:** https://github.com/bollux78/MD-DOOM64KB/actions/runs/44974318604, job `137060682593`.
**Estado na última consulta:** `in_progress`, preparando Marsdev em cache miss. **Não há ROM ou FPS publicados ainda.** Consulte estado/logs e artefatos antes de qualquer conclusão.

Commits:
- `fa9dd899`: `src/colasm.s`, flag `DREAD_OPT_COLPTR_INCREMENTAL`. Na passagem entre colunas consecutivas de `seg_columns`, reutiliza `a2`: no modo row-doubled `r_colb==1`, `addq.l #1,a2` se ainda na mesma coluna de tile; `adda.w #285,a2` no limite de 4 bytes, porque a altura lógica é 72 linhas e o stride é 288 bytes. Em salto de coluna, mantém lookup `r_colofs`. **É apenas uma hipótese; ganhos e correção visual NÃO verificados**. Primeiro verificar montagem e stepping de `a2`; incremento só válido para row-doubled com altura 72. Todos os modos do controle devem permanecer funcionais.
- `fdb65e35`: `src/main.c`, flag `DREAD_SPAWN_PROFILE`: define `spawn_published_frames` e incrementa no VBlank quando há flip completo; desativa limitador com `fcap=0`, apenas nas ROMs experimentais.
- `7c9b7033`: novo workflow hospedado para construir `DREAD-FERRET-CONTROL.bin` e `DREAD-FERRET-A1.bin`. Ambos usam `-DDREAD_VALIDATION_TEST -DDREAD_JOY_VBLANK -DDREAD_SPAWN_PROFILE`; A1 acrescenta `-DDREAD_OPT_COLPTR_INCREMENTAL`. Prepara todos os nove mapas uma só vez e distribui arquivos .bin via `DREAD-FERRET-A1-SPAWN` no GitHub Actions. Inclui teste MAME experimental via Lua `-autoboot_script`.

**Importante: instrumentação ainda não validada.** O MAME precisa conseguir ler o símbolo `spawn_published_frames` no endereço correto de memória 68000. Verifique endianness de `read_u32`, mapeamento dos endereços RAM (`0xFFxxxx`) e suporte a `-autoboot_script` / `-plugins 0` antes de confiar em medições. Após ~15 s de tela inicial, mede publicações entre frames de vídeo 1800 e 3000 (1200 quadros NTSC; usa 59,922743 Hz); a IA continua ativa, então faça repetição e registre as condições. **A execução MAME sem janela com código de saída 0 não constitui benchmark FPS por si só**. Se Lua falhar, usar Genesis Plus GX instrumentado da pesquisa, ou depurador MAME que permita leitura de memória, com método verificável.

**Possível problema a conferir no A1:** o label `.Lcol_ptrready` pula o cálculo de ponteiro em `.Lcol` para colunas adjacentes. `a2` é usado por `tex_fast`, mas esta rotina faz push/pop antes de retorná-lo. Conferir que ele também é preservado nos scalers e em todos os caminhos, e que o update `+285` cruza o limite de tile corretamente. A comparação deve exigir igualdade do framebuffer ou pelo menos mesmas cores em pixels na cena fixa e em ângulos extremos. Se compilação falhar, não anunciar ganho.

## Resultados prévios e limites de comparação

- Ferret Alpha2 original em spawn, Genesis Plus GX NTSC, 300 VBlanks, atores ativos: **5,9107 FPS sem SRAM**, **8,2554 FPS com SRAM16**. SRAM16 é opcional; não assumir presença no Everdrive nem transformar em dependência. Ferret usa buffer de 11.520 B, linhas duplicadas fisicamente para 23.040 B, com/sem SRAM duas formas diferentes de apresentação.
- Perfil Ferret sem SRAM: lista/candidatos **7,706 ms**, paredes **64,281 ms**, sprites **3,413 ms**, cena 3D **75,423 ms** (inclui etapas anteriores), conversão/escrita CPU→VDP **59,748 ms**. Valores inclusivos de interrupções/stalls, não somar indiscriminadamente. Com SRAM16: conversão→SRAM **20,604 ms** e paredes **71,906 ms**.
- D01 corrigido histórico, mesmo benchmark de percurso fixo de 312 imagens: ~**3,57–3,62 FPS**; comparação com Ferret em spawn **não é válida** por condições diferentes. Giro D01 5,98 FPS tem movimento dependente de cadência, não usar como controle parado.
- Usuário enviou capturas reais do spawn D01 com **3,4 FPS / 32 segmentos** e **3,9 FPS / 31 segmentos** (duas variantes com apresentação distinta), não confundir com captura anterior de corredor com 9,5 FPS / 4 segmentos. A referência é spawn.
- ROM Ferret reconstruída v03 por agente anterior: ~2,069 FPS, incompleta; não usar como arquitetura executável superior.

## O que a análise Ferret realmente prova

A Ferret usa listas de visibilidade por célula (BSP localiza posição, stream com tokens 16-bit produz paredes/setores/atores em ordem), registros sequenciais de coluna de 8 bytes, incremento de bordas via ADD/ADDX, escaladores desenrolados com entrada ajustada e A7 como ponteiro de pixels (incremento de 2 em acessos byte a SP), dois kernels de textura linear/perspectiva escolhidos por erro, e dois pipelines de apresentação dependendo de SRAM16. Na Ferret a geometria não é livre de MUL/DIV; há trabalho de divisão no setup. O D01 já possui **ColRec sequencial de 12 bytes, scalers desenrolados, segasm.s para linhas/âncoras e 16.16 vertical exato**; não chamar a introdução do que já existe de novidade.

Análise do D01:
- `src/colasm.s` em `seg_columns`: lookup `r_colofs`, recorte céu/chão/portais, `tex_fast` origem e teste exato de limite; otimizações podem mexer em ponteiros, setup, registro sequencial. Preservar caminho original `DREAD_EXACT_SPAN_REFERENCE` para comparar.
- `src/render.c`: `render_node` já possui PVS + BSP e colunas fechadas; `draw_seg_body` constrói ColRec e usa `seg_rows2`/`seg_rows1` e `seg_anchors`. Comparar custo **setup vs pixel loop**, não supor que o BSP é maior gargalo.
- A variante `LEGACYSEG` anterior apenas muda despacho de segs; **não é A1**, não valida textura/colunas.
- `RAW` / `PATH` anteriores também precisam FPS antes de afirmar benefícios.

## Próximos passos operacionais, na ordem

1. **Checar run 44974318604**: status, logs de compiler, artefato `DREAD-FERRET-A1-SPAWN`, confirmação de ROMs controle/A1. Se o build falhar, corrigir no branch A1 e disparar novo workflow. Manter publicação dos binários mesmo se o emulador falhar.
2. Validar MAME: procurar linhas `SPAWN_BEGIN` e `SPAWN_RESULT` no log por variante. Se nenhuma, NÃO atribuir FPS. Corrigir interface/endereçamento; considerar Genesis Plus GX da pesquisa, para medição da publicação real no VDP. Não confundir FPS de renderização, FPS da tela e velocidade do emulador.
3. Comparar hashes/pixels de CONTROL e A1 em spawn e ângulos fechados, e menus START e os quatro modos gráficos. Qualquer diferença visual não autorizada invalida A1 até explicar. FPS apenas com mesma ROM baseline/flags/ambiente, runs repetidos.
4. Se A1 trouxer ganho comprovado, seguir para **A2: otimizar setup exato dos escaladores/texturas**, especialmente `tex_fast` e `draw_seg_body`, mantendo arredondamento e origem fracionária 16.16. O antigo patch `6c8c512` degradou a exatidão visual e foi corrigido na branch exata, não reintroduzir.
5. Depois considerar **B: stream por célula**. Não reutilizar índices Ferret; adaptar conversor de cada mapa, preservar fronteiras, portas e snapshots de oclusão de sprites; fallback BSP obrigatório quando não houver garantia de ordem.
6. **C: apresentação sem H-int** é posterior e arriscada (duplica 11.520→23.040 bytes, potencial custo CPU/DMA, problemas de budget e SRAM); não misturar com A1/A2.
7. Combinar somente variantes corretas e medidas. Nunca publicar `ALL` de mudanças não aprovadas. Produzir ZIPs de ROMs jogáveis, hashes, benchmark detalhado e evidência visual. Nunca distribuir WAD/ELF/Ferret original.

## Ferramentas GitHub (via conector)

O assistente pode acessar GitHub por `functions.exec` e `tools.mcp__GitHub__*`. Exemplos:

```js
const repo="bollux78/MD-DOOM64KB",id=44974318604;
const [run,jobs,arts]=await Promise.all([
  tools.mcp__GitHub__fetch({url:`https://api.github.com/repos/${repo}/actions/runs/${id}`}),
  tools.mcp__GitHub__fetch_workflow_run_jobs({repo_full_name:repo,run_id:id}),
  tools.mcp__GitHub__fetch_workflow_run_artifacts({repo_full_name:repo,run_id:id})
]);
text({run:JSON.parse(run.result.content).status,steps:jobs.result.jobs,artifacts:arts.result.artifacts});
```

Logs: `tools.mcp__GitHub__fetch_workflow_job_logs({repo_full_name:"bollux78/MD-DOOM64KB",job_id:137060682593})`. Código: `fetch_file`, `update_file`, `create_file`, `create_branch`.

## Estado objetivo da entrega

Um teste do spawn da E1M1 **CONTROL × A1** com FPS medidos de publicações reais, captura/framebuffer equivalente, versão e flags documentadas, e download funcional no GitHub Actions. Se A1 perder, registrar e descartar: nenhum resultado é ruim se medimos corretamente. O trabalho é recuperar a eficiência da Ferret **sem sacrificar a aparência e o jogo do D01**.
