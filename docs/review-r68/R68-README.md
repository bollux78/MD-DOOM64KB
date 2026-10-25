# R68 — onde vai o tempo? (diagnóstico, só BlastEm)

Base: R66 (`exp-r66-claudio-colpair`, 7,21 FPS no DEMO3). Branch: `exp-claudio-r68-profiling-20261025`.
**Não é build de desempenho.** O ROM com a flag mede onde o tempo vai, nunca quão rápido o jogo é.

## Pergunta
Por que o FPS médio é 7,21 se o mínimo de 1 s é 2,9 e o máximo 13? Que carga explica os quadros lentos, e em quais funções o tempo é gasto nos lentos e nos rápidos? Sem isso, qualquer "qualidade adaptativa" é palpite.

## O que o ROM faz (`DOOM_R68_PROF=1`, só `-DDOOM_R68_PROF` difere do controle R66)
Um bloco de 324 B no heap do SGDK (mesmo padrão do R64D; só `r68_ptr`, 4 B, entra no BSS):
- **Registro por quadro de jogo** em `D_DoomLoop`: carimbos de VBlank no início, no fim da lógica (`TryRunTics`) e no fim de `D_Display`, tics do início e do fim, e contadores de carga: nós BSP, `R_CheckBBox`, `R_AddLine`, segmentos (`R_StoreWallRange`), colunas do laço de segmento, chamadas de parede (`R42_DrawPackedWall`), de flat (`R_DrawColumnFlat`), `R_PointToAngle16`, sprites projetados/desenhados, `P_CheckSight`.
- **Amostrador de PC por HInt** (`r68_prof_hint.s`, mesma validação de pilha do `R21_ProfHInt`): um sample a cada 48 linhas ativas, gravado como PC>>3 num anel de 128 entradas no mesmo bloco. Cobre quadros de até ~25 VBlanks; excesso é contado como perdido.
- `R68_FrameMark()` é o ponto de parada: o host lê o bloco por RSP a cada quadro e o ROM então zera anel e contadores.

## Como rodar
```
python3 scripts/lab/build_r68.py          # r66-perf (controle) + r68-prof-perf; BSS <= 57.920
python3 scripts/lab/r68_capture.py \
  --blastem ~/Projetos/blastem64-1.0.0/blastem \
  --rom dist/r68/doom-md-r60-r68-prof-perf.bin --elf dist/r68/doom-md-r60-r68-prof-perf.elf \
  --out dist/r68/capture --max-emulated-frames 10000
```
Com ~8 VBlanks por quadro de jogo, 10.000 quadros do emulador (limite do `AGENTS.md`) cobrem os primeiros ~1.000–1.200 quadros do DEMO3. Cobrir os 2.134 quadros exigiria ~18 mil quadros do emulador por invocação; isso passa do limite e **só deve ser feito com autorização explícita do mantenedor** (`--max-emulated-frames 25000`).

Saídas em `--out`: `frames.jsonl` (um registro por quadro), `rings.json` (amostras de PC por quadro), `summary.json` e **`report.md`**:
1. distribuição do custo por quadro e quanto do tempo vai para os 10/20/30/50% mais lentos;
2. divisão lógica (`TryRunTics`) contra render+vídeo (`D_Display`);
3. carga média por quadro e modelo de custo por mínimos quadrados (ciclos por unidade de carga, R²);
4. perfil de PC por função: todos os quadros, 20% mais lentos, 50% mais rápidos.

## Limitações conhecidas
- O HInt só dispara com a tela ativa: as linhas de VBlank (~14%) não são amostradas.
- Os contadores são correlacionados entre si (segmentos, colunas e paredes crescem juntos); os coeficientes do modelo são um guia, não custos exatos.
- A sobrecarga do amostrador (uma interrupção a cada ~3 mil ciclos) e dos contadores é de alguns por cento. Compare o FPS contra o controle R66 só para estimá-la.
- Código acima de 512 KiB satura o bucket (o leitor avisa se o ELF tiver símbolos de código ali).
- Se `MEM_alloc` falhar por falta de heap, o ROM para com `R68 heap unavailable`.

## Verificações já feitas (host, sem toolchain m68k)
- `check_r68_inert.py BASE .`: sem a flag, as 5 fontes alteradas são idênticas à R66.
- `test_r68.py`: layout C == leitor Python == offsets do assembly (com mutações detectadas), modelo de custo recupera coeficientes conhecidos (<2%), captura de ponta a ponta contra um BlastEm simulado em RSP.
- **Não verificado:** compilação m68k e execução no BlastEm (sem toolchain aqui). O assembly é uma variação curta do `R21_ProfHInt`, que já foi validado.

## O que devolver
`report.md` + `summary.json` (e `frames.jsonl` se for pequeno), BSS dos dois ROMs, e o FPS dos dois ROMs no mesmo prefixo para estimar a sobrecarga.
