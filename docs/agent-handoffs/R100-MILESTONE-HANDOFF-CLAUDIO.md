# R100 F1: milestone (handoff do Cláudio para o Werk)

**Status:** milestone aprovado pelo usuário (2026-10-30). **Nova base de trabalho.**

## 1. Identificação

| Item | Valor |
|---|---|
| ROM de entrega | `doom-md-r60-r100-f1-pl.bin` |
| sha256 PLAY | `679fc8354e550262bce309f8905bbc5dd6fb65b3de4bbb1fe492cca84c863989` |
| sha256 PERF (A/B) | `d365a15fb4afc8a7d7b43fecf31e7db070059b930947a4e84ee6630c67804619` |
| Tamanho ROM | 3.670.016 B (≤ 4 MiB) |
| BSS | PLAY 57.876 (folga 44), PERF 57.872 (folga 48) |
| Pilha (DEMO3, até o tic 400) | pico 1.632 de 2.562 B, igual à R98 sprmul |
| Branch | `exp-claudio-r100-f1-20261030`, commit `355f06d` |
| Base pinada (hooks R95–R98) | `exp-claudio-r99-three-20261030`, commit `bac4df1` |
| Artefato (ROMs + manifesto) | https://github.com/bollux78/MD-DOOM64KB/actions/runs/41081061207 (`R100-MANIFEST.json`) |
| Controle reproduzido | `r98-sprmul-pl` sha256 `69e56d83…`, idêntico ao build anterior |

## 2. Cadeia (cópia descartável do checkout)

```
apply_r81 → test_r80_pixofs → R80 P1+F1 → R83 sprites → R85 all → R88 ai → apply_r89
→ R90 control → R91 sh1 → R92 toggle
→ R95_NAME=flat apply_r95 → R96_NAME=wall apply_r96 → R97_NAME=shasm apply_r97
→ R98_CANDIDATE=sprmul apply_r98 → apply_r100 (R100_MODE=f1)
→ build_r71a12mul_hud.py
```

Workflow de referência: `.github/workflows/r100-claudio-f1.yml`. O `apply_r100.py` também ajusta a contagem esperada no `test_r15_wallmul.py`, que verifica o texto do código, porque o loop passa a ter 2 cópias.

Preservado da base: Shadow recortado com toggle (Off por padrão), SH1 com as tabelas originais aprovadas, modos A2/L3, menu com pedra original sem S/H, AI Normal por padrão. **Nenhuma alteração de CRAM (R93/R93c não integradas).**

## 3. O que cada passo faz

| Passo | Mudança | Validação |
|---|---|---|
| R95 flat | Piso e teto preenchidos inline no loop de colunas; amostras da cor por seg | framebuffer idêntico |
| R96 wall | Parede direto ao kernel R60 com as LUTs resolvidas por seg (sem o prólogo do R42) | idêntico |
| R97 shasm | Passe da Shadow p=0 em asm (~114 contra ~164 ciclos/bloco) | idêntico pós-passe (Shadow On) |
| R98 sprmul | Sprites: 32×8 com dois `MULU.W` em vez de `__mulsi3` | idêntico |
| **R100 F1** | Loop de colunas gerado em 2 cópias a partir do **mesmo texto**: caminho `midtexture` (teste do tier = 1) e o loop original para o resto. Escolha feita uma vez antes do loop | idêntico (Off; On A2/L3 pós-passe) |

## 4. Resultados

### Benchmark completo do usuário (2.134 frames, AI Normal)

| ROM | E1M1 Off | E1M1 On | E1M7 On |
|---|---|---|---|
| Referência R92 toggle | 7,82 FPS / 272,95 s | 7,06 / 302,18 s | — |
| R95 flat | 7,86 / 271,35 | 7,11 / 300,20 | — |
| R96 wall | 7,98 / 267,45 | 7,19 / 296,65 | — |
| R97 shasm | 7,97 / 267,62 | 7,43 / 287,13 | — |
| R98 sprmul | 8,09 / 263,75 | 7,53 / 283,27 | — |
| **R100 F1** | **8,38–8,39 / 254,47–254,60** | **7,78–7,79 / 274,07–274,17** | **5,19 / 410,98** |
| R101 F1b (descartada) | 8,39 / 254,48 | 7,78 / 274,17 | 5,19 / 411,07 |

- **Acumulado R92 toggle → R100 F1 (E1M1):** −6,7% de tempo com Shadow Off e −9,3% com Shadow On.
- **R100 contra R98 sprmul:** −3,5% (Off) e −3,2% (On).
- **Repetibilidade:** a mesma ROM R100 em duas rodadas do benchmark variou 0,13 s (254,47 contra 254,60), então diferenças de ~0,1 s são ruído.
- **Custo da Shadow:** 13,7 ms/frame na R92 toggle → 9,4 ms/frame na R100 F1. O valor de 17,6 ms era o da R91, com passe full.

### A/B de triagem no BlastEm (R100 contra R98 sprmul, mesmo job; cobertura parcial)

| Teste | Tics | Δ vblanks | Pixels |
|---|---|---|---|
| Shadow Off | 2–484 | −3,27% | 483/483 idênticos |
| Shadow On A2, pós-passe | 2–446 | −3,47% | 445/445 idênticos |
| Shadow On L3, pós-passe | 2–446 | −3,47% | 445/445 idênticos |

A cobertura de pixels no BlastEm é só o primeiro terço de E1M1. E1M7 e as outras salas foram validadas visualmente pelo usuário no benchmark.

### Diagnóstico (build separado, nunca entregue; tics 1–506 do DEMO3)
- 76.176 colunas: **43,8% no caminho `midtexture`** (todas desenham parede).
- Com a F1b: 56,4% das colunas são de duas faces sem masked; colunas com masked foram praticamente zero nesse trecho.
- Kernel R60: 53.359 chamadas; 5.618 colunas de um único pixel; **0 fallbacks** para `R_DrawColumnWall`.

### Disassembly (`R_Subsector`, onde o loop está embutido por LTO)

| | R98 sprmul | R100 F1 | R101 F1b |
|---|---|---|---|
| Frame (`link`) | 292 B | 272 B | 268 B |
| Leitura-modificação-escrita na pilha | 24 | 18 | 35 |
| Tamanho | 11.254 B | 11.368 B | 13.276 B |

## 5. Testado e descartado (não repetir sem ideia nova)

| Item | Resultado |
|---|---|
| R98 texcol (`DOOM_R20_WALL_HOIST`) | empate, +20 B de BSS |
| R98 segsplit (`R_RenderSegLoop` noinline) | +0,7% mais lenta |
| R99 texsplit (composite em helper noinline) | +0,8% no A/B |
| R99 angcache (vértice compartilhado em `R_AddLine`) | ruído, +8 B de BSS |
| R99 recip (recíproco sem o laço do libgcc) | +0,4%: a divisão em C virou libgcc de novo; só faz sentido com `divu.w` em asm, teto ~1% |
| **R101 F1b** (cópia de duas faces sem masked) | empate em E1M1 Off/On e E1M7 On; +1,9 KB de código, mais derramamento de registradores |
| R90 split, R93/R93c (cor) | rejeitados pelo usuário |

## 6. Próximos passos possíveis (para avaliação)

1. **Caminho de duas faces (56% das colunas):** a F1b mostrou que tirar só o masked não basta. O corpo ainda carrega top + bottom + `pixhigh`/`pixlow` + `solidcol`. Uma especialização mais funda (só top / só bottom / ambos, com e sem flats) precisa de um contador antes para ver quais combinações dominam. Risco de crescimento de código.
2. **F2 em assembly (só `midtexture`):** continua especulativa. Exige antes o mapa de registradores, porque o R60 destrói `d0`–`d7` e `a0`, e uma decisão entre salvar o estado, mudar a ABI ou embutir o kernel.
3. **Recíproco com `divu.w` em asm inline:** teto ~1%.
4. **Espera pelo VBlank (~4% no profile):** medir a duração diretamente antes de qualquer mudança; não mexer em ticker/som.

Medição: sempre o benchmark completo do usuário (E1M1 Off/On, E1M7). O A/B do BlastEm serve só para triagem e prova de equivalência na cobertura informada.
