# R135b — Werk: compilação PASS, BlastEm parcial/inconclusivo (2026-11-05)

Branch / fonte implementada por Cláudio: `45724a2`.
Build público de verificação: https://github.com/bollux78/MD-DOOM64KB/actions/runs/42024998207 — `success`.
Binário + ELF matching com R135b no runner privado:
`/home/dan/Projetos/Personal/r134-freedoom-maps/run-42025552684-1/`.

## Evidência efetiva

A execução `42025552684` compilou, verificou hashes da ROM de 5MiB e guardou o ELF; a fase BlastEm parou **antes** de iniciar por `M68K_NM` ausente no HOME isolado; **não foi erro do jogo**.

O workflow independente `.github/workflows/r135b-blastem-only.yml` foi criado. Sua primeira tentativa encontrou problema intermitente do JIT BlastEm (salto x86 fora de alcance / ASLR); foi modificada para repetir somente esse tipo de falha pré-RSP. Subsequentemente, o runner executou o ROM e ELF exatos.

Run de execução: https://github.com/bollux78/MD-DOOM64KB/actions/runs/42026909750
- `build: PASS`.
- `render: 500 frames` com `r70_capture.py`, tics 4–506, sem travamento do depurador.
- `r118_logic_check.py` (cópia de teste com limite ampliado a 45.000 frames, sem alterar benchmark canônico), seleções 1,2,3,4.
- Cada tentativa: `end=frame_limit`, **129 fingerprints** (~12.900 tics), nenhuma atingiu `I_Error` durante a janela observada.
- A checagem de conclusão exigia `demo_end`/`exit`; logo a etapa `Evaluate actual BlastEm results` terminou em `failure`.

**Interpretação correta**: `blastem: INCONCLUSIVE` quanto a demos completas, **não comprova defeito de ROM**. O termo `FAIL` no JSON publicado corresponde à condição estrita de encerramento não cumprida, e não ao disparo de `I_Error`.

## Próximas verificações

1. Investigar por que `R116_Done` / `R116_End` não são atingidos no probe, mesmo depois de 45k frames, e se a seleção de demo é armada cedo o suficiente. Os resultados iguais (129 checkpoints) merecem investigação.
2. Validar execução de PLAY com controles reais e troca de mapa (o teste renderizado é uma captura, **não** operação de menu por controle).
3. Comparar fingerprints com R128 All: 10 demos ainda **não** comparadas; ideal requer teste A/B da mesma demo e limites de execução equivalentes.
4. Testar compatibilidade SSF em cartucho *apenas* após validar PLAY, SRAM e estado de banco, sem risco aos saves.

Não publicar ROM, WAD, ELF ou dados de demos no repositório público. Resultados devem distinguir `build` e `blastem`.
