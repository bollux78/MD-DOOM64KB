# R128: simplificações de mapa e comportamento (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`. **Base:** R126b early. **O usuário aceitou** mudança de comportamento e pequenas mudanças nos mapas, desde que o jogo continue bem reconhecível.

| Variante | O que muda | Onde |
|---|---|---|
| `stairs` | Pares de degraus pequenos viram um degrau só. Até 8 unidades, o degrau de baixo sobe; com 16 (as escadas do E1M1), os dois vão para o meio. O espelho entre eles some do render, porque as duas linhas ficam idênticas (`RF_IGNORE`). Nenhum degrau passa de 24 nem fica com menos de 56 de altura livre. Não mexe em setores com special ou tag, nem em vizinhos de linhas especiais, portas ou elevadores. Teste local: E1M1 6, E1M2 20, E1M3 12, E1M4 5, E1M5 8, E1M6 23, E1M7 10, E1M8 2 e E1M9 7 pares fundidos. | `scripts/lab/r128_stairs.py`, passo do build depois do `r89_align_maps` |
| `corpses` | O cadáver de monstro some 2 s depois do último quadro da morte; o do jogador fica. O contador reaproveita `movecount`. | `P_MobjThinker` |
| `sight` | Um monstro só faz teste de visão numa janela de 4 tics a cada 12 (defasada por monstro); fora dela, não vê. Os testes do jogador não mudam. | `P_CheckSight` |
| `far` | Sprites a mais de 1.280 unidades não são desenhados. | `R_ProjectSprite` |
| `all` | as quatro juntas | — |

Nenhuma variante usa RAM nova. A correção de overflow da R126b continua valendo.

**Workflow `r128-claudio-simplify.yml`:**
- control = R126b, mais as 5 variantes.
- **Continuam fatais:** build, ROM e BSS, `.data`/`.bss` iguais, música abaixo de 2 MB, travamento/`I_Error`/fim inesperado nas 10 demos, e o PLAY smoke.
- **Viram só relatório:** identidade de lógica, pixels e A/B (divergências são esperadas).
- **Árbitro:** o Run All do usuário com as ROMs `r128-*-pl`, a começar pela `all`, comparado com a R126b (8.331,12 s, mínimo 1,9).

**Para disparar:**
```fish
git fetch origin; git checkout exp-claudio-r121-e1m7-20261103
date -u > .github/triggers/r128-claudio-simplify.trigger
git add .github/triggers/r128-claudio-simplify.trigger; and git commit -m "R128: trigger"; and git push
```
