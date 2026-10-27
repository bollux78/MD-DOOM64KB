# Política de HUD — DOOM-MD (a partir da R71A12MUL)

A versão de referência para todo desenvolvimento novo inclui **HUD-WAD do Cláudio com stone margins no modo H40** (origem: HUD-WAD A12, Actions run 40421474937).

- Padrão obrigatório para novas ROMs de desempenho e jogáveis: `DOOM_HUD_WAD=1`.
- Não criar variante sem HUD, salvo solicitação expressa posterior do mantenedor.
- Não eliminar `DOOM_R70A_LOCALS=1`, `DOOM_R70A_INVARIANTS=1` nem `DOOM_R71_MUL_ASM=1` da referência R71A12MUL.
- Entregáveis principais: `r71a12mul-hud-perf` e `r71a12mul-hud-play`.
- Assets do HUD são gerados a partir do shareware WAD verificado no runner; não publicar WAD nem assets proprietários em commits.
- Compilação: `scripts/lab/build_r71a12mul_hud.py`, workflow `.github/workflows/r71a12mul-hud-build.yml`, gatilho restrito `.github/triggers/r71a12mul-hud-build.trigger`.
- Cada variante futura herda esta política; controles históricos permanecem disponíveis em runs anteriores, não nas novas compilações.
- Antes de aprovar uma revisão: validar checksum/manifesto, BSS <= 57920 bytes, ROM <= 4 MiB, inicialização, menu e HUD funcional em H32/H40, e medir DEMO3 em 60 Hz.

A integração no branch experimental não equivale, por si só, a ROM compilada ou validada em hardware.
