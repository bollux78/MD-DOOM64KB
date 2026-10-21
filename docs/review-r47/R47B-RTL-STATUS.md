# R47B-RTL — etapa 1: clock/reset YM7101 real

**Branch:** `r47b-rtl-ym7101-busbench`

**Base:** R47B-SIM aprovada.

## Evidências verificadas

- Workflow aprovado: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39536377706
- VCD e log: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39536377706/artifacts/12318055824
- Fontes Verilog reais do MiSTer fixadas no commit `becbdee78c48e6eb536871cd03c869f43d7afa4d`.
- Verificação de hashes: `ym7101.v` blob `0862948114ddb7abec87e46fdbb16d4fa2172804` e `ym_lib.v` blob `26fce976757bda2612e7ec0effcc93868660e108`.
- Compilação e simulação: Icarus Verilog em `ubuntu-24.04`, sem instalar pacotes no runner MarsDev do usuário.
- Relatório: **12.128 ciclos MCLK**, **607 bordas de subida no HCLK do VDP**, **2 ciclos com sinal `vdp_dma` alto** (incluindo período de inicialização).
- Primeiro teste falhou porque o pino de enable de clock `MCLK_e` estava conectado diretamente a `MCLK` e `SEL0` não reproduzia o valor M3 do `md_board.v`. Corrigidos e verificados pela fonte: `MCLK_e` alterna no flanco de `MCLK`, `SEL0=0`.

## Limites desta etapa

- Os dois ciclos com sinal DMA ativo podem ser transitórios de inicialização; a causa não foi verificada. **Não** equivalem a DMA de tilemaps e não permitem medir tempo de transferência.
- O testbench mantém barramento 68000 inativo e não carrega cartucho, ROM, VRAM de placa nem dados de quadro.
- Não há teste ainda de comandos VDP, FIFO, arbitragem Z80, VBlank completo ou 42 DMAs de 76 bytes. **A viabilidade de 3.192 bytes/42 comandos dentro do VBlank permanece indeterminada.**
- Um teste de clock bem-sucedido não mede custos reais de DMA.
- Arquivos `.vcd` podem ser abertos no GTKWave; `vdp_dma`, `vdp_hclk1`, `vdp_de_h`, `vdp_de_v` e sinais de barramento ficam visíveis.

## Próxima etapa concreta: transações de barramento

1. Verificar no RTL `fc1004.v` e `md_board.v` a ligação real de `CLK1_i`, `HL`, `DTACK_i`, `BG/BGACK` e portas VDP, evitando estímulos artificiais.
2. Construir modelo mínimo do bus master 68000 e fornecer palavras de controle VDP válidas, confirmando seus efeitos com sinais da implementação.
3. Acrescentar VRAM funcional e transações de DMA; medir início/fim em unidades MCLK e delimitar por VBlank detectado, sem inferir do modelo de bytes.
4. Repetir com 42 transferências de 38 palavras, observando longas lacunas por FIFO e tempos de arbitragem. Reportar bloqueios antes de concluir.
5. Só depois integrar simulação CPU/VDP e eventual ROM opt-in do plane-pair; manter XGM2 e baselines R5/R6A/R47A sem alteração.

**Áudio:** manter XGM2. Uma comparação com XGM e PCM compartilhado é opção de último recurso, e somente se a medição revelar interferência relevante.
