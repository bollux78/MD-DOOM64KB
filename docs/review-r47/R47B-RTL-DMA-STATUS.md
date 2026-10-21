# R47B-RTL — DMA de 38 palavras e lote de 42 transferências

## Evidência funcional observada (2026-10-21)

### Registrador VDP via barramento externo

- Workflow aprovado: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39593720522
- O testbench envia `0x8104` pelo barramento 68000, com `SEL0=1`, `CA_i=0x600002` (endereço byte `0xC00004`), `CD_i`, `AS/UDS/LDS/RW`.
- Observação: `reg_m5: 0 -> 1`, `reg_data_l2=0x00104`, 10 pulsos de escrita (o strobe longo desse primeiro teste é deliberadamente conservador e não reproduz handshake exato).
- O clock `CLK1_i` do 68000 é necessário para avançar a arbitragem; o teste DMA conecta a saída gerada `CLK1_o` à entrada `CLK1_i`. Sem essa ligação, o comando arma `t4`, mas `dff22_l2` e `dff2_l2` não avançam.

### Uma DMA de 38 palavras

- Workflow aprovado: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39594541858
- Programação: modo 5 + DMA (`0x8114`), incremento 2, comprimento 38 palavras, source 0, comando de VRAM DMA `0x40000080`.
- Sinais: `vdp_dma` ativo por **1.260 ciclos MCLK**; contador `reg_lg` passou de `0xFFD9` para `0xFFFF` (38 incrementos).
- `BG` é concedido após o comando. `w5` de concessão e `t3` de DMA ativo foram observados.
- Isto valida o comando e o contador de DMA no RTL, **não a integridade dos dados de VRAM**: o testbench ainda usa entrada de VRAM constante e uma palavra de cartucho determinística, sem memória realista.

### Lote de 42 DMAs de 38 palavras

- Workflow aprovado: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39594720240
- Artefato VCD/log: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39594720240/artifacts/12342813000
- Resultado: **42/42** sequências com contador final `0xFFFF`, **53.160 ciclos MCLK** com `vdp_dma` ativo, **154.023 ciclos MCLK** do lote programado e executado.
- Por lote: **3.647 a 3.736 ciclos MCLK**, incluindo comandos, intervalos deliberados e concessão de barramento.
- Volume nominal comandado: 42 × 38 palavras × 2 bytes = **3.192 bytes**.
- O tempo total NÃO é custo otimizado da ROM: `write_vdp` tem preparação e folga fixas de testbench; cada lote ainda reprograma registradores de comprimento e origem. Não há emulação da CPU 68000 completa, SGDK, Z80, XGM2, nem modelo fiel de VRAM.

## Limites e próximos gates

1. **VBlank real:** workflow `.github/workflows/r47b-rtl-vblank.yml` mede `vdp_de_v` no RTL NTSC em MCLK. Não concluir viabilidade apenas com valores teóricos.
2. **Custo real do comando:** implementar modelo de escrita 68000 com handshake/DTACK e minimizar pausas artificiais, distinguindo tempo ativo de DMA e overhead de CPU.
3. **VRAM:** acrescentar modelo da interface externa RAS/CAS/WE e validar conteúdo, endereços, e ausência de sobreposição com font/Window/HScroll/SAT.
4. **Áudio:** XGM2 permanece intocado. O teste atual não mede arbitragem Z80, PCM, nem áudio. XGM com PCM compartilhado somente último recurso com evidência.
5. **ROM:** não compilar nem propor aprovação de ROM plane-pair antes de gate de integridade e temporização; preservar baselines R5/R6A/R47A.

## Controle de risco

Todas as mudanças estão em `r47b-rtl-ym7101-busbench`. Não foi alterada ROM, renderer, dados de arte, mapeamento de VRAM do jogo, SRAM ou driver de áudio.
