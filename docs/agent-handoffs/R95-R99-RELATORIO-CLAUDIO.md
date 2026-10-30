# R95–R99: relatório de desempenho do Cláudio + proposta para o loop de colunas

**Para:** Werk (avaliação) e usuário. **Base de partida:** R92 toggle (SH1, A2/L3, Shadow On/Off, menu com pedra normal).
**Base recomendada agora:** **R98 sprmul** (cadeia R92 toggle → R95 → R96 → R97 → R98 sprmul).
Todas as mudanças mantêm o framebuffer idêntico (comparado tic a tic no BlastEm). BSS sempre ≤ 57.920; ROM 3.670.016 B.

## 1. Resultado no benchmark do usuário (DEMO3 E1M1 completo, AI Normal)

| ROM | Shadow Off FPS | Tempo | Shadow On FPS | Tempo | Status |
|---|---|---|---|---|---|
| r93c-candidate (= base R92 toggle) | 7,82 | 272,95 s | 7,06 | 302,18 s | referência |
| r95-flat | 7,86 | 271,35 s | 7,11 | 300,20 s | entrou |
| r96-wall | 7,98 | 267,45 s | 7,19 | 296,65 s | entrou |
| r97-shasm | 7,97 | 267,62 s | 7,43 | 287,13 s | entrou |
| **r98-sprmul** | **8,09** | **263,82 s** | **7,52** | **283,82 s** | **entrou: base atual** |
| r98-texcol | 7,98 | 267,47 s | 7,42 | 287,73 s | descartada (empate, +20 B BSS) |
| r98-segsplit | 7,92 | 269,43 s | 7,37 | 289,57 s | descartada (mais lenta) |
| r99-texsplit / angcache / recip | — | — | — | — | não medidas pelo usuário; A/B ruim ou neutro (§3) |

**Acumulado R92 toggle → R98 sprmul: −3,3% de tempo com Shadow Off, −6,1% com Shadow On.** O custo da Shadow caiu de 17,6 ms/frame (R91) para ~9,4 ms/frame.

## 2. O que foi feito, item por item

### Ferramenta: profiler por amostragem (R94/R99)
- `scripts/lab/r94_pcprofile.py`: breakpoint no vetor de VBlank (endereço lido de 0x78 na ROM). Em cada interrupção, o PC interrompido é lido do frame de exceção: **uma amostra por quadro emulado, uniforme em tempo emulado**, sem alterar a ROM. O BlastEm não aceita interrupção assíncrona (0x03), por isso a primeira tentativa não gerou amostras.
- Atribuição de chamador (R99): varre a pilha acima do frame e pega a primeira palavra que é endereço de retorno logo depois de um JSR/BSR no ELF.
- Limitação: máscara de interrupção (`ori #0x700`) atrasa a amostra; ~4.400 amostras por execução (limite de 10.000 quadros emulados, cobre ~480 tics do DEMO3).

### R95: flats rápidos no loop de colunas (`apply_r95.py`)
- No `R_RenderSegLoop`, o piso e o teto deixaram de chamar `R_DrawColumnFlat`. A cor do flat é fixa no seg, então as duas amostras (x par/ímpar) são buscadas uma vez por seg. O preenchimento é inline, e o recorte é redundante porque `solidcol`, `ceilingclip` e `floorclip` já garantem a janela.
- Grava os mesmos bytes que a função original: linha ímpar → nibble baixo; pares → os dois nibbles; linha par final → nibble alto. Céu e outros chamadores continuam como estavam.

### R96: paredes rápidas no loop de colunas (`apply_r96.py`)
- O prólogo do `R42_DrawPackedWall` (recorte, contexto R64A, colormap → LUT) custava tanto quanto o kernel R60. Agora as duas LUTs compostas (par/ímpar) são resolvidas por seg, e cada coluna faz só frac + endereço + `R60_WallColumn` (count ≥ 2) ou a escrita de nibble único. Se o colormap mudar (o céu muda), cai em `R_DrawColumnWall`. BSS +16 B.

### R97: passe da Shadow em assembly (`apply_r97.py`, `r97/r97_shadow.s`)
- O caminho p=0 do `R92_ShadowPass` foi escrito à mão: ~114 ciclos/bloco contra ~164 do C, com a mesma tabela, o mesmo retângulo e as mesmas palavras. p>0 continua no fallback C (R79). Protegido por `#if defined(__m68k__)`, porque os testes de host compilam o arquivo nativamente.
- Validado capturando o framebuffer **depois** do passe (`R92_AfterPass`) com Shadow On: idêntico ao da R96 em 416/416 tics.

### R98 sprmul (`apply_r98.py`, `R98_CANDIDATE=sprmul`)
- Em `R_DrawMaskedColumn`, `spryscale × topdelta/length` (32×8) chamava `__mulsi3` duas vezes por post. Agora são dois `MULU.W`, com resultado exato módulo 2³².

### Descartadas (não repetir)
| Item | Ideia | Resultado |
|---|---|---|
| R98 texcol | `DOOM_R20_WALL_HOIST`: patch por seg | empate no benchmark, +20 B de BSS; perde de novo, como na R20 |
| R98 segsplit | `R_RenderSegLoop` noinline (alocação de registradores separada) | +0,7–0,8% mais lento |
| R99 texsplit | caminho composto num helper noinline | +0,76% no A/B |
| R99 angcache | cache do ângulo do vértice compartilhado em `R_AddLine` | −0,14% (ruído), +8 B de BSS |
| R99 recip | recíproco exato sem o laço do libgcc | +0,39%: o `(N>>s)/d` em C virou chamada à libgcc de novo. A ideia (host-testada exata em 36,8 M casos) só vale com `divu.w` em asm inline; teto ~1% |

## 3. A/B do BlastEm (mesmo job, Shadow Off salvo indicação; parcial: ~420–480 primeiros tics)

| Variante | Δ vblanks | Base | Pixels |
|---|---|---|---|
| r95-flat | −2,15% | R92 toggle | idênticos |
| r96-wall | −3,45% | R92 toggle | idênticos |
| r97-shasm (Shadow On, framebuffer pós-passe) | −2,55% | R96 | idênticos |
| r98-sprmul | −1,22% | R97 | idênticos |
| r98-texcol / segsplit | +0,88% / +0,53% | R97 | idênticos |
| r99-texsplit / angcache / recip | +0,76% / −0,14% / +0,39% | R98 sprmul | idênticos |

**Lição de medição:** o A/B parcial (início de E1M1) dá a direção certa, mas o tamanho varia: flats −2,15% no A/B viraram −0,6% no benchmark; paredes, −2,0%; sprmul, −1,4%. Para ganhos abaixo de ~1%, só o benchmark completo decide.

## 4. Onde o tempo está agora (profile R99, R98 sprmul, Shadow Off, 4.379 amostras)

| Função | % | Conteúdo |
|---|---|---|
| `R_Subsector` (LTO inline) | 37,5% | loop de colunas + flats inline + setup de seg + parte da BSP |
| `R60_WallColumn` | 11,8% | kernel asm das paredes (pixels) |
| `R_DrawSegTextureColumn` | 10,8% | `R_GetColumn`, `W_GetLumpByNum`, R96 inline e MOVEM de ~9 registradores por coluna |
| `D_DoomLoop` | 8,2% | traversal da BSP inline + **~4% de espera ociosa pelo VBlank** (só um framebuffer) |
| sprites (`R_DrawVisSprite` + coluna) | ~7% | |
| `R_PointToAngle16` | 3,4% | metade de `R_AddLine`, metade da BSP |
| `R_ScaleFromGlobalAngle` + divisões | ~3% | |

## 5. Proposta para o Werk: o loop de colunas (`R_RenderSegLoop`)

### Diagnóstico
- O corpo do loop mantém o estado que muda a cada coluna (topfrac, bottomfrac, scale, pixhigh, pixlow e os passos) **na pilha**: `addl %d1,%fp@(-196)`, `subl %d2,%fp@(-200)`. São leitura-modificação-escrita em memória, de 20 a 28 ciclos cada, várias por coluna.
- O motivo é a pressão de registradores: dezenas de valores vivos, chamadas que não são inline e ramos para todos os tipos de seg (uma face/duas faces, top/bottom/mid, markceiling/markfloor, masked, céu, lazy texcol) no mesmo corpo.
- Separar o loop do `R_Subsector` (segsplit) **não ajudou**: o problema está no próprio corpo, não na fusão LTO.

### Proposta em fases (cada uma com A/B de framebuffer idêntico)

**F1: especialização em C por tipo de seg (risco baixo).** Gerar 2 a 3 variantes do loop com macros:
- (a) **uma face** (só `midtexture`, sem top/bottom, sem masked), o caso mais comum em paredes externas;
- (b) **duas faces sem masked**;
- (c) **genérico** (o atual), para o resto.

Cada variante tem menos valores vivos e menos ramos por coluna, e o compilador consegue manter mais estado em registrador. A escolha é feita uma vez em `R_StoreWallRange`. Validação: framebuffer idêntico; olhar no disassembly se os `fp@(-xxx)` do laço diminuíram. Expectativa honesta: 1–3%.

**F2: núcleo da variante (a) em assembly (risco médio).** Só depois da F1, e só para o caso uma face:
- registradores: `d`: topfrac, bottomfrac, scale (16.16), rw_x/contador; `a`: ponteiros de `ceilingclip`/`floorclip`, framebuffer, LUT do seg, fonte da textura; os passos ficam em memória como operandos `(d16,An)` (só leitura, 12–16 ciclos), nunca leitura-modificação-escrita;
- o kernel R60 é chamado direto com registradores (ABI que já existe), sem `R_DrawSegTextureColumn`, com o patch de uma textura simples resolvido por coluna via `columnofs` (para textura de patch único o endereço é `patch + columnofs[col & widthmask] + 3`, igual ao `R_GetColumn`);
- casos fora do padrão (textura composta, colormap diferente, céu) chamam a rotina C da coluna.

Expectativa: 3–6% adicionais, se o loop de uma face responder por boa parte das colunas. **Medir antes** com um contador por tipo de seg (build de diagnóstico, BSS temporário).

**F3 (opcional): reaproveitar a espera pelo VBlank (~4%).** Não há WRAM para um segundo framebuffer. A única saída sem memória seria adiantar trabalho que não toca o framebuffer (ticker, sons) para dentro da espera. O `G_Ticker` já roda antes dela, então o espaço é pequeno. Deixar como nota.

### Riscos e salvaguardas
- **Pilha:** o pico medido na R82 foi ~1.674 de 2.562 B no DEMO3 (estimativa de ~2.010 nos mapas de BSP mais funda). Variantes em C podem mudar o frame; medir com `r82_stack_probe.py`.
- **BSS:** margem atual de 44 B na PLAY. F1/F2 não precisam de BSS (estado em registradores ou locais).
- **Equivalência:** framebuffer idêntico em todos os tics do A/B (as ferramentas existem: `r70_capture`/`r70_compare`; para Shadow On, `r93b_capture` com o framebuffer pós-passe).
- **Medição:** benchmark completo do usuário, Shadow Off e On.

## 6. Branches, workflows e artefatos

| Item | Branch | Workflow | Run (artefato) |
|---|---|---|---|
| Profile R92 | `exp-claudio-r94-profile-20261030` | `r94-claudio-profile.yml` | 41001313827 |
| R95 flat | `exp-claudio-r95-flatfast-20261030` | `r95-claudio-ab.yml` | 41002332452 |
| R96 wall | `exp-claudio-r96-wallfast-20261030` | `r96-claudio-ab.yml` | 41003644544 |
| R97 shasm | `exp-claudio-r97-shadowasm-20261030` | `r97-claudio-ab.yml` | 41006184524 |
| R98 (3 candidatas) | `exp-claudio-r98-three-20261030` | `r98-claudio-ab.yml` | 41054560663 |
| Profile R98 | `exp-claudio-r99-profile-20261030` | `r99-claudio-profile.yml` | 41067077059 |
| R99 (3 candidatas) | `exp-claudio-r99-three-20261030` | `r99-claudio-ab.yml` | 41067904536 |

**Para reproduzir a base R98 sprmul:** cadeia da R92 (`apply_r81` … `apply_r92.py` com `R92_CANDIDATE=toggle`) → `R95_NAME=flat apply_r95.py` → `R96_NAME=wall apply_r96.py` → `R97_NAME=shasm apply_r97.py` → `R98_CANDIDATE=sprmul apply_r98.py` → `build_r71a12mul_hud.py`. A branch `exp-claudio-r99-three-20261030` contém todos os hooks.
