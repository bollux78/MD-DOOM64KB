# Manifold E1M1 M02 — primeira ROM jogável (Claude)

**Branch:** `exp-manifold-e1m1-m01` · **Run validada:** [#42752744139](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42752744139)
**ROM (só no runner, deriva do WAD privado):**
`/home/dan/Projetos/Personal/manifold-e1m1/run-42752744139-1/doom-md-manifold-e1m1-m02-hintfix.bin`
(SHA-256 `f85cc4652535e91d0b6c163f4e7ce29b6e340f9e30a7efe057940ea2c3ac5c15`)

## Status verificado
- MAME (`genesis`, NTSC, headless): 900 quadros sem exceção; com controle injetado o jogador
  anda ~580 unidades para o norte (setores 103→105→109), gira à direita e à esquerda.
- BlastEm 1.0 headless: 90, 600 e 1200 quadros sem parada (E1M1, controle e ROM oficial).
- E1M1: geometria reconhecível (sala inicial, plataforma/degraus, corredores), cores
  provisórias, 6–12 fps na sala inicial.
- ROM de controle (mapa de teste do próprio Manifold): imagem igual à do `built_rom.bin`
  oficial, ~20 fps.
- **Não testado** em console real.

## Causas encontradas e corrigidas (todas em `stage_rom.py` / `emit_portal_map.py`)
1. **ADDRESS ERROR original**: no SGDK 2.x o vetor de H-Int é `JMP callback` direto; o handler
   de bitmap era C comum (RTS, d0/d1/a0/a1 destruídos). Agora `HINTERRUPT_CALLBACK` (RTE).
2. `normalize_math_and_menu` fazia `((s16*)out) + num_walls*2`: metade do deslocamento,
   escrita abaixo do buffer → nada era desenhado. Agora `(s16*)(out + num_walls*2)`.
3. Células E1M1 precisam ser **horárias** (os mapas do Manifold usam `VERT(x,-y)`); anti-horárias
   são descartadas como face traseira. Medido com contadores: CCW = 1 setor/quadro, CW = ~21.
4. `asm` inline da era GCC 6: entradas escritas viraram saídas `+`, clobbers `cc`/`memory`;
   jump-tables de textura restauradas com contrato explícito de registradores (o fallback C
   foi removido: 6,8 → 20,7 fps no controle).
5. `wall_tex_repetitions` NULL nos mapas de teste lia a tabela de vetores (0 no boot SGDK2) →
   todas as colunas com u=0. Padrão 1.
6. Joypad: SGDK 2.x só chama `JOY_update()` em `SYS_doVBlankProcess()`; agora em `update_joy()`.
7. Profundidade 12.4 dava a volta em `s16` (E1M1 > 2048 unidades) → ponteiro de coluna ímpar
   ao girar. Saturação + validação da janela em `visit_graph`.
8. Tiles do jogo começavam em `0x390` (layout SGDK 1.x); realocados para depois do framebuffer
   SGDK 2.x (`TILE_USER_INDEX + 896`), com limite antes do HScroll (`0x540`).
9. BlastEm "travado": não era crash — ele abre um terminal para mensagens KDebug
   (`KLog_S*`, `MEM_dump`) e bloqueia sem terminal. Todas silenciadas.
10. E1M1: alturas ×2 (proporção Doom no FOV do Manifold; aberturas ≤60 contam como porta
    fechada e degraus ≥40 bloqueiam), olho a 82, luz limitada a −2..2, cores de piso/teto no
    campo empacotado do parâmetro 0.

## Pendências
- Arma do HUD não aparece (sprite); artefatos de recorte em alguns cantos do teto.
- 112 arestas BSP sem par continuam sólidas; sem THINGS, portas/gatilhos, texturas do WAD.
- PVS provisório "tudo visível" (custo alto).

## Ferramentas de diagnóstico no workflow
MAME + Lua: snapshots, trace de PC, contadores `manifold_dbg`, dump dos buffers de bitmap,
injeção de controle. `MANIFOLD_SKIP` / `MANIFOLD_EXTRA` ligam/desligam passos do stage.
