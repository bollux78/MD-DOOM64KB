# R50 — Benchmark integrado à ROM PLAY e menu 3D econômico

**Branch:** `r50-play-benchmark-menu`  
**Base:** R49 Pair-V Fast / ColorMix + LUT  
**Estado:** experimental até validar o fluxo interativo em BlastEm e Mega Drive.

## Decisões para a evolução

- **Pair-V Fast** passa a ser o baseline 4×4 de desenvolvimento (5,31 FPS / 402,23 s em DEMO3 NTSC).
- **Pair-H** terá no máximo uma ROM de referência histórica; retirar variantes repetidas das próximas matrizes.
- Incluir **Benchmark** em todas as ROMs PLAY quando a nova implementação for promovida.
- Mais adiante incluir seleção 8×8 / 4×4 na mesma ROM, mas R50 ainda não implementa dual-mode.

## Funcionamento: Benchmark no PLAY

1. Abrir o menu principal em PLAY.
2. Escolher **Benchmark**.
3. O jogo encerra o menu e inicia `G_DeferedPlayDemo("demo3")`.
4. Define a mesma cadência `singletics=true` utilizada pela PERF.
5. Normaliza o mapa do DEMO3 para a mesma geometria de E1M1 da PERF.
6. `G_DoPlayDemo` ativa `I_BenchmarkReset()`.
7. `I_FinishUpdate()` contabiliza somente os frames apresentados quando `bench_active`.
8. Ao encontrar `DEMOMARKER`, apresenta o relatório habitual (FPS média/mínima/máxima, frames, segundos).
9. A tela aguarda um novo **Start**, solta o botão, limpa as flags de benchmark/demoplayback e retorna ao menu sobre a tela-título.

O resultado não usa relógio do host nem supõe ciclos de CPU: usa contagem de VBlanks (NTSC), tal como o benchmark PERF.

Diferenças pequenas entre PLAY benchmark e PERF ainda podem ser causadas por layout de código, movimentação de dados e polling extra de input. Não declarar FPS idênticos sem medição.

## Otimização do menu

`DOOM_R50_MENU_FREEZE` suspende somente o desenho 3D/automap/HUD quando `_g_menuactive` em jogo normal. `M_Drawer()` continua atualizando os caracteres e o joystick mantém responsividade. `G_Ticker()` e lógica do jogo permanecem como estavam: **não implica pause completo da simulação**.

Durante `_g_demoplayback`, o renderer continua ativo normalmente. Nenhuma das variantes PERF muda.

## Matriz inicial

| ROM | Benchmark no menu | Renderização 3D durante menu | Modo |
|---|---|---|---|
| vf-ctrl-play | Não | Original | PLAY |
| vf-bench-play | Sim | Original | PLAY |
| vf-freeze-play | Não | Suspensa | PLAY |
| vf-bf-play | Sim | Suspensa | PLAY |
| cm50l-bench-play | Sim | Suspensa | PLAY, ColorMix 50/50 + LUT |
| vf-ctrl-perf | Automático | N/A | PERF |
| cm50l-ctrl-perf | Automático | N/A | PERF |

## QA obrigatório antes de promover

1. Abrir **Benchmark** a partir da TITLEPIC e após entrar em E1M1.
2. Verificar DEMO3 com 2134 frames e tempos/FPS compatíveis com PERF.
3. Pressionar Start no resultado; confirmar retorno ao menu e capacidade de começar novo jogo.
4. Repetir Benchmark pela segunda vez sem reiniciar ROM.
5. Verificar música XGM2, SFX, Window overlay e tela estática após retorno.
6. Verificar MENU em uma cena leve e uma cena pesada, medindo responsividade.
7. Conferir WAD hash, BSS (limiar 57920 B) e PSRAM/heap na inicialização.
8. Testar no Mega Drive físico depois da validação no BlastEm.
9. Se menu congela a imagem preta, avaliar posteriormente retenção da última imagem 3D via plane-preservation sem custos por frame.
10. Guardar apenas uma ROM Pair-H como controle histórico, fora da matriz regular.

## Dual-mode 8×8 ↔ 4×4

Não é uma troca trivial de VDP: `i_genesisv.c` seleciona os dois backends usando `#if DOOM_R22_PIXEL4`; o viewport 8×8 compila em 38×22, enquanto o 4×4 usa 76×44; buffers, tilemap, VRAM e resolução da lógica também diferem. As variantes R46 M1/M1B já tinham co-link parcial da secundária 4×4, mas não havia dispatch runtime.

Próxima etapa: estudar um único buffer WRAM com ownership exclusivo e uma camada de dispatch de viewport/kernel, protocolo de VBlank/VDP, fallback seguro, pausa da renderização durante troca e item "RESOLUTION: 8X8/4X4" no menu. Validar primeiro cada resolução isolada na mesma ROM antes de permitir trocas com level ativo.

**Não afirmar que o dual-mode já existe.**
