# R126: tiro instantâneo para no primeiro obstáculo (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`. **Base:** R122 layout.
**Decisão do usuário (04/11/2026):** o comportamento pode mudar. A lógica **não** precisa ser idêntica ao vanilla nesta variante.

## O que muda (`scripts/lab/apply_r126.py`)
- **Antes:** `P_PathTraverse` juntava as interceptações de **todo** o traço (até 2.048 unidades e 64 blocos) e só depois visitava em ordem. Quase sempre a bala para nos primeiros blocos. Essa é a origem dos picos de 50–60 VBlanks do E1M7 e do E1M3 (R121).
- **Agora,** só nos traços que adicionam things (`P_AimLineAttack` e `P_LineAttack`; usar e deslizar não mudam): depois de cada bloco, o que foi coletado é visitado em ordem de frac, exatamente como em `P_TraverseIntercepts`.
  - Se o traverser parar (parede ou monstro), o traço acaba ali.
  - Se não, a lista é esvaziada e entra o próximo bloco.
- **Diferenças em relação ao vanilla:**
  - o estouro de 64 interceptações (que cancelava o tiro inteiro) praticamente some;
  - um thing com o centro no bloco seguinte pode ser visitado depois de uma linha de duas faces já atravessada, mesmo que esteja um pouco antes dela.
- Sem RAM nova.

## O workflow `r126-claudio-early.yml` (control = R122 layout, early = R126)
- **Continuam fatais:**
  - build;
  - ROM e BSS dentro do limite, `.data`/`.bss` iguais;
  - música abaixo de 2 MB;
  - travamento, `I_Error` ou fim inesperado da demo na checagem de lógica;
  - smoke do PLAY.
- **Viram só relatório:** identidade de lógica (divergência gera aviso com o tic), pixels Off/On e o A/B de tempo. Se a lógica divergir, o A/B estrito pode marcar a demo como INVALID: é esperado.
- **Árbitro:** o Run All oficial do usuário com a `r126-early-pl`, comparado com a R122 (8.688,93 s, mínimo 1,5) e conferindo o FPS CHECK (quadros ÷ tempo).

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r121-e1m7-20261103
date -u > .github/triggers/r126-claudio-early.trigger
git add .github/triggers/r126-claudio-early.trigger; and git commit -m "R126: trigger"; and git push
```
