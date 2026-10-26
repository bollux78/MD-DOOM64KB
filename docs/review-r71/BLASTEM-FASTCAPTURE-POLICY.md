# BlastEm — política de aceleração dos benchmarks (2026-10-26)

## Objetivo
Reduzir **tempo real no computador/runner**, jamais os ciclos medidos no Mega Drive emulado. Preservar clock original, NTSC 60 Hz, flags/ROM idênticas, framebuffer/tics/vblanks bit a bit. FPS da ROM = 60 / (vblanks emulados por frame). O ganho no tempo de execução do harness **não** significa ganho de FPS do jogo.

## Estado comprovado
- `scripts/lab/r64a_rsp_capture.py` já lança BlastEm como `blastem -b N -D rom.bin`, sem janela (headless/benchmark) e com depuração RSP. A execução não está deliberadamente travada em 100% de wall-clock.
- A captura lê 3344 bytes de framebuffer após cada breakpoint `I_FinishUpdate`; além dos símbolos tic e vblank.
- O `RSP_CHUNK` original era **192 bytes por transação**, o que exige **18 leituras de framebuffer** por render.
- O código-fonte do BlastEm upstream em `gdb_remote.c` declara `char send_buf[512]` e trunca as solicitações de memória `m` a `(sizeof(send_buf)-1)/2 = 255` bytes. **Não** escolher 512/1024/3344 no cliente sem modificar/recompilar o stub GDB do emulador. O `PacketSize` anunciado de 16 KiB é referente ao buffer de entrada, não ao de resposta `send_buf`.
- A opção experimental `BLASTEM_RSP_CHUNK=252` reduz para **14 transações por framebuffer** (22,2% menos transações), porém **o ganho de tempo real precisa ser medido**, pois a própria emulação e conversão hex também custam CPU.
- A rotina de captura possui override `BLASTEM_RSP_CHUNK`, padrão **192 enquanto o A/B estiver pendente**. Voltar a 192 restaura o comportamento original sem recompilar nada.

## Prova antes de promover
- GitHub Actions `blastem-rsp-throughput.yml` na branch `exp-chatgpt-blastem-fastcapture-20261026`, run inicial [40411537242](https://github.com/bollux78/MD-DOOM64KB/actions/runs/40411537242).
- Executar **A/B/A/B** com a mesma ROM R71-A12+MUL (SHA256 `9d8764b9cad175e9455e0113453a019bcb62a289f974f31033b8a645b273b085`), BlastEm instalado, 400 tics e clock stock. Mensurar segundos reais do host com `time.perf_counter()`, não FPS/VDP.
- **Obrigatório:** arquivos `frames.bin` (pixels) e `frames.jsonl` (tic, vblank, hashes) 100% idênticos entre as quatro capturas. Verificar que os 400 quadros foram gravados em todas as condições e que o `CAPTURE.json` é consistente. Não aprovar com resultado incompleto ou timeout.
- Promover default **252** apenas com validação completa e ganho de tempo real positivo; caso contrário manter default **192**. Ideal observar vantagem nas duas repetições e repetir se carga externa variar.
- Reavaliar para futuras branches de builds, mantendo A/B de controle. O usuário prefere aumentar o throughput do emulador sem comprometer fidelidade. **Não modificar** nem interferir no HUD do Cláudio ou na branch R66.
- Otimizações de comunicação são separadas de mudanças do próprio BlastEm e não justificam alterar `m68k_divider`, `max_cycles`, PAL/NTSC ou comportamento Z80/VDP. Não alterar o clock virtual para acelerar benchmark. `-b` já é adequado.
