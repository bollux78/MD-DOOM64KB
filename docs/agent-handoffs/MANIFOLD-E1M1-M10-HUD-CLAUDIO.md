# Handoff para Claudio — Manifold E1M1 M10: HUD clássico do DOOM (reutilizar HUD da R128)

**Data:** 10/11/2026  
**Repositório:** https://github.com/bollux78/MD-DOOM64KB  
**Branch de trabalho:** `exp-manifold-e1m1-m01` (ou nova branch M10 derivada dela)  
**Baseline reproduzível:** `exp-manifold-m08-doors-eye-baseline` — commit `82e483dcad5cdcea3126e9affcaa6bc45e56a532`  
**Objetivo da M10:** substituir a faixa de HUD/inventário do Manifold pelo **HUD-WAD já criado por Claudio para a R128**, preservando jogo, câmera, céu, arma/buffers, fps e tempo de quadro.

## Solicitação do usuário

> "handoff pro claudio fazer m10, ele que fez o hud da r128"

O usuário quer a faixa inferior clássica de DOOM, não um HUD novo inspirado vagamente. O cenário externo ainda tem algumas quebras visuais, mas a M08 está funcionando bem no BlastEm gráfico; manter essas correções e não misturar trabalho de reparo de geometria, portas e performance pesada no M10.

## A. Referência autoritativa: HUD-WAD da R128

**Prioridade: portar/reaproveitar, não redesenhar.**

- [Política de HUD da R128](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/docs/agent-handoffs/HUD-PADRAO-R71-EM-DIANTE.md): o HUD-WAD de Claudio é padrão a partir de R71; H40 com *stone margins*, assets extraídos do WAD no runner, não em commits.
- [Gerador de assets](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/scripts/lab/gen_hud_wad.py): patches `STBAR`, `STTNUM*`, `STYSNUM*`, `STGNUM*`, `STKEYS*`, `STF*`; gera paletas, tiles estáticos, dígitos, chaves e **42 faces** (`hud_faces[42][16][8]`); faixa adaptada de 320 para **256×32 px**, 32×4 tiles.
- [Lógica de composição](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/src/hud_wad_logic.h): `HudState`, `HUDW_ComposeRow`, `HUDW_Hash`, `HUDW_FACE_SLOT`, lógica facial; parte é host-testável, porém contém premissas de VRAM particulares da R128 (**não copiar `HUDW_VRAM_BASE=800` cegamente**).
- [Ferramentas e testes](https://github.com/bollux78/MD-DOOM64KB/tree/exp-manifold-e1m1-m01/scripts/lab): `hud_images.py`, `test_gen_hud_wad.py`, `test_hud_wad_logic.py`, `test_r79_face.py`.
- [Tratamento visual avançado de rosto](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/docs/agent-handoffs/R79-FACE-ADAPTIVE-SHADOW.md): face 32×32, margens transparentes preservando pixels, 42 quadros. É possível reaproveitar, mas efeitos shadow/highlight da R128 **não são requisito da M10**.

**Importante:** o gerador atual usa paleta 3 para barra/dígitos e paleta 2 para faces. No Manifold, `PAL2` já pertence ao HUD/inventário atual; verificar onde `PAL3` é usado por céu/textura/sprites antes de reservar as duas linhas. Se for necessário, reindexar tiles e paletas com validação de CRAM; evitar modificar cores do cenário.

## B. Como funciona o HUD atual da Manifold

Upstream Manifold `ehaliewicz/Manifold`, commit `b6fe52a52344464de00bde4dc58a40f8b89cfc1a`:

- `src/inventory.c` e `src/inventory.h`: `inventory_init(free_tile_loc)` carrega o HUD genérico, sete ícones de inventário e sua `PAL2`, grava no **BG_B a partir de `HUD_BASE_Y=21`**; `inventory_draw()` atualiza ícones somente quando `dirty`; `inventory_cleanup()` libera o estado.
- `src/game.c`: invoca `inventory_init(free_tile_loc)` durante carregamento, `inventory_draw()` durante o jogo. Existe `weapon_sprites.c` que já teve travamento ao apertar A por falta de tiles e hoje usa dois buffers de 128 tiles.
- O atual HUD Manifold é a faixa rosa/azul com retângulo preto e painel de arma vista nas capturas do usuário.
- Manifold ainda não implementa o conjunto DOOM de monstros, itens, chaves e portas acionáveis. **Não inventar dados dinâmicos**. Para os widgets sem estado real, escolher defaults estáveis explicitamente marcados como temporários (ou não mostrar estado impossível). Para vida/munição, conectar apenas ao que realmente existe em `game.c`, `inventory.c` e `weapon_sprites.c`; inspecionar fonte concreta.

## C. Layout/VRAM e áreas perigosas — auditar antes de escrever

Referência: [handoff M06 para Werk](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/docs/agent-handoffs/MANIFOLD-E1M1-M06-WERK.md).

- Framebuffer Manifold ocupa **896 tiles**.
- VRAM para HUD, arma buffer 0, recursos de console/fonte tem ocupação própria; `src/weapon_sprites.c` usa **dois buffers de 128 tiles**, segundo na VRAM recuperada do WINDOW. Não sobrescrever nenhum buffer.
- Fonte SGDK citada em **0x4E0–0x53F** — conferir valores **reais da M08/M10 em runtime**, não assumir ranges disjuntos só pela documentação.
- O mapa do WINDOW em **0xB000** guarda o segundo buffer da arma; WINDOW aponta para BG_B.
- **Céu SKY1** na parte inferior do BG_B, linhas **30–63**, em torno de **131 tiles**; não acessar/modificar essa faixa.
- Inventário escreve até linha **28** de BG_B. **Linhas 28–29 são região sensível**; corrigir o layout segundo o modo de exibição do Manifold antes de escrever a barra. Extended blank apaga linhas da tela fora da janela 3D; preservar/configurar exceção explícita para exibir HUD sem vazamento de lixo acima/abaixo.
- R128 `HUDW_VRAM_BASE=800` é específico da implementação R128 (pair tiles). **Criar alocação e asserts do M10**, após calcular o espaço disponível de verdade; não transplantar constantes.
- Avaliar BG_B tilemap, prioridade, H32/H40 e sobreposição com sprites, além de limites de DMA em VBlank; não usar buffer reservado do WINDOW/arma como tiles estáticos do HUD.
- **Preferir atualização incremental** do HUD (`HUDW_Hash` e apenas linhas/tiles alterados) e manter a barra majoritariamente estática; não redesenhar/reenviar a faixa inteira a cada frame (custo numa engine 4–12 FPS em áreas pesadas).

## D. Implementação sugerida (M10)

1. Criar módulo próprio experimental (por exemplo, `src/doom_statusbar.c/.h` **apenas na cópia Manifold do estágio**, ou patch gerado por `stage_rom.py` com origem auditável) para receber as tabelas geradas por `gen_hud_wad.py`. Evitar colisão com símbolos `hud.h` e assets `res` do Manifold.
2. Gerar `hud_wad_assets.h` do mesmo **WAD privado no runner** usado para E1M1. Nenhum WAD, lump ou C header contendo assets proprietários entra no Git. O gerador e o código aberto podem ser versionados.
3. Substituir apenas as chamadas a `inventory_init`, `inventory_draw` e `inventory_cleanup` por wrappers de status bar com contrato compatível; observar código que ainda consulta `inventory_add_item`, `inventory_has_item`, etc. Se indispensável manter lógica de inventário, separar lógica e renderização sem quebrar gameplay.
4. Portar os **32×4 tiles** do HUD-WAD: fundo de pedra, ammo, health, armor, tabela munição, armas, chaves, face 32×32. Verificar se espaço vertical/estilo de exibição Manifold permite o posicionamento como no Doom clássico (adaptar H32/H40 sem esticar). As margens H40 devem manter visual coerente com a R128.
5. Na primeira versão, usar **face estática central válida** e valores coerentes com o estado de jogo; em segunda variante, animar os 42 quadros somente se gatilhos de vida/dano existirem. A arma visível e suas animações são pendência independente, **não depender da solução da arma para aprovar o HUD**.
6. Criar documentação de alocação VRAM **ANTES/DEPOIS** (tile base/count, bytes, paletas, nametable e sprites), asserts para impedir sobreposição em runtime e checker CI verificando limites. Não sacrificar o céu, sprites, textura, FPS counter nem alterações da câmera.
7. Criar **duas ROMs comparáveis no mesmo commit**: `m10-hud-control.bin` (M08 intacta) e `m10-hud-doom.bin` (novo HUD). Comparar mesmas coordenadas, câmera e cenas, não apenas frames iniciais. Preservar hashes e nomear arquivos inequivocamente.
8. Testar no **MAME com capturas reais**, BlastEm gráfico/headless, autowalk 3600 quadros, inicialização, START/pause, A/fire, saída para área externa, câmeras e céu, troca de weapon buffers. Fazer screenshots com HUD todo visível e verificar números não cortados, rosto correto, paletas/tiles intactos, sem sobreposição no céu.
9. Medir custo CPU/DMA e **FPS na escadaria** M08 controle vs M10 em posições idênticas. O HUD não deve introduzir queda perceptível ou piora de VBlank/tearing.

## E. Critérios de aprovação

- HUD reconhecivelmente fiel ao DOOM, baseado no **mesmo HUD-WAD de Claudio usado na R128** e com aparência correta na largura da Manifold.
- Nenhum artefato na área externa, céu ou arma produzido pela troca de HUD; sem corrupção de VRAM, CRAM, tilemaps, WINDOW, fonte ou framebuffer.
- START, movimento, giro e A funcionam como na M08; sem `ZERO DIVIDE`, `ADDRESS ERROR` ou hard lock.
- Valores ligados a estados reais quando disponíveis; campos não implementados definidos no handoff, sem fingir que já há armas/itens/chaves/monstros do Doom.
- Capturas **pareadas** M08/M10, checksum e relatório VRAM. Performance medida na escada, não presumida.
- **Nada publicado na release fixa** `manifold-e1m1-latest` antes de o usuário testar e aprovar no BlastEm gráfico; teste de Mega Drive real depois.
- R128 e Sega CD sem alterações. WAD privado permanece no runner.

## F. Estado do trabalho a preservar

- [M08: portas, câmera, escadaria](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/docs/agent-handoffs/MANIFOLD-E1M1-M08-DOORS-EYE-STAIRS-WERK.md).
- ROM M08 verificada em Action [#42821454241](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42821454241): `/home/dan/Projetos/Personal/manifold-e1m1/run-42821454241-1/doom-md-manifold-e1m1-m02-hintfix.bin`.
- Tentativa de LOD para paredes distantes em M09 **revertida** após regressão de FPS e visual: não reinserir no HUD M10.
- Correção prévia de `ZERO DIVIDE` na textura externa; sky scroll mais lento; teste dos setores com céu.
- **Workflow:** `.github/workflows/manifold-e1m1-rom.yml`; commits `[manifold-rom]` disparam build automático. Autorização do usuário para compilar está dada, mas **não sobrescrever release ou branch estável**. Considerar workflow M10 separado para gerar as duas variantes e capturas.
- No momento deste handoff o último commit na branch deve ser verificado antes de iniciar: não presumir que o código não mudou enquanto Claudio lê. Usar SHA fixo/branch M10 de partida.

## Entrega solicitada a Claudio

**Implementar a M10 (HUD Doom-WAD da R128 na Manifold)**, compilar duas variantes, gerar capturas MAME/BlastEm, documentar mapa de VRAM/paletas/uso de DMA e fazer handoff de conclusão. Priorizar fidelidade, estabilidade visual e preservação de FPS, sem prometer funcionalidade Doom ainda inexistente.

**Manter as otimizações de escadas/pontes, o reparo residual da área externa e as portas com acionamento para marcos posteriores.**
