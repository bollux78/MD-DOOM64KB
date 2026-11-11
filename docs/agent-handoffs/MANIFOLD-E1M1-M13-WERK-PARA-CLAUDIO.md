# Manifold E1M1 M13 — retorno do Werk para o Cláudio (11/11/2026)

**Referência recebida:** [handoff M13 Cláudio → Werk](MANIFOLD-E1M1-M13-CLAUDIO-PARA-WERK.md), commit `6968fe7`. **Branch compartilhada:** `exp-manifold-m12-claudio`. H40 é a única resolução de desenvolvimento no momento.

## 1. Sincronização e procedência

- Li as seções 1–6 do handoff recebido e o diagnóstico M12 anterior (inclusive seção 8).
- A **ROM fixed do Werk** veio da branch de experimento separada `exp-manifold-m12-h40-stability`, commit `74133dc`, Action **[43024454693](https://github.com/bollux78/MD-DOOM64KB/actions/runs/43024454693)**, `manifold-m12-h40-precision-window-ab`. Ela produz `m12-h40-control.bin` e `m12-h40-fixed.bin`. **Não** possui o padrão posterior `MANIFOLD_BUILD_TAG`/`CLAUDIO M12 PLAY H40`, então não há etiqueta de build nela.
- O usuário informou que a fixed **funcionou** antes deste handoff, mas **não relatou um teste discriminante da etiqueta, do flicker de sua última linha, ou uma comparação lado a lado do HUD fixed vs. M11/M12 no CRT**. Não concluir que a fixed resolveu o HUD.
- A **M12 play H40 do Cláudio**, Action **43042097429**, **foi testada no console/CRT**: jogo e etiqueta presentes, fundo preto no HUD, última linha da etiqueta piscando; pequenas alterações de pixels no canto direito. O **M11 control H40** do mesmo run mostrou mais elementos do HUD, sem o mesmo fundo preto, mas ainda incompleto, e `FPS 3.3–3.4`, com queda durante o jogo. A M12 mostrou cerca de `FPS 3.0` na captura. Estes resultados são do console, não de MAME/BlastEm.

## 2. Interpretação e hipótese técnica — **não é correção comprovada**

Há um teste A/B especialmente valioso **dentro do mesmo run 43042097429**: M11 controle sem flags M12 contra M12 play (BSP+RADIUS+STABLE_VIEW). Ambas geram o HUD pelo mesmo `install_doom_hud()` e chamam o mesmo `hud_fps_and_build_tag()`, de modo que o sintoma **não aponta simplesmente para um problema estático de paleta ou PNG do HUD**.

Linhas de investigação, em ordem de custo:
1. **Distinguir diferença de VRAM/VDP de diferença no conteúdo:** capturar no mesmo ponto do console/BlastEm ou MAME o BG_B nametable nas linhas 22–26, os índices das tiles do HUD, os bytes dessas tiles em VRAM e a linha PAL2 da CRAM no M11 e M12; observar antes/depois de um flip e do `showStats()`. Verificar se o tilemap está correto, mas sua imagem na VRAM é sobrescrita, ou se o tilemap passa a apontar a tiles erradas.
2. **Reescrita BG_B concorrente:** `showStats()` limpa e reescreve **40 tiles da linha 26 a cada quadro** usando `VDP_clearTileMapRect` e `VDP_setTileMapXY` em CPU. Por estar na região da borda inferior e piscar somente a última linha, testar atualização **somente quando texto/FPS muda**, fora da janela crítica do VDP. O flicker em uma linha de texto **não comprova** corrupção da imagem do HUD inteira.
3. **DMA, SAT e armas:** o handoff M12 registra que `SYS_doVBlankProcess()` não é chamado e a fila SGDK 2 pode ficar sem flush. O uso de `DMA_QUEUE` para a arma e outras atualizações pode produzir sintomas indiretos. Medir o tamanho e overflow da fila antes de ativar `DMA_flushQueue()`; respeitar a janela H40.
4. **Modo BSP como discriminante:** comparar uma variante H40 com apenas BSP ligado, e outra só com RADIUS/STABLE_VIEW, mantendo a mesma instrumentação para identificar a flag responsável; a geometria e a quantidade de células visitadas mudam com BSP.

Hipóteses do handoff anterior do Cláudio que **seguem abertas**: concorrência VInt×VDP e recorte incompleto de colunas; o caso de bordas exclusivas do H32 não é prioridade na H40.

## 3. Respostas explícitas solicitadas pelo Cláudio

| Pergunta | Resposta Werk |
|---|---|
| A fixed tem **etiqueta piscando**? | **Não verificável neste build**: a ROM fixed de `74133dc` é anterior ao M13 e não desenha a etiqueta `MANIFOLD_BUILD_TAG`. Não atribuir um teste negativo a isso. |
| A fixed tem **fundo preto no HUD inteiro**? | **Pendente de teste discriminante em console**. O usuário informou que a fixed funcionou, mas não há comparação visual documentada desse detalhe. A M12 play do Cláudio apresenta o fundo preto; M11 control **não** apresenta esse mesmo sintoma no teste relatado. |
| Perda de texturas da stable? | Foi relatada pelo usuário em versões M12 anteriores; não há evidência de que a fixed elimine todos os cortes em todas as áreas. |
| Base correta para próxima rodada? | **Base de código compartilhada: commit M13 do Cláudio**, adicionando patches específicos por flags, sem substituição ou merge cego de branches antigas. **Base de comparação visual: M11 control H40**, por mostrar mais elementos do HUD e ter causa de degradação ainda a investigar. **Candidata principal de renderer: M12 play H40**, não promovida ainda a baseline gráfica estável no CRT. |

**Atenção:** a ação fixa anterior do Werk consistiu em duas alterações **opt-in** e isoladas na branch `exp-manifold-m12-h40-stability`: (a) coeficientes BSP de frustum em `s32` com escala uniforme para testar overflow/false culling, `MANIFOLD_BSP_PRECISION=1`; (b) respeitar `LINEDEF BLOCKING` para portais/janelas na geração da lista de colisão, `MANIFOLD_DOOM_BLOCKING=1`. Nenhuma dessas alterações foi validada isoladamente no CRT em A/B; não assumir correção causal do HUD. Para importar, portar essas funções/flags ao novo `stage_rom.py` e `emit_portal_map.py`, com testes; não fazer cherry-pick cego.

## 4. Estado de gameplay e recursos futuros

- No ramo histórico `exp-manifold-m12-objects` houve sprites de E1M1, coleta com mudanças de HUD e protótipo de portas, mas **não estão na M13 do Cláudio**. Incorporar cada subsistema em H40 somente depois de estabilizar o HUD, observando possíveis diferenças no layout do BSP.
- Requisitos de longo prazo do usuário: único motor H40, texturas/sprites/som compartilhados e comprimidos entre mapas; considerar SRAM auxiliar apenas se o FPS não cair; menus, abertura e novos mapas exigirão controle explícito do uso de ROM/VRAM/RAM.
- Evitar tratar compilar no runner, autowalk headless e teste visual no console como equivalentes.

## 5. Próximo passo — para a seção 6 do Cláudio

1. Se o usuário solicitar novo build, usar `.github/workflows/manifold-console-set.yml`, opção `builder=werk`, sempre H40, com controle e candidato; só executar quando o usuário pedir.
2. Priorizar diagnóstico concreto do **HUD preto** por contraste M11/M12 e do **pisca da linha 26**, antes de combinar gráficos com objetos/portas.
3. Não assumir que a fixed tem/resolve o defeito da etiqueta. Anotar FPS por cena e por duração, pois o teste atual não separa queda temporal de custo por cena.
4. Entregar o novo conjunto e logs no mesmo turno do build solicitado; não criar releases sem aprovação explícita e teste gráfico.

## 6. Regras de handoff

O presente documento é **apenas informativo**; não altera código do renderer/HUD/VDP nem dispara compilação. O Cláudio deve ler primeiro o head da branch compartilhada antes de continuar. Handoff atualizado em um commit isolado. Nunca commitar o WAD.
