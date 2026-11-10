# Manifold E1M1 M11 — primeira ROM H32 com música (10/11/2026)

**Branch isolada:** `exp-manifold-m11-music`. Não alterar R128/Sega CD, branch principal ou release `manifold-e1m1-latest`.

## Resultado
- Action [#42872340400](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42872340400) **SUCCESS**; commit `7be9eef92a0b2dfec681ef08928e49da239d2dbd`.
- **ROM jogável:** `/home/dan/Projetos/Personal/manifold-e1m1/run-42872340400-1/m11music-h32.bin`. Tamanho 1.966.080 bytes, SHA256 `bd0fcdd8a61abfc45130e0ae6d84ab91f26b17661156421c356fe8df2762098c`, header SEGA.
- Controle sem música: `doom-md-manifold-e1m1-m02-hintfix.bin` na mesma pasta; 1.835.008 bytes, SHA256 `9d432ea4e41313424b47ec657c528b19bbd6d34b190b64bf6e744f0687f45737`.
- Música: a **E1M1 VGM já restaurada pelo gerador da R128** (`scripts/lab/prepare_r25_music.py`, fonte `assets/r25-music.json`; arranjo Spoony Bard, compositor Robert Prince, conforme metadados do repo). Na cópia *descartável* do Manifold gerada pelo stage, `music_res.res` usa `XGM bgm_e1m1 "manifold_e1m1.vgm"`; `init_game` chama `XGM_startPlay(bgm_e1m1)` após configurar PCM e inicializar o mapa. Tudo atrás de `MANIFOLD_MUSIC=1`.
- SGDK 2.x do runner `/home/dan/Projetos/marsdev/sgdk/SGDK/bin` tinha `xgmtool.exe` mas não `xgmtool` Linux. Workflow passa a criar symlink para o binário nativo preexistente `/home/dan/mars/m68k-elf/bin/xgmtool`, resolvendo a falha `Cannot run program .../bin/xgmtool`.
- Autowalk **da ROM com música habilitada**: `M11_MUSIC_AUTOWALK=PASS_3600_FRAMES` no BlastEm headless, com 90 quadros de boot e vetores de exceção fatais. MAME inicializa a variante musical e executa 900 quadros.
- **Ainda não comprovado:** som audível, melodia correta/loop, interação música/SFX no console e mudança de FPS em cenas pareadas; testes headless usam SDL_AUDIODRIVER=dummy. Não anunciar áudio aprovado no console sem escutar.
- AROM musical usa XGM (FM via Z80) e seu áudio é assíncrono ao render 68000; CPU e bus contention precisam de comparação prática, não de promessa.
- Esta variante musical foi derivada da H32 normal, **sem cache experimental de vértices ativado**. Próximo passo possível: música + `MANIFOLD_VERT_CACHE=1` em uma ROM separada, mantendo controle sem cache para saber qual mudança afeta FPS.

## Teste sugerido ao usuário
Abrir `m11music-h32.bin` no BlastEm com áudio ativo: confirmar que E1M1 toca durante o jogo, se há repetição, glitches/notas presas, e se disparos/menus interrompem ou abafam a faixa. Comparar FPS em escadas e área externa com a ROM sem música da mesma run. Testar depois no Mega Drive real; não substituir a release sem aprovação explícita.
