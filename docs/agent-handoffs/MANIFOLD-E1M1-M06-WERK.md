# Handoff para o Werk — Manifold E1M1 M06

Branch: `exp-manifold-e1m1-m01` · commit `0cf6b10` · run de referência 42815383908 (verde).
ROM estável: https://github.com/bollux78/MD-DOOM64KB/releases/download/manifold-e1m1-latest/doom-md-manifold-e1m1-m02-hintfix.bin

Status: testado em MAME e em BlastEm headless (autowalk 3600 quadros). **Console real NÃO testado.**

## Como rodar
- O workflow `.github/workflows/manifold-e1m1-rom.yml` dispara em push com `[manifold-rom]` na mensagem do commit, ou via `workflow_dispatch` na branch.
- Usa o WAD shareware fixado no runner (`/home/dan/Projetos/doom-md/assets/wads/doom1.wad`, sha256 `1d7d43be…c771`). Nada além disso é necessário.
- Em caso de sucesso, publica a ROM principal na release `manifold-e1m1-latest`, que tem URL fixa.
- Artefato `manifold-e1m1-roms-<run>` (7 dias):
  - ROMs principal, autowalk e tour;
  - ELF e symbol.txt;
  - `sgdk-kit.tgz` e `m68k-elf-kit.tgz`, para compilar fora do runner.
- Também há um artefato de screenshots.

### ROMs geradas
| ROM | Para quê |
|---|---|
| `doom-md-manifold-e1m1-m02-hintfix.bin` | jogável (START pausa; direcional anda e gira; A atira) |
| `…-autowalk-m02.bin` | anda sozinha; os vetores de exceção apontam para I/O, então qualquer crash vira erro fatal no BlastEm |
| `…-tour-m03.bin` | teleporta para o centro de cada setor girando a câmera (`MANIFOLD_TOUR_SKY=1` limita aos setores com céu) |

### Testes que precisam passar
1. Passo "BlastEm autowalk stress": `AUTOWALK_VERDICT=PASS_3600_FRAMES_WALKING`.
2. Smokes do BlastEm de 90 e 1200 quadros.
3. Visual (indicador do usuário): abrir a ROM principal no BlastEm gráfico. START entra no jogo; andar até a área externa com ácido e até as escadas.

### Build local (fora do runner)
- `experiments/DOOM_Manifold_E1M1/tools/lbuild.sh` (caminhos locais do Claude; ajustar): extrai os dois kits do artefato e usa `makefile.gen` com `-fno-lto`.
- No link, acrescentar `-Wl,--build-id=none -Wl,-z,noexecstack`.
- Copiar `src/boot` do SGDK para dentro do kit.
- O gcc `m68k-linux-gnu` **não** serve: ele usa outra ABI, devolve ponteiros em a0, e a ROM dá ADDRESS ERROR.

## O que mudou desde M02 (tudo em `experiments/DOOM_Manifold_E1M1/m01/`)
- `true_cells.py`: as células são a folha da BSP cortada pela região real do setor, depois fundidas, soldadas e pareadas. Zero bordas sem par. Requer shapely, que o workflow instala com pip.
- `wad_textures.py`:
  - 29 texturas do Doom convertidas para 32×64;
  - paleta de 16 cores do Mega Drive, escolhida por seleção gulosa (greedy);
  - tabelas de luz recalculadas para essa paleta;
  - faixa SKY1.
- `stage_rom.py`, passos novos:
  - `robust_sector_crossing`: quinas de células e validação final da posição; o jogador nunca fica fora da célula;
  - `far_portal_fog`: portais a mais de 1600 unidades viram parede escura;
  - `scale_light_distances`: faixas de luz para a escala do E1M1; a faixa FADE escrevia cor 0, que é transparente;
  - `textured_portal_steps`: bytes high/low com o bit 0x80 ligado indicam índice de textura;
  - `keep_overlays_off_sky`: console e fps fora das linhas do céu;
  - `fix_fps_font_base`;
  - `weapon_buffers_fit_vram`;
  - `install_sky`.

## Mapa de VRAM (ver o README do experimento)
- Framebuffer: 896 tiles. HUD, arma (buffer 0) e console até 0x4FF.
- Fonte do SGDK: 0x4E0–0x53F.
- O nametable do WINDOW (0xB000, 128 tiles) guarda o **buffer 1 da arma**. O endereço do window é apontado para o BG_B.
- As linhas 30–63 do BG_B (0xCF00–0xDFFF, 136 tiles) guardam o **céu**: 131 tiles, 128 px de largura, repetido a cada 45°.
- O inventário escreve até a linha 28 do BG_B. Não usar as linhas 28 e 29.
- Linhas da tela fora da área 3D ficam apagadas pelo extended blank. Texto só aparece nas colunas 0–3 das linhas da área 3D ou no HUD.

## Problemas conhecidos / próximos passos
1. **Repetição vertical da textura**: hoje ela é esticada, porque os escalonadores `scale_64_N` sempre espalham 64 texels pela altura toda. Plano: emitir as repetições verticais e chamar o escalonador uma vez por segmento, usando `bot_clip` no último. Medir o fps no tour antes e depois.
2. A arma não aparece na tela, mas apertar A não trava mais. Investigar `update_weapon_sprites` e a prioridade dos sprites.
3. O console está na linha 1, que é invisível. Se voltar a ter mensagens de pickup, colocá-lo numa linha da área 3D sem céu, ou usar sprites.
4. Dois pontinhos cor-de-rosa na borda direita, linha 4, provavelmente sprites do console. Cosmético.
5. Sem THINGS (inimigos e itens), portas ou gatilhos. A PVS ainda considera tudo visível; o custo está limitado pela neblina.
6. A ROM de controle (mapa de teste do Manifold) pisca. Não teve prioridade.
7. Teste em console real: pendente.
