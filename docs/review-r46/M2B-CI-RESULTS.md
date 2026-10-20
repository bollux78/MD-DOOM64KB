# R46 M2B — validação automatizada e critérios de aprovação

**Build:** GitHub Actions [#39413007853](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39413007853) — **SUCCESS**.
**Artefato:** [#12259982916](https://github.com/bollux78/MD-DOOM64KB/actions/runs/39413007853/artifacts/12259982916).

Esta é **M2B etapa vertical/clipping**, não é um renderer 76×44 ativado em runtime.

## O que foi vinculado no mesmo ELF

- R39f 8×8 primário, mantendo dither Off/Checker/Vertical.
- M1A kernel R44 ASM 4×4 e rotinas de sprites/flats com framebuffer de 1672 B compartilhado com `_s_screen[38×28]`.
- M1B tilemap/empacotamento de VRAM do 4×4.
- M2A projeção horizontal com 77 ângulos de borda e 2032 entradas de ângulo→x em ROM.
- **Novo M2B:** `R46_P4_InitOpeningClips`, `R46_P4_ClipColumn`, `R46_P4_VerticalOps` e `R46_P4_VerticalValidate`, valores 76×44, centro 22; recorte de bordas 2 em gameplay, clipping da primeira linha para FPS; arrays de clipping de 76 colunas são **memória fornecida pelo chamador, não global estático**.

Teste host com mais de 640 mil combinações de clipping, bordas, alturas, sentinel guard e inicialização dos arrays. Equivalência ao caminho R44 para essas operações. **Não** prova ainda compatibilidade do pipeline de BSP/visplanes/sprites completos em resolução 4×4; isso é tarefa posterior.

## ROMs

| ROM | Conteúdo ativo | Objetivo |
|---|---|---|
| `doom-md-r46-primary-perf.bin` | 8×8 original | Controle DEMO3 |
| `doom-md-r46-m2b-perf.bin` | 8×8, módulos M1A/M1B/M2A/M2B co-linkados | Detectar regressões DEMO3 |
| `doom-md-r46-m2b-play.bin` | 8×8, módulos co-linkados | Validar jogabilidade/áudio/dithering |

Todas passaram pelo smoke de 300 quadros no BlastEm, verificação de símbolos de link, flags, cabeçalho e ROM linear de tamanho real dentro de 4 MiB.

## Memória no ELF

| Métrica | Controle | M2B |
|---|---:|---:|
| Text | 2.674.580 B | 2.677.652 B |
| Data | 452 B | 452 B |
| BSS | 57.724 B | **57.692 B** |
| ΔBSS | — | **−32 B** |

Não interpretar −32 como memória negativa do módulo; variação é resultado de link/otimização. Esta etapa não alocou novos buffers permanentes de clipping (304 B se ambos os arrays fossem reservados separadamente).

## Status / próximos gates

- ✅ CI, equivalência host para clipping e smoke 300 quadros.
- ⏳ **Usuário ainda precisa testar** os 2134 quadros de DEMO3 nas duas ROMs PERF (meta de **11,80 FPS / 180,82 s**) e gameplay/audio/menu na PLAY.
- ⏳ M2C: integrações completas de visplanes, BSP, projeção vertical de sprites/arma, alternativa para ownership e scratch de 76 colunas e renderer dispatch.
- ⏳ M3: VDP/VRAM/CRAM/HBlank/VBlank e DMA de troca de bancos seguro.
- ⏳ M4: toggle 8×8/4×4 sem reiniciar nível.

O plano de camadas não fixa céu no plano B. Alternativas céu no B, arma/HUD no B e arma por sprites são documentadas em `docs/review-r46/RENDER-LAYERS-ALTERNATIVES.md`. A paleta original do 4×4 segue como padrão até comparações futuras.
