# S1b — prova de DIR/LUMP real no Sega CD (Werk, 2026-11-07)

**Status:** `build: PASS`; `blastem: PASS`. **Ainda NÃO é S1:** o ticker do Doom continua no MD após START, e o Sega CD faz apenas WAD I/O.

Build/teste: https://github.com/bollux78/MD-DOOM64KB/actions/runs/42376206144

ROM privada no runner:
`/home/dan/Projetos/Personal/scd-subport-s1b/run-42376206144-1/doom-md-scd-s1b.bin`

ELF de diagnóstico:
`/home/dan/Projetos/Personal/scd-subport-s1b/run-42376206144-1/doom-md-scd-s1b.elf`

**Resultados verificados pelo BlastEm no segundo 68000:**
- `stage: 5` (troca de WAD concluída)
- `served: 4` (DIR + três lumps de E1M1)
- `bytes: 26331`
- `errors: 0`; `timeouts: 0`
- `mdcrc: 0x998D122A`; `subcrc: 0x998D122A` (idênticos)
- `MD gameplay after START/timeout: True` (breakpoint em `G_Ticker`)
- ROM Mode 1, 3.932.160 bytes, programa sub de 11.474 bytes, BSS sub termina em 0x29CEC.

**Arquivos implementados:**
- `scd_proto.h`
- `scd_sub_transport.c`
- `scd_md_server.c`
- `scd_sub_w_wad.c`
- `s1b/s1b_md.c`
- `s1b/sub_main.c`
- `s1b/build.py`, `s1b/test_s1b.py`
- `.github/workflows/scd-subport-s1b.yml`

**Próximo S1 real:** implementar `scd_sub_system.c`, integrar objeto(s) do motor em PRG-RAM, executar `Z_Init`, `P_SetupLevel`, `G_Ticker` + demo E1M1 sem render no sub, e comparar os fingerprints com a R128. Preservar a tela de diagnóstico/START → jogo no MD para ROM de console. Não alegar lógica rodando no sub só com este marco. A S1a original e o checkout principal permanecem intactos.

**Segurança:** WAD, ROM e ELF ficam em `Personal`; não publicar binários privados. O teste S1b passa no BlastEm, mas console físico ainda não testado pelo usuário.
