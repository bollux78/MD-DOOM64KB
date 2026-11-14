# HANDOFF Werk → Cláudio | M14 multimap ~12 MB | H-Int / DMA / arma | 14/11/2026

**Status:** proposta para análise, **não é patch aprovado**. **Base de trabalho correta:** ROM multimap atual (~12 MB, segundo o usuário), com menu, mapas, músicas corretas, objetos/inimigos, HUD e mapper. **Não substituir pela E1M4 isolada** do Werk.

## Achado principal

O usuário relata que as ROMs diagnósticas **F e G** não exibiram as faixas pretas, mas ambas são **builds isoladas de E1M4**, sem o conteúdo atualizado da multimap. A–E apresentaram problemas. A–E e F/G usam a mesma base de E1M4; **B** tem `MANIFOLD_NO_TEXT=1`; **F** acrescenta `MANIFOLD_WEAPON_FIX=1` e `MANIFOLD_INPUT_FIX=1`; **G** é F mais `MANIFOLD_NO_GUNBOB=1`. Assim, **F vs B é o contraste relevante**, mas mistura WEAPON_FIX e INPUT_FIX. F vs G indica que o bob não parece ser condição para eliminar as barras; **não prova causalidade**.

As capturas de A–E no BlastEm mostram A/B com cena e HUD, C com HUD incompleto, D com corrupção maciça em colunas e E com janela de imagem reduzida e grandes bordas pretas. Não promover D/E. Capturas estáticas não medem piscadas; relato do usuário é teste visual, não instrumentação.

**Limitação das ROMs Werk:** `experiments/DOOM_Manifold_E1M1/tools/m14/hint_five_roms.py` fixa E1M4 mas usa `res/r25-e1m1.vgm`; não ativa `MANIFOLD_MONSTERS`. Música incorreta e ausência de inimigos não são evidência de regressão de H-Int: são diferenças de configuração.

## Medições e testes já comunicados pelo Cláudio

- MAME, E1M7 girando no spawn: H-Int fase 0 esperado na linha 32, atraso em ~1,6% dos quadros (linhas 33–66); fase 2 esperada em 215, às vezes cedo (185–212).
- DMA SGDK no flip: ~15 KB/quadro com console, ~1,9 KB sem console, zero sem console e sem arma.
- Sem console ainda há atrasos; console a cada 8 quadros zerou atrasos em 500 quadros **no MAME**, mas r022 não resolveu no hardware.
- r018 (rearme VInt), r019 (display sempre ligado: lixo/FPS ~8), r020/r021 (margens 8/16), r022/r023 (texto reduzido/congelado) não resolveram. r024 sem texto melhorou parcialmente.

## Inspeção do código: pontos promissores

1. **`m14_weapon_fix(out)` em `stage_rom.py`:** substitui dois testes `DMA_getQueueSize() == pre_queue_size` por `m14_wpn_ready()`, coloca sprites idle no início, parcela uploads em até 32 tiles (~1 KB) por quadro, mantém idle/fire na VRAM e ajusta animação. Quando `MANIFOLD_PCM_DELAY=1` também chama `XGM_setForceDelayDMA(TRUE)`. **Patch composto, não isola DMA vs PCM vs animação**.
2. **`m14_input_fix(out)`:** desativa em `src/draw.c` um ramo de debug de BUTTON_C dentro do `flip()` que limpa/copia buffers e chama `waitMs(125)`; também muda disparo A/C, SFX IDs, recoil e áudio do tiro. Inspecionar o ramo de debug prioritariamente; não atribuir piscadas ao C se ocorrerem sem C.
3. **`m14_hint_rearm`, `m14_hint_margin`, `keep_display_enabled_in_hblank`:** já foram experimentados sem correção confiável em hardware. Não insistir em margens ou display sempre ligado sem explicar o timing.
4. **`MANIFOLD_HINT_PROBE=1`:** instrumenta RAM com VCounter por fase H-Int e tamanhos da fila DMA. Ampliar se possível para ring buffer de eventos sem console/printf no caminho crítico.

## Proposta: testar na **mesma ROM multimap ~12 MB**

**Primeiro:** identificar o commit/gerador exato da ROM de 12 MB e verificar quais patches já estão integrados. A branch `exp-manifold-m14-e1m1` tem `stage_rom.py`, mas **não foi comprovado que o HEAD dessa branch corresponde à ROM multimap atual**. Não alterar linker, mapper SSF2, mapa, trilhas, menu ou conteúdo.

| Variante | Diferença controlada | Hipótese |
|---|---|---|
| M0 | Multimap atual intacta | Baseline |
| M1 | Só remover FPS/console do gameplay; preservar HUD | Isolar custo do texto |
| M2 | M1 + apenas gestão de tiles/sprites da arma; separar PCM se viável | Isolar `WEAPON_FIX` |
| M3 | M2 + apenas desativar ramo debug BUTTON_C em `flip()` | Isolar caminho input/flip |
| M4 (opcional) | M3 + mudanças PCM/XGM e recoil do patch completo | Isolar áudio/PCM |

Se a multimap já tiver partes desses patches, **fazer diff do C gerado e testar ablações seletivas**, em vez de reaplicar. Os experimentos devem manter arma visível e animada. Compilar somente em branch isolada; sem merge automático.

**Validação:** girar ≥2 min no spawn E1M7 em hardware real; contar faixas e medir H-Int fase 0/2; registrar DMA bytes/descritores por quadro e duração do flip/VInt; testar E1M4, menu/troca de fase, todas as músicas, inimigos, HUD, A/C, bob e tiro. Diferenciar taxa ~60 fps do emulador de FPS do render. MAME é complemento, não substitui Mega Drive real.

**Se persistir:** examinar em conjunto `src/my_bmp.c` (`bmp_do_hblank_process_vertical`, `do_vint_flip`, `request_flip`), `src/draw.c` (`flip`), fila SGDK DMA e Z80/XGM. Hipótese: contenção/ordem de interrupções e transferência VDP, ainda **não comprovada**. Investigar orçamento fixo de DMA no VBlank, prioridade do framebuffer e adiamento de atualizações secundárias, sem desligar display durante a região ativa.

## Fontes e histórico

- [A–E: GitHub Actions](https://github.com/bollux78/MD-DOOM64KB/actions/runs/43649111733) — branch `exp-manifold-m14-hint-five-roms`.
- [F/G: GitHub Actions](https://github.com/bollux78/MD-DOOM64KB/actions/runs/43649657354) — branch `exp-manifold-m14-weapon-bob-diag`.
- [Código M14](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-m14-e1m1/experiments/DOOM_Manifold_E1M1/m01/stage_rom.py) — branch consultada no commit `bdf7e9d182`.
- Upstream Manifold: `ehaliewicz/Manifold` commit `b6fe52a52344464de00bde4dc58a40f8b89cfc1a`.
- Handoff histórico `MANIFOLD-M14-MULTIMAP-4MB.md` descreve **versões anteriores** de 5 mapas (10,5 MB/7 MB) e SSF2; **não presume** layout da atual ~12 MB.
- Capturas A–E anexadas pelo usuário no chat de 14/11; pacote ZIP preparado separadamente para repasse.

## Pedido ao Cláudio

1. Identificar a ROM/commit multimap atual e as flags/patches já ativos.
2. Comparar C gerado de B vs F e F vs G; identificar mudanças efetivas, não apenas flags.
3. Propor patch mínimo testável na multimap sem perda de conteúdo.
4. Validar no MAME **e no hardware**; informar hipótese, resultados, riscos e rollback.

**Nenhum patch aprovado para merge.**