# Revisão do Cláudio: R93, CRAM SH1 re-quantizada (`review-chatgpt-r93-cram-20261030`)

Revisei `R93-CRAM-REVIEW.md`, `r92_cram_study.py`, `CRAM-SUMMARY.json` e `CRAM-SLOTS-P0.csv`. Recalculei cada slot alterado nos dois estados com o mesmo proxy (`to_lab` do R79). Nenhuma ROM foi criada.

## Veredito

**A direção está certa. O candidato corrige o matiz, mas troca o bege por marrons e verdes acinzentados.** Antes de virar ROM de teste, recomendo **uma rodada a mais com guarda de croma**.

## 1. O que está bom

- O objetivo está bem posto: normal = ideal contínuo ×1,35, sombra = metade. Busca nas 512 palavras e depois R79 e R91 regenerados, então códigos, custos e decisão de estado ficam consistentes. Sem cópias duplicadas e com o mesmo custo de execução.
- Os slots cinza (p=0) não mudaram, e o índice 0 está preservado.
- Nos 10 slots alterados (6 no A2, 4 no L3), o **dE melhora nos dois estados**, normal e sombra, em todos eles.
- O matiz do marrom principal (3,2,1) volta de 81° para 69° (ideal 67°). Era o bege-amarelo que o usuário viu.

## 2. Problema: perda de croma

O `CRAM-SLOTS-P0.csv` não traz o croma ideal. Calculei para os slots que mudaram (croma do estado normal; ideal = original ×1,35):

| Slot (perfil, banco, slot) | Original | SH1 hoje | Candidato | Croma ideal | Hoje | Candidato |
|---|---|---|---|---|---|---|
| A2 0#2, A2 1#12, L3 0#2, L3 1#14 | (3,2,1) marrom | (4,3,1) | (4,3,2) | 38,4 | 44,8 (+6) | **27,7 (−11)** |
| A2 0#12, L3 1#2 | (2,2,1) marrom-oliva | (3,3,1) | (3,3,2) | 28,9 | 40,5 (+12) | 21,3 (−8) |
| A2 1#6 | (1,2,1) verde | (1,3,1) | (2,3,2) | 36,1 | 50,5 (+14) | **26,7 (−9)** |
| A2 1#7 | (4,2,1) marrom-avermelhado | (5,3,1) | (6,3,2) | 57,3 | 55,3 | 56,4 ✓ |
| A2 1#13 | (2,4,1) verde | (3,5,1) | (2,5,1) | 81,2 | 76,0 | 81,6 ✓ |
| L3 0#10 | (1,2,0) verde | (1,3,0) | (2,3,0) | 53,8 | 60,9 | 55,1 ✓ |

- Hoje o SH1 **satura demais**, com matiz amarelo. O candidato **dessatura demais**: o marrom mais usado de E1M1 perde ~28% de croma em relação ao ideal.
- O dE baixa porque, no Lab, a distância favorece acertar L e matiz mesmo perdendo croma. Na tela isso tende a ficar como "marrom acinzentado". Pode não ser bege, mas tampouco é o marrom do Doom.
- A grade de 3 bits limita: para (3,2,1) não existe palavra com matiz e croma perfeitos ao mesmo tempo. A escolha é um compromisso e precisa ser explícita.

## 3. Ajustes sugeridos (só no estudo)

1. **Guarda de croma** junto com a de matiz: |C − C_ideal| ≤ max(6, |C_atual − C_ideal|), ou um termo de croma ponderado no escore. Se nenhuma palavra passar, aceitar o meio-termo com menor erro de **matiz + croma**, e não o menor dE puro.
2. **Avaliar a cor efetiva, não o slot isolado.** O que aparece na tela é a média M50 do slot com o parceiro (`pairs_even/odd`). Um slot que muda altera também os códigos misturados que o usam. O R79 já usa a cor efetiva; o estudo de CRAM deveria usar a mesma.
3. **Pesos normal/sombra medidos, não 0,5/0,5.** Com o ponto de parada pós-passe da R92 dá para contar a fração real de blocos em cada estado no DEMO3 (A2 e L3) e ponderar a busca e o relatório por frequência de tela, não por enumeração das 65.536 chaves.
4. **Reportar o brilho global.** Pela enumeração, o L3 cai de 20.839 para 16.261 chaves em sombra (−22%) e o A2 de 26.407 para 24.973. Se isso se repetir na tela, a imagem fica mais clara e o efeito de sombra, que é o que o usuário gostou, fica mais fraco, principalmente no L3. Medir isso na mesma captura.

## 4. Próximo passo

- **Werk:** rodada 2 do estudo com 1 a 3 acima e o CSV incluindo `ideal_chroma`. Sem ROM.
- Se o croma ficar dentro de ±6 do ideal nos marrons e verdes: uma ROM SH1 com a CRAM nova sobre a R92 (O1, toggle, menu), comparada com a SH1 atual por captura pós-passe nos mesmos tics, nas portas, nas paredes cinza e na última sala de E1M1, em A2 e L3. A palavra final é do CRT.
- Até lá, manter a SH1 atual como referência e não afirmar que o bege foi corrigido.
