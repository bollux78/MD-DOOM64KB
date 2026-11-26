# FERRET-MD — relatório Werk para Cláudio
**26/11/2026 | R09 `2dfd46883c3ddb920011cf37840ab58f51e0b26a` | Auditoria independente concluída no x360**

## 1. Resumo executivo

- PVS angular de 16 direções: 7.690/7.690 estados de rasterização idênticos à R09, 24/24 capturas MAME idênticas pixel a pixel, 12/12 mailboxes legadas equivalentes à R04 exceto o contador de candidatas. Redução de 32,1% das candidatas nas 12 poses R04, mas apenas 4,0% de ganho de velocidade no render MAME; nas cinco câmeras Alpha2, ganho de 2,4%. O filtro não reduz mais as chamadas de `fr_project` após o pré-teste de frustum da R09.
- GPGX, mesmas cinco câmeras, sem SRAM: Alpha2 4,832 FPS; R09 2,305 FPS; R09 angular 2,359 FPS (média agregada de tempo por quadro, não média aritmética de FPS). A R09 gasta 3,51× o tempo do pipeline de paredes da Alpha2 e 2,10× o tempo do quadro completo. Limites são próximos, não perfeitamente iguais; R09 não executa gameplay.
- SRAM16: Alpha2 6,228 FPS. R09 com SRAM detectada, mas apresentação WRAM, mantém 2,305 FPS. Forçar o caminho SRAM da R09 atual (cópia e verificação de staging) derruba para 1,248 FPS. A origem DMA confirmou uso efetivo; não é falha de detecção. Não utilizar esse caminho como acelerador.
- Escalador gerado Alpha2: nova medição de 2.680.084 escritas de bytes lógicos em 429 intervalos, aproximadamente 26,86 ciclos 68000/byte no agregado; 26,65–27,47 por câmera/modo. É um alvo concreto para implementação independente, sem copiar código original.
- Recomendação: manter o PVS angular opcional e priorizar escaladores gerados, kernels e preparação de spans. Não integrar a máscara de 349.540 bytes por padrão antes de medir variantes compactas em conjunto com as novas otimizações de Cláudio.

## 2. Reprodutibilidade

- [PR #44, PVS angular](https://github.com/bollux78/MD-DOOM64KB/pull/44), base congelada `research-ferret-r09-reference-2dfd468`, commit testado `1d5368ca34fbd077999a6a715de6cbcec561ff83`.
- [Run 45909219927](https://github.com/bollux78/MD-DOOM64KB/actions/runs/45909219927), job 140213264228: todos os passos aprovados (build, diferencial, MAME, screenshots/mailboxes, GPGX).
- [PR #43, Alpha2 independente](https://github.com/bollux78/MD-DOOM64KB/pull/43), [run 45909125750](https://github.com/bollux78/MD-DOOM64KB/actions/runs/45909125750), job 140212953420, commit `a58019270816564ef95560e58d17a3acd5aaaa06`: sucesso integral.
- [PR #42](https://github.com/bollux78/MD-DOOM64KB/pull/42), [run 45908147029](https://github.com/bollux78/MD-DOOM64KB/actions/runs/45908147029), job 140209799515, head `0c55efeaa9a98735ed9adeef151ddc1b14aad49a`: sucesso integral.
- GPGX fixado em `2499cd3e3d1d8b7d0130d8b2825adb4cc608b2c0`, NTSC, clock 53.693.175 Hz, 896.040 master cycles/VBlank, 7 master cycles/ciclo 68000. Alpha2 autenticada SHA256 `47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267`.
- Assets e capturas permanecem privados. Nenhum commit na branch do Cláudio; nenhuma integração/merge.

## 3. PVS angular: resultados R09 exatos

O filtro offline usa limites Q14 sobre bbox da célula FRV2, agrupados por direção. Mantém casos incertos e com risco de wrap. Compara a R09 com e sem `FR_ANGLE_PVS`, sem mudar projeção, ordem de travessia ou rasterização. A otimização de frustum inline de Cláudio em `2dfd468` já elimina as mesmas paredes antes de `fr_project`; por isso o ganho residual do PVS é economizar backface/transformação/pré-teste, não chamadas do projetor.

### 12 poses R04 — MAME, `mame_render_time.lua`, BENCH

| Pose | R09 ms | Angular ms | Candidatas antes | Depois | Removidas | Chamadas fr_project (ambas) | Projetadas (ambas) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 614 | 603 | 235 | 186 | 49 | 49 | 47 |
| 1 | 286 | 285 | 82 | 82 | 0 | 50 | 50 |
| 2 | 198 | 197 | 82 | 81 | 1 | 38 | 36 |
| 3 | 169 | 169 | 9 | 9 | 0 | 5 | 5 |
| 4 | 432 | 405 | 460 | 312 | 148 | 124 | 114 |
| 5 | 250 | 218 | 289 | 119 | 170 | 44 | 44 |
| 6 | 143 | 143 | 3 | 3 | 0 | 2 | 2 |
| 7 | 144 | 144 | 3 | 3 | 0 | 2 | 2 |
| 8 | 168 | 165 | 69 | 59 | 10 | 3 | 3 |
| 9 | 253 | 241 | 153 | 108 | 45 | 42 | 42 |
| 10 | 428 | 393 | 302 | 108 | 194 | 55 | 54 |
| 11 | 536 | 519 | 460 | 388 | 72 | 105 | 96 |
| Total | 3620* | 3482 | 2147 | 1458 | 689 | 519 | 495 |

* Total do Lua antes do arredondamento individual; as linhas exibidas somam 3621 ms. Speedup 1,040× (4,0%); excluindo pose inicial, aproximadamente 4,45%. Maior ganho nas poses 5 e 10. A primeira pose inclui preparação única do renderer.

### Cinco câmeras Alpha2 equivalentes — MAME, segunda renderização

| Câmera | WAD (x,y,olho,graus) | R09 ms | Angular ms | Candidatas antes→depois | Removidas | fr_project (ambas) | Projetadas (ambas) |
|---|---|---:|---:|---|---:|---:|---:|
| Spawn | 1056,-3616,41,90 | 374 | 364 | 235→186 | 49 | 49 | 47 |
| Zigzag 0 | 2980,-3286,17,0 | 299 | 298 | 86→83 | 3 | 26 | 26 |
| Zigzag 64 | 2980,-3286,17,270 | 347 | 342 | 156→137 | 19 | 51 | 46 |
| Zigzag 128 | 2980,-3286,17,180 | 538 | 515 | 537→433 | 104 | 187 | 153 |
| Zigzag 192 | 2980,-3286,17,90 | 328 | 322 | 101→74 | 27 | 21 | 20 |
| Total | — | 1886 | 1841 | 1115→913 | 202 | 334 | 292 |

Speedup 1,0244×, redução de tempo de 2,39%; 18,1% menos candidatas. Não confundir candidatas com chamadas ao projetor ou paredes realmente desenhadas (R09 conta como projetadas também spans totalmente ocultos).

### Validação e custo de ROM

| Teste | Resultado |
|---|---|
| Todas as orientações no spawn | 360/360 |
| Todas as orientações no zigzag | 360/360 |
| Distribuídas pelas células | 6970/6970 |
| Capturas MAME R04 + câmeras Alpha2 repetidas | 24/24, zero pixels diferentes |
| Mailbox R04 legado | 12/12, todos campos iguais exceto contador de candidatas |
| VRAM GPGX (4 combinações ROM/modo) | 48/48 exatas, zero erros |

No diferencial de 7690 câmeras, candidatas 1.899.405→1.397.312 (−26,43%); chamadas `fr_project` 372.534→372.534; projetadas 322.438→322.438. Estado completo comparado, incluindo framebuffer e arrays de clipping/depth/tags.

| Direções | Máscaras/índice (bytes) | Redução offline de candidatas |
|---:|---:|---:|
| 8 | 172512 | 20,43% |
| 16 | 349540 | 26,71% |
| 32 | 699732 | 29,97% |

Somente 16 direções foram benchmarkadas nesta rodada. ROM R09 1.179.648 bytes; angular 1.507.328 bytes (+327.680 no arquivo alinhado). As tabelas são grandes para um ganho de 2–4%. Avaliar compressão ou índices por região e direção apenas se a economia real justificar. O compilador PVS é independente dos dados de visibilidade da Alpha2.

## 4. Alpha2 × R09 no mesmo GPGX

Limites Alpha2: PC de entrada da visibilidade `077402` até fim das paredes `07E13E`; quadro inteiro de entrada a próxima entrada. Limites R09: mailbox stage 3→4 (preparação, visibilidade, projeção, desenho; BENCH sem hashes), stage 3→próximo stage 3 para quadro. A R09 não executa gameplay nem sprites do jogo. Portanto, não são cargas idênticas; ainda assim, agora o relógio, emulador, modo de memória e câmeras são controlados. Spawn forçado na Alpha2 célula 131, diferente da célula 29 natural. As cinco câmeras são geometricamente correspondentes, não imagens pixel-idênticas à Alpha2.

### Sem SRAM (WRAM)

| Câmera | Alpha2 paredes ms | R09 paredes ms | Angular paredes ms | Alpha2 quadro ms | R09 quadro ms | Angular quadro ms |
|---|---:|---:|---:|---:|---:|---:|
| Spawn | 85,23 | 379,77 | 369,04 | 177,39 | 433,89 | 417,20 |
| Zigzag 0 | 98,69 | 303,72 | 302,39 | 203,53 | 350,45 | 350,45 |
| Zigzag 64 | 110,16 | 351,95 | 346,91 | 208,92 | 400,52 | 400,52 |
| Zigzag 128 | 144,64 | 545,60 | 522,25 | 245,38 | 600,77 | 567,40 |
| Zigzag 192 | 106,42 | 332,57 | 326,75 | 199,60 | 383,82 | 383,83 |

R09/Alpha2 pipeline paredes: 4,46× / 3,08× / 3,20× / 3,77× / 3,13×. Agregado 3,51×. Quadro inteiro: 2,45× / 1,72× / 1,92× / 2,45× / 1,92×; agregado 2,10×. PVS ganha 2,48% no render GPGX, 2,36% no quadro agregado; espera pelo VBlank absorve parte da economia em certas poses.

### SRAM16 real selecionada

| Câmera | Alpha2 paredes ms | R09 paredes ms | Alpha2 quadro ms | R09 quadro ms, SRAM forçada |
|---|---:|---:|---:|---:|
| Spawn | 94,63 | 379,68 | 131,48 | 801,03 |
| Zigzag 0 | 107,04 | 303,63 | 149,10 | 717,59 |
| Zigzag 64 | 118,01 | 351,87 | 161,34 | 767,66 |
| Zigzag 128 | 152,65 | 545,52 | 196,65 | 967,91 |
| Zigzag 192 | 114,81 | 332,49 | 164,28 | 750,97 |

R09 com SRAM16 disponível, mas NÃO selecionada: os mesmos tempos de paredes da WRAM e quadro virtualmente igual (diferenças inferiores a 0,01 ms). DMA WRAM origem decimal 16716762 (0xFF13DA). SRAM16 forçada: `sram_selected=1`, DMA origem 2139648 (0x20A600), 12/12 VRAM exatas. Quadro 1,846× mais demorado do que R09 WRAM, pois a versão existente copia 23040 bytes e relê/verifica tudo a cada quadro. Pipeline paredes permanece praticamente igual; penalidade após render é de cerca de 367 ms em cada câmera. Não é um acelerador; para usar SRAM, converter diretamente no destino e eliminar verificação integral por quadro após probe inicial, preservando fallback. Mesmo um novo backend deve ser medido; a WRAM segue obrigatória.

| Configuração | FPS agregados, cinco câmeras |
|---|---:|
| Alpha2 WRAM | 4,832 |
| R09 WRAM | 2,305 |
| R09 angular WRAM | 2,359 |
| Alpha2 SRAM16 | 6,228 |
| R09 SRAM16 detectada, apresentação WRAM | 2,305 |
| R09 SRAM16 selecionada, staging atual | 1,248 |

Alpha2 SRAM16 +28,9% de FPS sobre Alpha2 WRAM (agregado). O original sem SRAM escreve ~11520 words pela CPU no VDP; com SRAM, conversão externa e DMA fracionado. A diferença de modos não pode ser atribuída ao kernel de paredes.

## 5. Escaladores originais: medição, não cópia

Auditoria estrutural anterior: 2048 índices de escala, 159 endereços distintos de rotina, 158 mapeamentos distintos; 72 linhas por rotina, 12 bytes por linha + 4 bytes de terminação, 138012 bytes de código de parede, tabela de índices 8192 bytes. Entrada calculada na linha inicial, contador DBF para extensão, retorno indireto, deslocamento do texel incorporado à instrução, destino pós-incrementado (stride de 2). Não há leitura de tabela de offsets nem teste de transparência por texel nesse caminho. Esse contrato é descrição de comportamento; não transportar bytes/instruções originais para a engine independente.

Nova medição exclusiva da faixa de escaladores de parede (não a faixa geral de scalers): classifica escritas, DBF, saltos e outras instruções executadas; nenhuma instrução não classificada foi observada. Ciclos do emulador atribuídos a essa região divididos por 7 e pelo número de escritas. Um byte lógico representa dois pixels horizontais, com duplicação vertical na apresentação. Não inclui preparação/dispatch fora da faixa.

| Câmera | WRAM escritas | WRAM ciclos/byte | SRAM16 escritas | SRAM16 ciclos/byte | Entrada média WRAM (linha 0–71) |
|---|---:|---:|---:|---:|---:|
| Spawn | 103200 | 27,4667 | 142647 | 27,4715 | 28,84 |
| Zigzag 0 | 266511 | 26,8194 | 374556 | 26,8194 | 19,30 |
| Zigzag 64 | 301500 | 26,8353 | 402000 | 26,8353 | 28,85 |
| Zigzag 128 | 194773 | 26,6548 | 238754 | 26,6548 | 13,51 |
| Zigzag 192 | 290130 | 26,8272 | 366013 | 26,8262 | 28,50 |

Total: 2.680.084 escritas, 503.878.760 master cycles, ~26,86 ciclos CPU por byte. Contagens somam amostras de diferentes números de quadros, não custo por quadro. A média inclui DBF e retorno. A distribuição por câmera confirma que a SRAM não é responsável pelo desempenho dos escaladores.

A lista de visibilidade Alpha2 tem 213 paredes em cada direção do zigzag e 20/25/95/22 despachos de kernel (WRAM). Na R09, as chamadas reais ao projetor já caíram para 26/51/187/21. O sky/zigzag128 continua sendo o caso crítico. Não explicar a vantagem original somente pelo número de candidatas: custo do loop de parede, preparação e rasterização importam muito mais após o pré-teste R09.

**Sugestão para Cláudio:** comparar o kernel gerado independente com o kernel R09 usando a mesma contagem de bytes escritos; medir ciclos exclusivos por byte e tempo inclusivo de preparo + desenho, incluindo spans curtos, longos, offsets negativos, wrap e alternância dos nibbles. Meta inicial ~27 ciclos/byte lógico no núcleo, sem reduzir resolução ou qualidade. Geração independente a partir de parâmetros matemáticos de escala, não de código de máquina da ROM. A métrica não prova que o scaler seja o único gargalo; os perfis por fase da R09 também devem orientar a prioridade.

## 6. PR #42: números oficiais

MAME 12 poses: R06 5,180 s, revisão Cláudio 3,620 s (1,431×); inclui primeiro frame. Luma_corr nas cinco câmeras 0,588/0,426/0,336/0,513/0,511; edge_corr 0,594/0,184/0,059/0,293/0,120; color_dist 30,2/33,4/33,8/40,9/32,4. Correlações de luminância acima do limiar 0,30 e da pose errada; não prova equivalência de pixels ou geometria exata com Alpha2. Os dados foram obtidos antes da rodada angular final. A paridade exata R04 no modo legado foi verificada de forma automática no PR44 (exceto contador de candidatas).

## 7. Hardware e regra do desafio

ROMs disponíveis localmente no x360:

```
~/.local/share/ferret-research/playtest/R09-audit-45909219927/FERRET-MD-R09-BENCH.bin
~/.local/share/ferret-research/playtest/R09-audit-45909219927/FERRET-MD-R09-VERIFY.bin
~/.local/share/ferret-research/playtest/R09-audit-45909219927/FERRET-MD-R09-ANGLE-BENCH.bin
```

BENCH sem hashes; VERIFY para estabilidade/observação. Teste físico não realizado pelo Werk, portanto não reportar FPS de console como medido. Sugestão: categoria principal sem SRAM, categoria adicional SRAM16, NTSC, mesmas câmeras, medir quadro inteiro e pipeline separadamente; confirmar modo efetivamente usado. O acordo com Ferret e professor depende dos participantes.

## 8. Arquivos privados e próximos passos

- `~/.local/share/ferret-research/angular-pvs/45909219927/`: builds, cenas, capturas e logs MAME; `r04-*` e `alpha-*`.
- `~/.local/share/ferret-research/alpha2-profile/45909125750/`: perfis por quadro do original.
- `~/.local/share/ferret-research/r07/45908147029/`: rodadas PR42.
- Artefatos dos runs acima: JSON/TXT numéricos, incluindo `pose-census.json`, `differential.json`, `screen-parity.json`, `render-times.txt`, `alpha-*-gpgx-mode*.json`, `alpha2-profile.json`.

Decisão de Werk: manter o PVS angular experimental; o ganho medido não justifica integração automática com custo atual. Continuar independência da engine, WRAM obrigatória, SRAM como aceleração opcional somente após medição e validação. Nenhuma alteração na branch de desenvolvimento de Cláudio.
