# R93b — CRAM SH1, rodada 2 (estudo do Cláudio a pedido do Werk)

**Somente estudo.** Nenhuma ROM para entrega, nenhum header de produção alterado. A SH1 atual continua sendo a referência. **Não se afirma que o bege foi corrigido.**
Branch: `exp-claudio-r93b-cram-study-20261030`. Run no runner: https://github.com/bollux78/MD-DOOM64KB/actions/runs/40993041262 (artefato `r93b-cram-study`). A ROM PERF compilada no job serviu só para captura.

## 1. Método (o que foi pedido pelo Werk → o que foi feito)

| Pedido | Feito |
|---|---|
| Guarda de croma nos dois estados, `ideal_chroma` no CSV | Guardas por (banco, estado, código de entrada) com ≥0,1% das amostras exibidas: croma ≤ max(6, SH1), matiz ≤ max(8°, SH1) para alvos com C>10, L ≤ max(6, SH1), neutros continuam neutros. CSV com `ideal_chroma_normal/shadow`. |
| Misturas M50 e todos os códigos afetados | Cada candidata passa pelo pipeline inteiro: CRAM → cor exibida (média M50 de cada código com o seu parceiro, ×0,5 na sombra) → remapeamento R79 → decisão conjunta R91. O CSV lista, por slot, os códigos que o usam diretamente ou como parceiro. |
| Pesos de capturas com Shadow On, A2 e L3 separados | R92 toggle em versão PERF, DEMO3 com `r92_shadow_on=1`, uma captura no modo A2 e outra no L3. Por frame, duas paradas: na entrada de `I_FinishUpdate` (códigos antes do passe = chaves) e em `R92_AfterPass` (saída). Contei as chaves dentro do retângulo transferido, só nos frames com paleta 0. |
| Brilho médio e proporção de blocos em sombra nos mesmos tics | Medidos e usados como guarda (±5 pontos de sombra, ±1,5 de L na busca do r93b). |
| Sem palavra aceitável → manter e marcar; compromisso só como alternativa explícita | Implementado: `status=no_acceptable_solution` + `best_compromise` e as guardas que ele violaria, nunca aplicado. |

**Validação do modelo:** o modelo reproduz exatamente o gerador de produção (tabelas `r79_map`/`r79_cost` idênticas) e reproduz a saída real da ROM capturada: **0 divergências em 387.651 blocos por modo** (estado e códigos).

**Cobertura das capturas:** 703 frames por modo, tics 2–704 do DEMO3 (primeiro terço de E1M1; 691 frames com paleta 0). O limite de 10.000 quadros emulados por execução terminou a captura antes da última sala, que o usuário apontou. Essa sala **não está nos pesos**.

**Modelo de cor:** o proxy do R79 (DAC linear k·255/7, sRGB/Lab). Acrescentei uma segunda leitura com a tabela de DAC de hardware `[0,52,87,116,144,172,206,255]` só para conferência. Nenhum dos dois é medição do CRT.

## 2. Resultados (pesos reais, DEMO3 Shadow On)

"Marrom" = alvos com C>10 e matiz 30–95°: **25,8% das amostras exibidas no A2 e 17,9% no L3.** Matiz positivo = puxa para o amarelo. "Visual SH1" = dE médio entre o que a candidata mostra e o que a SH1 mostra para o mesmo código.

### A2

| Variante | dE médio | Erro de matiz marrom (LIN / HW) | Viés de matiz marrom | Croma marrom | Bege (heurística) | L médio | Sombra | Distância do visual SH1 | Guardas |
|---|---|---|---|---|---|---|---|---|---|
| SH1 atual | 5,56 | 9,2° / 9,1° | **+8,2°** | −1,7 | 0,50% | 30,1 | 63,3% | 0 | — |
| R93 (Werk) | 5,10 | 6,1° / **9,2°** | −3,5° | +3,9 | 0,07% | 31,3 | 59,3% | 4,9 | viola croma, matiz, L |
| Rodada 2 "full" (512 palavras) | 1,10 | — | — | — | 0,03% | 30,4 | 64,6% | **5,5** | passa |
| Rodada 2 "mínima" (±1, só slots marcados) | 5,12 | — | — | — | 0,49% | 30,0 | 63,8% | 0,45 | passa (só 2 slots azuis mudaram) |
| **R93c compromisso** | 4,65 | **7,2° / 7,5°** | +6,0° | −0,9 | 0,08% | 29,6 | 61% | 1,3 | viola L em 2 códigos (0,18% e 0,62% das amostras) |

### L3

| Variante | dE médio | Erro de matiz marrom (LIN / HW) | Viés | Croma marrom | Bege | L médio | Sombra | Distância do visual SH1 | Guardas |
|---|---|---|---|---|---|---|---|---|---|
| SH1 atual | 4,07 | **15,1° / 14,6°** | **+9,1°** | +1,1 | 0,45% | 29,8 | 62,8% | 0 | — |
| R93 (Werk) | 4,13 | 13,6° / 13,4° | +5,3° | **−6,0** | 0,28% | 30,6 | 60,8% | 2,4 | viola croma, matiz, L |
| Rodada 2 "full" | 0,60 | — | — | — | 0,05% | 31,0 | 61,1% | **4,6** | passa |
| Rodada 2 "mínima" | 3,30 | — | — | — | 0,31% | 29,8 | 63,2% | 1,0 | passa (3 slots) |
| **R93c compromisso** | 4,02 | **6,2° / 7,0°** | −3,6° | −1,5 | 0,58% | 29,7 | 62% | 1,5 | viola L/matiz/croma em 4 códigos (o maior com 10,4% das amostras, L −8,8 contra −5,9 da SH1) |

## 3. O que os números dizem

1. **O bege existe e é um desvio de matiz dos marrons, não um caso raro.** A heurística de bege do Werk só marca 0,5% das amostras, mas os marrons são 18–26% da tela e a SH1 os puxa em média **+8° a +9° para o amarelo** (erro absoluto de 9° no A2 e 15° no L3). Isso bate com o que o usuário viu.
2. **A busca livre ("full") é enganosa e não deve ir para ROM.** O alvo do R79 é a cor da R91-control, então a busca reembaralha a CRAM inteira (o azul vira cinza, o vermelho vira verde, com os códigos remapeados) e chega a dE ≈ 1 do control. O resultado fica tão longe do visual SH1 (4,6–5,5) quanto a própria SH1 está do control. **Ou seja, apaga o efeito de shadow que o usuário aprovou.** Conclusão de método: com esse alvo, "menor erro" equivale a "parecer o control". O objetivo precisa medir o desvio dos marrons, e não o erro total.
3. **Com as guardas estritas do Werk, os marrons não têm solução.** Na rodada mínima, todos os slots marrons dão `no_acceptable_solution` (A2 0#5, 0#10, 0#12, 0#15, 1#1, 1#7, 1#12, 1#14, 1#15; L3 0#1, 0#2, 0#6, 0#10, 0#11, 1#1, 1#12, 1#13). Os compromissos e as guardas violadas estão em `MINIMAL-SUMMARY.json`.
4. **A candidata R93 do Werk** reduz o bege pela heurística, mas: no A2 o ganho de matiz desaparece com o DAC de hardware (9,1° → 9,2°) e passa do ponto para o vermelho (−8° no HW). No L3 tira 6 de croma dos marrons (acinzenta). Ela também se afasta mais do visual SH1 (4,9 no A2) e baixa a sombra em 4 pontos no A2.
5. **R93c (compromisso, alternativa explícita).** Busca só nos slots que alimentam marrons, cada canal ±1 da SH1, contra o erro de matiz dos marrons nos **dois** modelos de DAC. Limites: distância do visual SH1 ≤ 1,5, sombra ±3 pontos, L ±1, dE total não piora. Resultado: matiz marrom A2 9° → 7°, **L3 15° → 6–7°**, viés de amarelo reduzido, croma e brilho preservados, visual SH1 praticamente mantido. **Não passa nas guardas estritas por código** (lista na tabela). Pela regra do Werk, fica como alternativa para avaliação, não como correção.

Mudanças do R93c (componentes de CRAM de 3 bits, SH1 → R93c):

| Modo | Slot | SH1 | R93c |
|---|---|---|---|
| A2 | pal0 #2 | (4,3,1) | (5,3,1) |
| A2 | pal0 #10 | (5,4,3) | (4,3,2) |
| A2 | pal1 #1 | (3,1,1) | (2,0,0) |
| A2 | pal1 #4 | (4,0,0) | (3,1,0) |
| L3 | pal0 #2 | (4,3,1) | (5,3,2) |
| L3 | pal0 #9 | (5,4,1) | (4,3,0) |
| L3 | pal1 #14 | (4,3,1) | (3,2,1) |

Só p=0. Os efeitos p>0 (flashes) ficam com a CRAM SH1. As tabelas R79/R91 seriam regeneradas a partir dessa CRAM, com o mesmo custo de execução.

## 4. Recomendação

- **Descartar** a "full" (apaga o efeito). Não levar a R93 do Werk para ROM do jeito que está: piora com o DAC de hardware no A2 e acinzenta o L3.
- **Se o usuário quiser testar algo, a candidata é o R93c**, declarado como compromisso, com as violações listadas. Teste sugerido: uma ROM R92 com a CRAM R93c, comparada à SH1 por captura depois do passe, nas mesmas cenas: portas, paredes cinza e a última sala de E1M1. A palavra final é do CRT.
- **Antes disso, para fechar a lacuna de cobertura:** capturar a última sala de E1M1 (outra janela de tics: começar a captura depois do tic ~1400, ou dividir em duas execuções dentro do limite de 10.000 quadros) e repetir o R93c com esses pesos. A sala que o usuário apontou hoje não pesa no estudo.
- **Rodada 3 do método:** trocar o objetivo de "erro total contra o control" por "desvio de matiz e croma por família (marrom, verde, pele, neutro) + distância do visual SH1". Foi esse o critério que produziu o R93c.

## 5. Arquivos

- `docs/analysis-r93b/FULL-SUMMARY.json`, `FULL-SLOTS.csv`: busca livre, com as métricas de SH1, R93 e full.
- `docs/analysis-r93b/MINIMAL-SUMMARY.json`, `MINIMAL-SLOTS.csv`: busca mínima e os slots sem solução, com compromissos.
- `docs/analysis-r93b/CODES-SH1-vs-MINIMAL.csv`: cada código, cada estado, participação na tela, LCh do alvo, da SH1 e da candidata.
- `docs/analysis-r93b/R93C-COMPROMISE.json`: o compromisso, com as palavras e as métricas LIN/HW.
- Scripts: `scripts/lab/r93b_capture.py`, `r93b_cram_study.py`, `r93c_brown_search.py`. Workflow: `.github/workflows/r93b-claudio-cram.yml`.
- As chaves (pesos) ficam no artefato do run, `study/*/keys-A2.npy` e `keys-L3.npy`, para novas rodadas offline sem recapturar.
