# MANIFOLD E1M1 — M13.2 all-leaves: medição local do Cláudio (11/11/2026, tarde)

Responde a `MANIFOLD-E1M1-M13-2-ALL-LEAVES-RESULTADO-CLAUDIO.md` e corrige `MANIFOLD-E1M1-M13-2-CLAUDIO-RESPOSTA-INICIAL.md`.

**Correção:** na resposta inicial eu escrevi que os buracos não vinham da seleção de folhas pelo BSP. A medição abaixo mostra o contrário: o bbox culling em `bsp_box_visible` é a causa principal dos buracos. Remover esse culling elimina quase todos eles.

Ambiente: MAME headless, ROMs H40 locais com as flags do workflow M13 (`MANIFOLD_BSP=1`, `MANIFOLD_BSP_ALL_LEAVES` 0 ou 1), commit `b6fe52a` do upstream, branch `exp-manifold-m12-claudio` em `83ff9c3`. Contadores lidos da RAM a cada quadro por `counters.lua`.

## 1. Resultados

| Medida | Controle (culling) | All-leaves |
|---|---|---|
| Quadros com colunas abertas (buraco azul), passeio de 7191 quadros | 3857 (54 %) | 379 (5 %) |
| Média de linhas abertas por quadro | 984 | 3,1 |
| Máximo de linhas abertas num quadro | 7575 | 207 |
| Média de células BSP visitadas por quadro | 7,0 | 42,6 |
| Máximo de células visitadas por quadro | 52 | 236 |

Câmeras fixas do M11 (`MANIFOLD_CAMERAS=fixed`, 2397 quadros): controle com 1745 quadros de buraco e média de 964 linhas; all-leaves com zero quadros de buraco e 61 células por quadro em média.

Os blocos azul-escuros são exatamente as linhas que `manifold_fill_open` pinta com `0x1111` no fim do quadro, por não terem sido fechadas por nenhuma parede. Como o contador `manifold_filled_rows` zera com all-leaves na maior parte do passeio, o culling é o mecanismo principal.

## 2. Buracos residuais no all-leaves

Os 379 quadros com resíduo ocorrem em um conjunto pequeno de posições, todas em área externa, com y entre cerca de −3150 e −4256 (unidades de mapa):

- (−192, −3336), (408, −3232), (240, −3232), (3008, −4256), (1360, −3152), (288, −3360), (2422, −3697), (3493, −3424)

A posição fixa E0 do M11, (1781, −3691), está nessa mesma faixa. Ou seja, o resíduo está na área externa que o usuário reportou.

## 3. Hipóteses descartadas

- **Guarda de pilha em `visit_graph`** (`manifold_dbg[7]`): zero células descartadas em ambos os builds durante todo o passeio. Não é a causa.
- **Overflow de `s16` na projeção do bbox:** não se confirmou para as coordenadas acima.

## 4. Custo

Visitar todas as folhas multiplica as células por ~6 (7,0 → 42,6). O FPS do console cai na mesma proporção, mas não medi FPS real aqui; a MAME sem limite de velocidade não reproduz o FPS do hardware.

## 5. Próximo passo

1. Nas posições da seção 2, registrar quais paredes foram visitadas e quais colunas elas fecharam, para as colunas que ficaram abertas. Verificar se são paredes que nunca entram no traversal (folha não alcançada pelos portais) ou paredes que entram mas não cobrem a coluna.
2. Medir se o resíduo é de parede longa passando do `BSP_FAR` (paredes de bordas do mapa ficam fora da distância) ou de projeção perto do plano de recorte.
3. Só depois disso propor uma seleção de folhas que mantenha o resultado sem as 42 células por quadro.

Scripts usados em `experiments/DOOM_Manifold_E1M1/tools/m13/` (`build_ab.sh` gera os dois ROMs; `counters.lua` grava `quadro, linhas_abertas, dbg[0], dbg[7], células` por quadro).

## 6. Continuação (11/11, noite): o que sobra no all-leaves

Dois testes opt-in, sem mudar o padrão dos builds (`stage_rom.py`):

- **`MANIFOLD_BSP_FAR_FOG=1`** aplica a regra de névoa de parede distante também no modo BSP (em `visit_graph`, hoje desligada com `manifold_bsp_mode`). Resultado: quadros com resíduo caem de 379 para 340, mas o máximo de linhas sobe de 207 para 316. **Não é a causa.** Descartada a hipótese de paredes distantes sem parede parceira.
- **`MANIFOLD_BSP_FILL_DIAG=1`** registra o último vão que `manifold_fill_open` pinta (lo, hi, coluna). Resultado, nos quadros com resíduo:
  - **All-leaves:** 291 de 291 casos são **vão no meio** da coluna (lo > 0 e hi < 144), com faixas de 10 a 30 linhas, em colunas 0 a 12 e 63, com posições em área externa. São aberturas de portal entre degraus de altura de piso/teto, cuja face não foi fechada por nenhuma parede visitada.
  - **Controle:** 1191 casos no topo (lo = 0, teto ou céu não desenhado), 489 na base (hi = 144, piso não desenhado) e 2214 no meio. O controle perde sobretudo teto e piso, o que é coerente com o culling removendo folhas.

Conclusão revisada: o culling explica a perda de teto e piso (buracos grandes e azuis do controle). O resíduo que sobra no all-leaves é outro mecanismo, de faces de degrau (portal) no meio da coluna. Próximo passo: nas posições da seção 2, listar as paredes de portal dos dois lados do degrau e verificar qual lado deveria desenhar a face entre os pisos.

Scripts novos em `experiments/DOOM_Manifold_E1M1/tools/m13/`: `span.lua` (registra quadro, linhas abertas, vão, posição do jogador).

## 7. Causa mais provável e ROM de teste

**Testes com uma condição de rejeição desligada por vez** (`MANIFOLD_BSP_CULL_OFF`, controle com 7191 quadros de passeio):

| Teste desligado | Quadros com buraco | Média de linhas abertas | Média de células |
|---|---|---|---|
| Nenhum (controle) | 3857 | 984 | 7,0 |
| `rnx` | 2359 | 533 | 8,2 |
| `lnx` | 2318 | 468 | 8,6 |
| `far`, `front`, `empty`, `cols` | 3850 a 3940 | ~1000 | 7,2 a 8,7 |
| **`rnx,lnx` juntos** | **626** | **6,9** | **9,3** |
| All-leaves (referência) | 379 | 3,1 | 42,6 |

As duas condições de semiplano lateral de `bsp_box_visible()` são as que rejeitam células cujas colunas ainda estavam abertas. Desligá-las juntas reduz o buraco quase ao nível do all-leaves, com custo de ~2 células por quadro em vez de ~35. A álgebra dos semiplanos parece correta à primeira vista, então a causa exata da rejeição indevida ainda não foi achada. Já descartados: overflow de 16 bits em `project_and_adjust_x` (`lsl.w #5`, opção `MANIFOLD_PROJ_FIX`, sem efeito) e escala da tabela de recíprocos (confere: `65536/i`).

**No spawn (parado, 1798 quadros):** o controle tem buraco em 1441 quadros; o ROM de teste não tem nenhum.

**ROM de teste:** `claudio-m13-sides-off-h40.bin` (H40, jogável, sem tour e sem câmeras fixas; construído com `MANIFOLD_BSP=1 MANIFOLD_BSP_CULL_OFF=rnx,lnx` e o resto das flags do M13 A/B). Tag na tela: `CLAUDIO M13 SIDES`. SHA-256 no envio. Não é fix definitivo: é um desligamento conservador de rejeição, que visita mais células.

Para o console, o que medir: buracos azuis no passeio externo, mesmo ponto do M13.2 e FPS com a mesma câmera contra o `werk-m13-bsp-baseline-h40`.

## 8. Feedback do console no ROM sides-off: buracos que mudam com o passo

O usuário viu, no `claudio-m13-sides-off-h40`, paredes com altura correta e céu atrás, mas no espaço aberto faltam trechos do cenário, em azul-escuro. Ao andar um passo para frente ou para trás, o trecho volta, e ao virar também muda.

**Causa provável: o framebuffer não é limpo.** O renderer só limpa `bmp_buffer_write` no modo wireframe e no debug (`game.c:127`, `draw.c:757`). Num span de coluna que nenhum desenho pinta neste quadro, aparece o conteúdo de dois quadros antes, que depende da posição. Por isso o buraco aparece e some ao andar um passo. Isso confirma e completa a nota do handoff M12 sobre os dois buffers.

**Teste de marcador (`MANIFOLD_CLEAR_DIAG=1`):** limpa o buffer com `0xFFFF` a cada quadro. Nas capturas do passeio, as áreas que ficam com essa cor são as que nenhum desenho cobriu. Atenção: no palette atual, o índice `F` também é azul-escuro, a mesma cor do preenchimento de névoa (`0x1111`). O marcador por si não separa os dois casos, então a leitura exige uma cor de marcador distinta.

**Teste de névoa por quadro (`MANIFOLD_CLEAR_VALUE=0x1111`):** ROM `claudio-m13-sides-clearfog-h40.bin`. Limpa o buffer com a mesma cor da névoa em todo quadro. Se o buraco some ou fica fixo, o mecanismo é o do buffer. Se continua variando com o passo, a causa é outra.

**Ainda não resolvido:** o que não é pintado. Para corrigir de verdade, falta achar qual desenho deixa de cobrir cada span (piso, teto ou parede) nas posições do passeio. O ROM de névoa só torna o buraco visível e estável; não o elimina.

**Para o console, comparar:** `claudio-m13-sides-off-h40` (v1) e `claudio-m13-sides-clearfog-h40` (v2) no mesmo ponto. Anotar se o azul fica parado na v2 e se o FPS cai.

## 9. Resultado do teste de névoa por quadro (v2) e próximo passo

- O console confirmou que `claudio-m13-sides-clearfog-h40` piora o FPS e não elimina o defeito. Ele não é a solução e fica só como ferramenta de diagnóstico (`MANIFOLD_CLEAR_DIAG`, desligado por padrão).
- O defeito continua sem localização: não sabemos qual desenho (piso, teto ou parede) deixa de cobrir os trechos no passeio externo.
- Sugestão: comparar o ramo atual com a build corrigida do Werk, que o usuário considera boa, e bisseccionar as mudanças por flag. Isso é mais barato do que seguir instrumentando o renderer às cegas.

## 10. O defeito não é só do E1M1

Pipeline parametrizado por `MANIFOLD_MAP` (padrão E1M1). Medido com o mesmo passeio, 7191 quadros:

| Build | E1M1 quadros com buraco (média de linhas) | E1M9 quadros com buraco (média de linhas) |
|---|---|---|
| Controle (culling ligado) | 3857 (984) | 3410 (913) |
| Culling lateral desligado (`rnx,lnx`) | 626 (6,9) | 217 (1,1) |
| All-leaves | 379 (3,1) | 33 (0,1) |

O mesmo mecanismo aparece nos dois mapas. O ROM `claudio-m13-e1m9-sides-off-h40.bin` é o teste no E1M9 (sem tour, jogável, tag `CLAUDIO M13 E1M9 SIDES`).

Observações:
- O relatório `e1m1-stage.json` continua com o rótulo "E1M1" mesmo quando o mapa é outro; é só rótulo.
- O passeio automático é o do E1M1, então no E1M9 ele anda aleatoriamente e não cobre o mesmo trajeto.
- O E1M9 mostrou outro defeito visível: listras verticais fortes em várias paredes. Não investigado; pode ser outro problema de coluna de textura.

## 11. Feedback do console: E1M9 renderiza certo; altura da câmera e queda

- Usuário: no E1M9 o render está correto (sem o defeito), então o E1M9 não é um caso do defeito de render. A medição de quadros com buraco no controle do E1M9 (seção 10) aparece aqui como resíduo pequeno, invisível na prática. Isso é coerente com o ROM sides-off.
- Câmera alta demais em todos os mapas: aceito por enquanto.
- Gravidade: ao descer escadas, o personagem flutua na diagonal e cai devagar, a cerca de 0,1 g. O resto está bom.

**Causa no código** (`game.c`, bloco da altura de repouso): a altura do olho cai de forma fixa, `FIX32(8)` por quadro, até a altura de repouso do grupo de setores atual. Numa escada, o olho fica atrás do piso e a queda é constante e lenta. Não há aceleração.

**Candidato** (`MANIFOLD_FALL=1`, ROM `claudio-m13-e1m9-fall-h40.bin`): acompanha o piso em degraus de até `FIX32(24)` (altura de degrau de Doom) e acelera quedas maiores, de 4 até 32 por quadro. Não consegui reproduzir a flutuação na MAME, porque o passeio automático quase não desce escadas. A verificação é no console.

Registrado aqui e no commit seguinte.

## 12. Decisão do usuário: só a correção de paredes que piscam

- A única correção de visão que vale aplicar é a de paredes que piscam ao se aproximar, já feita em versões anteriores (guardas de largura zero e de reciprocal).
- As tentativas de melhorar a visão à distância (culling lateral desligado, all-leaves, limpeza do buffer) aumentaram a carga de CPU sem resultado aceitável. Ficam como diagnóstico, não como candidatas. Os ROMs `claudio-m13-sides-off-h40`, `claudio-m13-sides-clearfog-h40` e `claudio-m13-e1m9-sides-off-h40` não devem ser usados como base.
- O ajuste de queda e degraus (`MANIFOLD_FALL`) não mexe na visão; é de gravidade e custa quase nada de CPU. É o único candidato desta rodada.
