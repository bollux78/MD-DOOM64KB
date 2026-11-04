# HANDOFF PARA CLÁUDIO — R121: FPS mínimo / E1M7 (03/11/2026)

## Pedido do usuário

Investigar **redução de travamentos / aumento do FPS mínimo real** no DOOM-MD (Mega Drive). O FPS médio melhorou consistentemente R117→R119, mas ainda há gargalo em E1M7. O usuário deseja manter a **imagem, a lógica e o gameplay idênticos**; não reabrir paleta, Shadow, menu, crops, IA low, qualidade de imagem, mapper ou áudio.

**Base candidata:** R119 `both` (que **já inclui** R118 `mulvc`). **NÃO** consolidar R120 nem fazer merge em main sem autorização. Trabalhar em branch experimental isolada, com variantes A/B revertíveis.

## Dados medidos no BlastEm (PLAY, Benchmark > Run All Demos in Sequence)

Condições: NTSC 60 Hz, 7,67 MHz original, H40, crop padrão, IA Normal, Shadow OFF, dez demos, 45.706 quadros em todos os casos.

| ROM | FPS médio | Mínimo de gameplay / E1M7 | Tempo total (s) | Observação |
| --- | ---: | ---: | ---: | --- |
| R117 MEAS | 4,96 | 1,4, mas pior janela em E1M3 tic306 | 9.220,62 | Controle antigo |
| R118 MUL | 5,14 | 1,0 E1M7 tic296 | 8.888,62 | Mul nativa |
| R118 VC | 5,02 | 1,0 E1M7 tic296 | 9.101,85 | validcount SRAM |
| R118 MULVC | 5,21 | 1,0 E1M7 tic296 | 8.768,10 | R118 acumulada |
| R119 SECNODES | 5,27 | 1,5 E1M7 tic425 | 8.679,18 | R118 MULVC + fusão SRAM |
| R119 COLLISION | 5,21 | 1,0 E1M7 tic296 | 8.766,73 | R118 MULVC + índice blockmap |
| **R119 BOTH** | **5,27** | **1,5 E1M7 tic425** | **8.668,97** | **Base recomendada** |
| R120 BOTH | 5,27 | 1,5 E1M7 tic425 | 8.680,95 | 0,14% pior que R119 BOTH |

Valores lidos das capturas de tela do usuário; FPS arredondado pelo próprio jogo. Não interpretar isoladamente o salto de mínimo 1,0→1,5 como garantia de ganho de 50% em TODAS as janelas: o *tic* crítico mudou. FPS médio R119 BOTH versus R117 ≈+6,25%. R119 BOTH `10/10` demos, 832 bytes livres mínimos na zone, maior bloco 448 bytes.

A R119 `both` no BlastEm passou validação de fingerprints 10 demos, pixels Shadow OFF/ON e tamanho de RAM. Validação no Mega Drive real ainda deve ser confirmada pelo usuário.

## Resultado R120 — NÃO PROMOVER

Branch: `exp-chatgpt-r120-sight-collision-20261103`.
- `control`: R119 `both` intocada.
- `sight`: em `P_CrossSubsector`, substituição da bbox fixed-point por limites inteiros equivalentes floor/ceil; busca do ponteiro de mapline após validcount.
- `collision`: em `PIT_CheckLine`, substituição da bbox fixed-point por limites inteiros floor/ceil equivalentes.
- `both`: soma de sight+collision.
- Script `scripts/lab/apply_r120.py`, workflow `.github/workflows/r120-sight-collision.yml`.
- Run inicial `41722538929` FAIL **de instrumentação**: `BlastEm RSP EOF` com **zero checkpoints** na demo3 incluindo o **controle**. O workflow foi alterado para retentar apenas esse EOF transitório, sem mascarar divergências reais.
- Run concluído **SUCCESS** `41726158554`: ROMs compiladas, `.data/.bss` invariáveis, 10 demos com checkpoints idênticos, pixels Shadow OFF e Shadow ON idênticos, PLAY smoke aprovado.
- **Não houve aceleração útil**: benchmark completo R120 BOTH, feito pelo usuário, 5,27 FPS; 8.680,95 s versus R119 BOTH 8.668,97 s (**11,98 s mais lento**).

**Anomalia grave no ensaio automático rendered-heavy A/B R120:** `scripts/lab/r118_ab.py` imprimiu +167,07% sight; +166,96% collision; +167,26% both (VBlanks adicionais, pior); demos 3/7/9 quase +600% cada, demo10 ~0%; porém o benchmark completo no jogo ficou praticamente igual. Isso **não se reproduziu** e NÃO pode servir como base para aprovar/rejeitar uma otimização. INVESTIGAR antes de reutilizar o ensaio:
- `.github/workflows/r120-sight-collision.yml`, etapa `Rendered timing on the heavy demos`: executa `r117_profile.py --demo {3,7,9,10} --skip 150 --norender 0`, capture de `frames.tsv`. Atenção a `--skip 150` que inicializa com render desabilitado e muda a variável em runtime.
- `scripts/lab/r118_ab.py`: lê mapas tic→vblank de `frames.tsv`, escolhe janela comum, subtrai contadores cumulativos de VBlank; checar **pontos exatos de captura, carregamento, limite e mudança de modo**.
- A etapa usa `|| echo ::warning` para erros do profile, então pode seguir e produzir comparação com saídas parciais; **corrigir para rejeitar explicitamente** profiles incompletos, status incompatível, ranges de tics não equivalentes, off-by-one, gaps/loads, offsets, VBlanks anômalos, checkpoints ausentes e mismatch de `leveltime`.
- Inspecionar `PROFILE.json` de **cada demo/candidato/controle**, `frames.tsv` nos artifacts da run; comparar deltas por frame, `gametic`, `leveltime`, final status, contagem de quadros e ranges. Não declarar causa sem comprová-la.
- Diferenciar perf profile via `pf` emulador/breakpoints do benchmark PLAY `pl` real, com mesmas opções.
- Testar microbenchmark control vs control (repetições) antes de aceitar percentuais; uma regressão verdadeira de ~167% deveria aparecer facilmente no Benchmark PLAY.
- Se possível gerar comparação focada **E1M7 em torno dos tics 296 e 425**, com profiler consistente sem render desligado durante o trecho ou com verificação de equivalência.

## Perfil de gargalos previamente levantado (R117)

Amostragem de lógica, estimativas percentuais: `P_CheckSight` 18,5%, `P_MobjThinker` 12%, `P_CheckPosition` 11,1%, `__mulsi3` 10,7%, `R23_MapRead` 8,5%, `P_SetThingPosition` 6%, `R_PointInSubsector` 5,2%, `R23_MapWrite` 4,6%. **Esses percentuais não são de FPS total e não devem ser somados como ganhos possíveis.** R118 reduziu custo de multiplicações; R119 otimizou acessos a secnodes; portanto refazer perfil da **base R119** especificamente na E1M7, não repetir cegamente os alvos antigos.

## Plano solicitado (ordem proposta)

1. **Reproduzir e explicar a anomalia de medição da R120**. Criar diagnóstico de `frames.tsv` e `PROFILE.json` para quatro demos/variantes. Exigir ranges completos, status correto, igualdade de `gametic` e `leveltime` por quadro, e margens de amostragem consistentes. Validar controle vs controle e controle vs controle em processos independentes.
2. **Localizar os piores períodos de gameplay E1M7 (mínimo 1,5 FPS em tic425)**. Capturar custo por tic/quadro, lista top-10 de janelas de ~1 s sem cargas, e hot functions/categorias no trecho crítico. Se disponível, distinguir CPU do 68000 vs espera de VDP/SRAM e overhead de sondas. Checar se a pior janela de R118 em tic296 de fato melhorou na R119.
3. Propor **2–3 mudanças locais e independentes** com hipóteses de custo verificáveis (e.g. janela SRAM em hotpath `P_CheckSight`, redução comprovada de acessos `R23_MapRead`/`R23_MapWrite`, `P_CheckPosition`, caminhos de `P_MobjThinker`), sem perda de precisão e sem introduzir estado inconsistente ou quebrar IRQ/SRAM. Não repetir R120 sight/collision sem hipótese NOVA bem fundamentada. Em particular, **não** manter SRAM habilitada através de callback, allocator ou função que pode reentrar na SRAM; respeitar helpers delimitados `R25_SRAM_BEGIN/END`.
4. Build isolado por variante e **A/B acumulativo** contra `R119 BOTH`. Guardar ROM/ELF/DEMO exclusivamente na pasta privada runner; publicar GitHub apenas relatórios/metadados sem WAD/ROM privada.
5. Regras de aprovação: (a) compilar PLAY/PERF; (b) 10/10 demos logic fingerprint idênticos, com checkpoints não vazios; (c) pixel identity Shadow OFF e ON; (d) `.data`/`.bss` inalterados e zone heap segura; (e) PLAY smoke; (f) ganho reproduzível medido no benchmark **10 demos da ROM PLAY**, preferencialmente com avanço da *pior janela* E1M7 sem piorar FPS médio. Se uma variante só melhora o médio e piora o mínimo, reportar o tradeoff.
6. **Não consolidar na main** nem substituir a R119 sem autorização expressa. Entregar relatório de hipóteses, diffs, hashes das ROMs e links às runs/artefatos, com ganho medido **e falhas honestamente registradas**.

## Localização, ambiente, relatórios

- Repositório: `https://github.com/bollux78/MD-DOOM64KB`.
- R119 (base) branch: `exp-chatgpt-r119-secnodes-collision-20261103`; run **41708926876**, passou automatizados: `https://github.com/bollux78/MD-DOOM64KB/actions/runs/41708926876`.
- R120 branch: `exp-chatgpt-r120-sight-collision-20261103`; run **41726158554** `https://github.com/bollux78/MD-DOOM64KB/actions/runs/41726158554` artifact `13275254154`: `https://github.com/bollux78/MD-DOOM64KB/actions/runs/41726158554/artifacts/13275254154`.
- Runner: CachyOS, fish por padrão mas workflow bash; Marsdev m68k-elf-gcc; SGDK; BlastEm. Pasta ROMs R119: `/home/dan/Projetos/Personal/r119-sram/run-41708926876-1/c-both/`; R120: `/home/dan/Projetos/Personal/r120-sight-collision/run-41726158554-1/`.
- Cuidado: base branch R119 contém gerador por overlays. Ao compilar scratch, aplicar R118 `mulvc` e R119 `both` **uma vez**, depois possíveis overlays; aplicar R120 somente se quiser reproduzir a regressão sem ganho. `scripts/lab/apply_r118.py`, `scripts/lab/apply_r119.py`, `scripts/lab/build_r71a12mul_hud.py`, `r117_profile.py`, `r118_ab.py`.
- Limites benchmark: no máximo 10.000 frames em sondas, nunca mudar H40/recorte/IA/Shadow/clock durante A/B; uso do benchmark PLAY como árbitro final.

## Resultado esperado do Cláudio

**Primeiro**: diagnóstico reproduzível de por que o A/B R120 apresentou falsos +167%, com correção validada contra a R119. **Depois**: experimento R121 que ataque efetivamente as piores janelas de gameplay da E1M7, com demonstração de ganho em vez de especulação. Se não existir otimização segura com ganho material, recomendar parar: R119 BOTH permanece candidata final.

## ATUALIZAÇÃO — ANOMALIAS DE ÁUDIO NO MEGA DRIVE REAL (03/11/2026)

**Nova evidência comunicada pelo usuário, investigar em paralelo ao FPS mínimo — não assumir que é efeito da R118/R119:**

- **Sintoma:** durante a música aparecem sons anormais semelhantes a *buzinas* / **notas de instrumento presas** por alguns segundos; depois desaparecem espontaneamente, enquanto **o restante da música continua normalmente**, sem interromper a execução do jogo.
- **Ambiente:** reproduz no **Mega Drive físico** com EverDrive V1 clone chinês; **não reproduz no BlastEm** nos testes do usuário.
- **Histórico corrigido:** o usuário confirmou que **o defeito ocorre ocasionalmente desde a R116**. Não afirmar que a R116 é limpa ou que surgiu na R118/R119; a R119 apresentou sintomas claros, mas versões anteriores também.
- **Correlação com IA:** na **R118**, mudar para AI Low aparentemente reduz bastante a frequência, e voltar para AI Normal no mesmo mapa fez o defeito voltar. **Porém AI Low NÃO elimina o problema**: também pode surgir esporadicamente. Trata-se de correlação com carga/processamento, **não de demonstração causal**.
- **SFX:** desativar os efeitos sonoros **não parece ajudar**. Prioridade menor para hipótese simples de competição música/SFX, mas não está totalmente excluída.
- **Hardware do flashcart:** o EverDrive V1 clone também tem um problema **distinto** de travamentos durante 'gravando...' ROMs grandes (>512 KiB com muito mais frequência), inclusive com cartões SD diferentes que funcionam em outros aparelhos. Não atribuir automaticamente o defeito de áudio a esse problema de gravação; testar áudio isoladamente para separar o hardware do cartucho, o código e a temporização.

### Hipóteses técnicas (não confirmadas)

1. Perda/atraso de atualização de **key-off / estado de canal FM** no **XGM2 / Z80 / YM2612** sob determinadas condições de carga. O evento musical posterior pode restaurar o canal.
2. Disputa temporária de barramento, acesso concorrente ao Z80, interrupções/VDP/DMA e/ou **janelas de SRAM**, provocando atualização tardia ou perdida do driver no hardware real, mas não no BlastEm. Verificar primeiro a implementação concreta do SGDK/XGM2, não supor um mecanismo inexistente.
3. Condição específica da música/driver ou de compatibilidade do clone/console. Repetir na mesma faixa para identificar se é determinístico no tempo musical.

### Experimentos recomendados ao Cláudio

1. **Verificar configuração e pontos de integração do driver XGM2**: chamadas de reprodução/pausa/troca, controle de Z80, estado do bus request, interrupções, processamento a cada VBlank, DMA e uso da SRAM. Procurar períodos críticos em que o Z80 possa ficar impedido de atender aos comandos; instrumentação leve, sem alterar o som.
2. Fazer **três ROMs diagnósticas** em branch separada: (a) música isolada, sem lógica do DOOM nem SFX; (b) mesma música + carga artificial ajustável de CPU/VDP, sem SFX; (c) jogo normal + música, com AI Normal/Low e SFX ligados/desligados. Medir tempo até nota presa, persistência e se música prossegue. Manter mesmas músicas e condições no hardware.
3. Conferir reprodução com driver XGM2 padrão/integração SGDK, se possível com ROM de referência que reproduza o mesmo fluxo musical. Se o defeito não surgir na música isolada, investigar interação com engine e carga; se surgir, concentrar análise em driver, dados ou hardware.
4. **Não usar key-off forçado periódico** como primeira correção: mascararia o defeito e cortaria notas legítimas. Não modificar a R119 principal nem comprometer desempenho, imagem ou lógica sem testes A/B aprovados.
5. **Reportar apenas achados medidos**; o teste no console físico é indispensável, já que BlastEm não reproduz a anomalia. Entregar parâmetros de reprodução fáceis para o usuário, que está testando no EverDrive V1.

**Prioridades em paralelo:** (A) investigar a anomalia de medição da R120 e otimizar os piores FPS da E1M7; (B) rastrear e corrigir a corrupção intermitente do áudio presente desde a R116. Não misturar mudanças de áudio e desempenho na mesma ROM experimental sem variantes separadas.
