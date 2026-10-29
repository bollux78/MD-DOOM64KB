# R90 — Handoff do Cláudio para o Werk: novas LUTs de flats (chão/teto)

**Branch:** `exp-claudio-r90-palmap-analysis-20261029` (base R89 `542501f`)
**Tabelas para integrar:** [`R90-FLAT-LUTS-lf050.json`](R90-FLAT-LUTS-lf050.json)
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

## Como foi escolhido

Para cada cor e cada modo, mantendo a CRAM e os pares M50 da R89, escolhe-se o par (código da coluna par, código da coluna ímpar) que minimiza:

`dE(cor do Doom, média das duas colunas) + 0,5 × dE(coluna par, coluna ímpar)`

A métrica é CIELAB dE76 com o DAC medido do Mega Drive. Os níveis de luz vêm da COLORMAP. O segundo termo limita as faixas verticais.

## Resultado esperado (média E1M1–E1M9; paredes e sprites inalterados)

| Modo | Erro chão/teto | Faixas chão/teto | Erro geral |
|---|---|---|---|
| Hybrid Blue | 20,4 → 13,7 | 2,6 → 0,3 | 14,9 → 12,2 |
| A2 | 19,8 → 12,3 | 7,7 → 1,9 | 12,4 → 9,4 |
| L3 | 18,5 → 13,7 | 6,8 → 0,6 | 13,3 → 11,4 |
| HN | 20,0 → 13,7 | 5,5 → 0,6 | 14,0 → 11,4 |

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
