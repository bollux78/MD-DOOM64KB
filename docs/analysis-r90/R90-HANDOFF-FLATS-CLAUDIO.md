# R90 — Handoff do Cláudio para o Werk: novas LUTs de flats (chão/teto)

**Branch:** `exp-claudio-r90-palmap-analysis-20261029` (base R89 `542501f`)
**Tabelas para integrar:** [`R90-FLAT-LUTS-safe.json`](R90-FLAT-LUTS-safe.json) (rodada 5, versão protegida)

> **Atenção (29/10):** a primeira versão (`R90-FLAT-LUTS-lf050.json`, rodada 4) foi **retirada**. No teste do usuário ela deixou muitos chãos em cinza claro: em A2, L3 e HN existe um par de cinza claro idêntico nas duas paletas, e o termo anti-faixa puxou cores não cinzas para ele (entradas de cinza claro: A2 26→48, L3 32→53, HN 26→53). A rodada 5 substitui essa versão.
**Análise completa:** `scripts/lab/r90_color_analysis.py` (rodadas 1–4); resultado da rodada 4 no run 40923525509 do Actions.

## O que mudar

Só os 8 arrays de flats do `src/r59_color_tables.h` gerado. **Não mudar** CRAM, pares M50, `wall_*`, `comp_*`, sprites nem a HUD.

| Modo (`r59_color_tables[i]`) | Arrays a trocar |
|---|---|
| 0 Hybrid Blue | `r77_h_flat_even`, `r77_h_flat_odd` |
| 1 A2 N25A-M50 | `r76_a_flat_even`, `r76_a_flat_odd` |
| 2 L3 L32F-M50 | `r76_l_flat_even`, `r76_l_flat_odd` |
| 3 HN | `r76_n_flat_even`, `r76_n_flat_odd` |

Cada array tem 256 entradas (índice = cor Doom pós-COLORMAP) com códigos de 1 a 15. O índice 0 (preto transparente) nunca aparece, então não há buracos pretos no chão.

## Pré-condição obrigatória

As LUTs foram calculadas sobre as tabelas da R89 com SHA-256 `38b4319bce37ac31164b757bd8525cf4d71015873b697d61c1aca6a6f1eb03cc` (o `r59_color_tables.h` gerado pela cadeia R89). O passo de injeção deve:

1. conferir esse hash no `r59_color_tables.h` gerado, **antes** de trocar qualquer coisa. Se for diferente (CRAM ou pares mudaram), parar e pedir uma nova rodada de análise;
2. trocar exatamente os 8 arrays, cada um uma única vez (âncora única);
3. conferir que nenhum outro byte do arquivo mudou.

Faça isso como hook pós-geração numa cópia descartável, como nas rodadas anteriores. Não edite os geradores R74/R76/R77.

## Como foi escolhido (rodada 5, protegida)

Para cada cor e cada modo, mantendo a CRAM e os pares M50 da R89, uma entrada só muda se o novo par (coluna par, coluna ímpar), **para aquela cor**:
- errar pelo menos 1 dE a menos que a R89 (CIELAB dE76, DAC medido do MD);
- não aumentar o contraste entre colunas (faixas) além de max(o da R89, 3);
- não mudar a luminosidade além de max(o desvio da R89, 6) nem perder saturação (pelo menos 70% da cor do Doom, ou a da R89);
- nunca virar cinza claro, a menos que a cor do Doom seja cinza claro.

Garantia verificada nas 256 cores, sem peso: nenhuma cor fica pior que na R89, nem em erro nem em faixas.

## Resultado esperado (rodada 5; paredes e sprites inalterados)

| Modo | Erro chão/teto (média E1M1–E1M9) | Faixas chão/teto | Entradas alteradas (de 256) | Cinza claro R89 → R90 | Cores piores |
|---|---|---|---:|---|---:|
| Hybrid Blue | 20,4 → 14,2 | 2,6 → 0,0 | 60 | 0 → 0 | 0 |
| A2 | 19,8 → 12,9 | 7,7 → 6,3 | 56 | 26 → 27 | 0 |
| L3 | 18,5 → 13,1 | 6,8 → 5,3 | 62 | 32 → 31 | 0 |
| HN | 20,0 → 13,9 | 5,5 → 2,8 | 61 | 26 → 27 | 0 |

A única entrada que passou a cinza claro em A2 e em HN é de uma cor que já é cinza claro no Doom.

## Validação da ROM

- Nome da versão: `r90-flats` no `.bin`, no header e no título do benchmark.
- A/B quadro a quadro contra a R89, no mesmo job: as diferenças devem aparecer **só** em pixels de chão e teto. Diferença em parede, sprite ou HUD indica erro de injeção.
- BSS e desempenho não devem mudar: só bytes em ROM são trocados.
- A decisão final é do usuário, no CRT.

## Ressalvas

- A cor sólida de cada flat na análise foi estimada pela média da textura. O conversor do projeto (jWadUtil) pode ter escolhido um índice um pouco diferente. Isso afeta só a nota da métrica, não a validade das LUTs, que cobrem as 256 cores.
- A luz dos flats foi aproximada pela luz do setor, e os pesos de tela são estimativas.

## Descartado na análise (não repetir)

- Paletas por mapa: ganho de ~0,5 dE sobre uma paleta global validada fora da amostra, com mais faixas.
- Modelo de DAC real no gerador de paletas: ganho desprezível.
- Paleta global nova inteira: só melhora chão/teto e piora paredes e sprites do A2.
- Peso extra em áreas escuras: sem efeito mensurável.
