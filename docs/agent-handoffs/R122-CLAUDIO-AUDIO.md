# R122: notas presas na música só no console (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`. O mesmo branch da R121, com variantes e workflows separados: áudio e desempenho não se misturam.
**Estado:** código pronto, **não executado**. O Werk dispara e o usuário testa no console.

## 1. Causa provável, com evidência nos mapas de símbolos das ROMs entregues
As ROMs têm a música (`bgm_episode`, o pacote XGM2 com todas as faixas, 219.136 B) **atravessando o endereço $200000**, logo antes do WAD (`doom_iwad`, `.rodata_binf`).

| ROM | `bgm_episode` | Bytes da música acima de $200000 |
|---|---|---|
| R100 f1 | 1CB500–200D00 | 3.328 |
| R104 mask | 1CBA00–201200 | 4.608 |
| R105 twoface / R107 direct / R109 | ~1CD400–202C00 | ~11.300 |
| R111 colsrc (descartada) | 1D0E00–206600 | 26.112 |
| **R113 hilut** | 1DA000–20F800 | **63.488** |
| **R115 dbuf** | 1DA200–20FA00 | **64.000** |

As PCMs dos efeitos ficam embaixo (0x84E00–0xEDA00 na R115), sem risco. Isso explica por que desligar os SFX não muda nada.

**Mecanismo:**
1. Toda leitura ou escrita do estado do mapa na SRAM abre uma janela (`R25_SRAM_BEGIN`, `$A130F1 = 1`), e a SRAM passa a ocupar o lugar da ROM a partir de $200000.
2. A R104 mascara as interrupções do 68000 nessa janela, mas **o Z80 continua rodando**.
3. Se o driver XGM2 busca bytes da música na ROM acima de $200000 justamente durante uma janela, ele **lê a SRAM no lugar da música**.
4. Um comando errado (por exemplo, um key-off perdido) deixa a nota tocando até o próximo evento daquele canal.

**Isso bate com tudo o que o usuário observou:**
- **Só no console:** o BlastEm não reproduz. Provavelmente não aplica a sobreposição às leituras do Z80, ou não intercala o Z80 dentro de janelas tão curtas.
- **Proporcional à carga de lógica:** com AI Normal há muito mais acessos à SRAM (visão, colisão, secnodes) do que com AI Low. AI Low reduz o problema mas não zera.
- **Depende da faixa:** só as faixas guardadas no final do pacote estão acima de $200000. Trocar ou recarregar o mapa pode mudar a faixa ou o momento.
- **Ficou bem mais frequente a partir de ~R113:** a parte exposta passou de ~4–11 KB para ~63 KB. O usuário percebeu "desde a R116".

O que ainda falta para ser prova: o teste no console com a ROM corrigida.

## 2. Correção (`apply_r122.py`, variante `layout`): só layout, sem código e sem RAM
- `r91_joint` (tabela da Shadow, 512 KiB, lida só pelo 68000 em `I_FinishUpdate`, nunca dentro de uma janela de SRAM) passa para `.rodata_binf`, depois da música, junto do WAD.
- A música desce 512 KiB e fica inteira abaixo de 2 MB (estimativa: termina por volta de 0x18FA00).
- O tamanho total da ROM não muda.
- Nenhuma leitura do 68000 acontece dentro das janelas (regra R104), então mover dados do 68000 para acima de 2 MB é seguro.
- **Guarda nova:** `scripts/lab/r122_z80_layout.py ELF --require` falha se qualquer byte de `bgm_*`, `pcm_*` ou `stop_xgm` estiver em $200000 ou acima. Recomendo usá-la em todo build daqui para frente, porque qualquer tabela nova que crescer pode empurrar a música de novo.

Não usei key-off periódico nem pedido de barramento do Z80 por janela. O key-off só esconderia o defeito. O pedido de barramento custaria desempenho e atrasaria o PCM a cada acesso à SRAM.

## 3. O workflow `r122-claudio-audio.yml`
- Builds: `control` = R119 both, `layout` = R119 both + `apply_r122`.
- Confere ROM ≤ 4 MiB, BSS ≤ 57.920 e `.data`/`.bss` iguais.
- Configuração do BlastEm fixa (divisor 7).
- **Guarda do Z80:** imprime a faixa da música nas duas variantes; a `layout` tem que dar 0 B acima de 2 MB.
- Lógica 10/10 idêntica.
- Pixels Off e On idênticos.
- Tempo nas demos pesadas com o A/B estrito: o esperado é ~0%.
- Smoke do PLAY.
- ROMs só na pasta privada `/home/dan/Projetos/Personal/r122-claudio-audio/run-…/`.

**Como disparar:**
```fish
git fetch origin; git checkout exp-claudio-r121-e1m7-20261103
date -u > .github/triggers/r122-claudio-audio.trigger
git add .github/triggers/r122-claudio-audio.trigger; and git commit -m "R122: trigger audio layout"; and git push
```

## 4. Teste no console (usuário)
1. Usar a ROM `doom-md-r60-r122-layout-pl.bin` da pasta privada.
2. Configuração: AI **Normal**, SFX ligados e as mesmas opções de sempre.
3. Jogar os mapas e trechos onde as notas presas apareciam com mais frequência.
4. Comparar com a R119 both no mesmo trecho e pelo mesmo tempo.
   - Se sumir com AI Normal, a causa está confirmada.
   - Se continuar, a próxima hipótese é concorrência de barramento do Z80 com outra coisa. Aí entram as ROMs isoladas que o Werk sugeriu: música pura; música + carga; jogo com AI e SFX ligados/desligados.
