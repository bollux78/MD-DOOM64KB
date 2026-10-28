# R80 — Resultado do Cláudio: diagnóstico, parecer P1–P7 e candidato P1+F1

**Data:** 27–28/10/2026
**Branch:** `exp-claudio-r80-perf-20261027` (derivado de `exp-chatgpt-r80-performance-20261027`, sem merge na base)
**Commit do candidato:** `1b1ce4d`
**Estado:** candidato **P1+F1** pronto para o benchmark completo do usuário. Nenhuma promoção feita.

---

## 1. Resumo

| Variante | Mudança | Framebuffer (326 tics) | Vblanks no trecho | Δ vs. controle | BSS PERF/PLAY | ROM |
|---|---|---|---:|---:|---|---:|
| Controle R79 | — | — | 3.872 | — | 57.896 / 57.910 | 2.883.584 |
| P1 | tabelas de offset Pair-V (parede + flat) | **idêntico** | 3.818 | **−1,39%** | igual | igual |
| F1 | laço `dbra` no preenchimento do flat | **idêntico** | 3.841 | **−0,80%** | igual | igual |
| **P1+F1** | as duas | **idêntico** | 3.746 | **−3,25%** | igual | igual |

- Os três terços do trecho melhoraram em todas as variantes. Nenhum regrediu.
- P1+F1 rendeu mais que a soma das partes (−3,25% contra −2,19%). Explicação provável, **hipótese**: o flat do P1+F1 ficou sem nenhuma multiplicação (139 instruções, contra 149), e o GCC alocou registradores melhor no corpo menor.
- **Isto é parcial:** cobre os tics 2–327 do DEMO3, uma execução BlastEm por ROM, até 8.000 quadros emulados. **Não é o benchmark completo**, e a promoção depende da medição do usuário.

---

## 2. Diagnóstico (P0)

### Ferramentas e dados usados

- ELFs de controle do artefato `12776668748` (run 40597005254), SHA-256 conferido contra `control-build/MANIFEST.json`.
- Disassembly local com capstone (M68000) sobre o ELF real.
- Controle recompilado no runner self-hosted: **byte-idêntico** ao manifesto R79 nos 3 runs (40611998731, 40612341437, 40614373322).
- Perfil por amostragem de PC (`r71_pcsample.py` + `r71_asm_report.py`), run 40611998731.
  - **HInt de novo não funcionou (0 amostras).** Caiu para VInt: 3.879 amostras, tics 1–316. A amostragem por VInt tem viés de fase, porque cada amostra cai no mesmo ponto do quadro.
  - Limite: 8.000 quadros emulados, uma execução.

### Perfil parcial da R79 (VInt, viesado; leitura qualitativa)

| Grupo | Participação |
|---|---:|
| BSP + subsetor (inclui seg loop inlined) | 26,4% |
| Cola C das colunas de parede | 18,0% |
| Flats | 14,4% |
| Outros | 10,9% |
| Setup de segmento / geometria | 9,3% |
| Sprites / masked | 6,0% |
| Kernel ASM de parede | 5,9% |
| Lógica do jogo | 4,5% |
| Streaming de mapa (SRAM) | 3,5% |

Blocos mais quentes:

| # | Bloco | Amostras | O que é |
|---|---|---:|---|
| 1 | `R_DrawColumnFlat @f144` | 4,36% | montagem do destino: `mulu.w #$4c` e `mulu.w #$98` → **alvo do P1** |
| 2 | `R60_WallColumn @1b4c` | 3,69% | laço do kernel ASM (já enxuto) |
| 3 | `__mulsi3` | 2,63% | chamado só pela **lógica do jogo** (`T_PlatRaise`, `P_BoxOnLineSide`…), não pelo renderer |
| 4 | `R42_DrawPackedWall @edc6` | 2,45% | montagem do destino da parede, os mesmos dois `mulu` → **alvo do P1** |
| 6–7 | `D_DoomLoop @fc24/@fc2e` | 3,30% | **espera ocupada** por `r22_ready` (o VBlank ainda não consumiu o quadro anterior) |
| 13, 17, 18 | `R_DrawColumnFlat @f1c8/@f1e6/@f1f0` | 3,53% | laço de pares do flat: limite e ponteiro final calculados com `mulu.w #$98` → **alvo do F1** |

### Respostas às perguntas do projeto

- **O kernel continua perto de 12%?** Não. Neste trecho ele dá 5,9%. O custo está na cola em volta dele (18%).
- **Que chamadas a libgcc restaram?** No renderer, `R_Subsector` ainda chama `__modsi3` (6×) e `__udivsi3` (5×), mas em caminhos frios: `(leveltime>>3)%3` e o módulo de largura de textura que só roda quando a largura não é potência de 2. O `__mulsi3` quente vem da lógica do jogo.
- **SRAM cresceu?** Não há sinal disso: 3,5%.
- **Há trabalho por quadro fora do render?** A espera por `r22_ready` (3,3% neste perfil viesado) é espera de apresentação, não trabalho repetido.

---

## 3. Parecer sobre P1–P7

| Item | Parecer | Evidência |
|---|---|---|
| **P1** offsets em ROM | **Apoiado, implementado e medido** (−1,39%). **Modificado:** a tabela de linha é indexada por **y** (44 entradas, 88 B), não por y>>1 (22). Isso elimina também o `lsr`. Total: 240 B de ROM. | Blocos #1 e #4. Depois do P1, a montagem do flat e a da parede (caminho R60) ficaram sem `mulu`. |
| **P2** caminho rápido de parede | **Adiado, não rejeitado.** O bloco de clipping e fração (`@ed68`, 2,09%) é o próximo alvo natural, mas o ganho exige provar as pré-condições do caller. Depois do P1 o GCC reorganizou `R42` (968 → 1.316 B), com os `mulu` restantes só nos laços de fallback com colormap, então convém re-perfilar antes. | Disassembly do controle e do candidato |
| **P3** BSP/registradores | **Adiado.** `R_Subsector` tem 26%, mas espalhado: o maior bloco tem 1,47%. Não há alvo único, e as chamadas a libgcc dali são frias. | Perfil por bloco |
| **P4** resolução de textura | **Possível, depois.** `R_DrawSegTextureColumn` tem 7,5%. O bloco de entrada (`@24e84`, 1,6%) é prólogo e stack. Não proponho transformação concreta sem novo perfil. | Perfil |
| **P5** SRAM | **Baixa prioridade** (3,5%). | Perfil |
| **P6** espera e DMA | **Rejeitado nesta rodada.** A espera por `r22_ready` é a correta, por ownership do buffer. Removê-la exigiria um segundo framebuffer (3.344 B de WRAM), e o PLAY tem 10 B de folga. | `D_DoomLoop @fc24–fc3c` |
| **P7** kernel ASM | **Baixa prioridade.** O laço de pares (`@1b4c`) já está enxuto: duas amostras por iteração com `dbra`. | Disassembly |
| `__mulsi3` restante | **Fora de escopo.** Vem da lógica do jogo; trocar a aritmética ali arrisca o determinismo do demo. | Chamadores no objdump |

### Alternativa que o projeto não considerou

O GCC transforma laços `while(count>=2){...; dst+=152; count-=2;}` em **comparação com ponteiro de fim, calculado com `mulu.w #$98`**, mais um `mulu` para o ponteiro depois do laço. Esse é o custo atacado pelo F1. O mesmo padrão aparece em **`R_DrawColumnSprite` (5× `mulu.w #$98`, 3,6% no perfil)**, que é o candidato natural do próximo experimento: P1 e F1 aplicados ao sprite, com os mesmos testes.

---

## 4. Implementação

Tudo fica no hook `scripts/lab/apply_r80_performance.py`, que roda só no candidato, depois da cadeia R79. Base e patches históricos não foram tocados.

Seleção por variável de ambiente: `R80_EXPERIMENTS="P1"`, `"F1"` ou `"P1+F1"` (padrão: `P1`).

- **P1:** `R80_PIXEL_BYTE(p,x,y) = p + r80_col_ofs[x] + r80_row_ofs[y]`, só em `R42_DrawPackedWall` e `R_DrawColumnFlat`. O sprite e os demais usos de `R22_PixelByte` ficam intactos. Se os macros Pair-V não estiverem ativos, o macro cai em `R22_PixelByte` (fallback = código original). Tem `_Static_assert` de 76×44.
- **F1:** o laço `V_FAST` de pares do flat vira `move.b / lea 152 / dbra`. Escreve os mesmos bytes nos mesmos endereços e deixa `dst` e a paridade de `count` iguais. Builds com `DOOM_R49_COLORMIX` mantêm o laço original.
- Cada experimento tem âncora única, confere em qual função está e recusa aplicação dupla.

### Memória

| | PERF | PLAY |
|---|---:|---:|
| BSS (controle = candidato) | 57.896 | 57.910 |
| Folga até 57.920 | 24 | 10 |
| ROM | 2.883.584 (igual: as tabelas couberam no preenchimento) | igual |

---

## 5. Testes de equivalência

1. **`scripts/lab/test_r80_pixofs.py`** (host; roda no preflight do workflow):
   - diff do hook: exatamente 2 linhas trocadas (parede e flat), o sprite intacto, aplicação dupla recusada;
   - C no host: o `R22_PixelByte` real (de `reference-prepared/src/r22_pixel4.h`) contra `R80_PIXEL_BYTE`, nas **3.344 coordenadas**, nos ramos Pair-V e fallback: **0 divergências**;
   - F1: âncoras nas duas ordens, escapes do asm conferidos, **parse do C gerado pelo GCC do host** e modelo do `dbra` contra o laço C para count de 0 a 44.
2. **Framebuffer real no BlastEm** (`r70_capture.py` + `r70_compare.py`): 326 tics comparados por tic, **326/326 quadros idênticos** em P1, F1 e P1+F1.
3. **Reprodutibilidade:** o controle compilado no runner é byte-idêntico ao manifesto R79, e o P1 repetiu exatamente 3.818 vblanks em dois runs diferentes.
4. **Smoke e limites:** BSS ≤ 57.920, ROM ≤ 4 MiB e ausência de `DOOM_R79_SHADOW`, verificados em todas as ROMs.

**Não testado aqui:** DEMO3 completo; menus (START rápido, telas nativas, H32/H40, troca de perfil); tintas de dano e bônus; hardware real. O P1 e o F1 só mexem nas funções de coluna de parede e flat, que essas telas também usam, mas isso **não** substitui a checagem.

---

## 6. Limites da medição

- Um único trecho: tics 2–327 (~15% do DEMO3), uma execução BlastEm por ROM, ≤ 8.000 quadros emulados. Não houve sessões encadeadas.
- A resolução é de um vblank por quadro. Os totais somam 326 quadros, e o próprio relatório trata diferenças abaixo de ~0,3% como ruído.
- O perfil é por VInt, com viés de fase. As porcentagens do perfil indicam onde olhar, não quanto se ganha.
- **Estimativa de ganho no DEMO3 completo: hipótese.** Se o trecho for representativo, algo entre −2% e −3,5% de tempo total, ou seja, de 7,32 para ~7,5 FPS. Só a medição do usuário vale.

---

## 7. Como reproduzir

```fish
git clone --branch exp-claudio-r80-perf-20261027 https://github.com/bollux78/MD-DOOM64KB.git
cd MD-DOOM64KB
python3 scripts/lab/test_r80_pixofs.py
# candidato para benchmark (checkout limpo e descartável):
env R80_EXPERIMENTS="P1+F1" python3 scripts/lab/prepare_r80_performance.py --variant candidate
python3 scripts/lab/build_r71a12mul_hud.py
```

No runner: alterar `.github/triggers/r80-claudio-ab.trigger` (workflow `r80-claudio-ab.yml`, matriz `control P1 F1 P1+F1`) ou `.github/triggers/r80-claudio-p0.trigger` (perfil). O workflow do projeto `r80-performance.yml` continua válido; o candidato dele usa o padrão do hook (`P1`).

### Runs

| Run | Conteúdo | Resultado |
|---|---|---|
| 40611998731 | P0: perfil do controle | sucesso; controle reprodutível |
| 40612341437 | A/B controle × P1 | sucesso; idêntico, −1,39% |
| 40612699119 | matriz (1ª tentativa) | **falhou:** escapes do asm do F1 (corrigido em `1b1ce4d`) |
| 40614373322 | matriz controle/P1/F1/P1+F1 | sucesso; tabela da seção 1 |

---

## 8. Próximos passos sugeridos

1. **Usuário:** benchmark completo do DEMO3 com o **P1+F1** (`doom-md-r60-r80-perf-pf.bin`, pasta `c-P1_F1` do artefato do run 40614373322), alternando com o controle, e checagem de menus, HUD, H32/H40 e tintas.
2. Se o ganho se confirmar: o mesmo P1/F1 em `R_DrawColumnSprite`, como experimento separado.
3. Depois: re-perfilar e avaliar o P2 (bloco de clipping e fração `@ed68` da parede).
