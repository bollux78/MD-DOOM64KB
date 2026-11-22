# DREAD C7 (proposta) — fácil + IA 12 Hz + projéteis 20 Hz

**Status: código-fonte alterado, SEM COMPILAÇÃO, SEM ROM, SEM benchmark.** Criado em 22/11/2026 a partir do commit C6 `1c99d6a5862f2b886a90356ff2c12f23206931a1`. Nunca substituir a C6 estável sem verificação em console.

## Atualização visual: armas originais do WAD (C5)

Após feedback do usuário, a folha personalizada `tools/weapon_src/guns_optimized_pal.png` da C6 **deixou de ser utilizada** na futura C7. O `tools/build_map.sh` não executa mais `gen_user_weapons.py`; os seis conjuntos de sprites voltam a ser extraídos do WAD pela rotina original `gen_gameplay_assets.py`, como na **C5 (`691c711360`)**. Esse gerador já produz 24 quadros de arma (6 armas × 4 fases), atlas 128×80, paleta PAL1 com 15 cores e transparência, compatível com o HUD atual.

- **Bob da C6 preservado:** `main.c` continua com `sy = sintab[...] >> 12`, deslocamento para cima durante movimento e `HUD_WeaponBob(0,0)` ao parar. Não recuperar o bob maior da C5.
- **Correção dos flashes pretos preservada:** não reverter o carregamento seguro de tiles na C6, nem a lógica de transferência no VBlank.
- **Dithering opcional nas seis armas originais:** `gen_gameplay_assets.py` aceita `DREAD_WEAPON_DITHER=1` (Floyd–Steinberg em RGB nas 15 cores da PAL1 Mega Drive, máscara de transparência preservada). A futura build C7 usa **1 por padrão**; definir `DREAD_WEAPON_DITHER=0` reproduz a quantização sem dithering da C5. A escolha **não** afeta as texturas/paletas do cenário.
- **Limitação:** nenhuma imagem comparativa nem ROM foi gerada; o dithering pode aumentar tiles únicos e o tamanho da ROM, especialmente no layout NORMAL 4 MiB. Validar a aparência em ambas as versões e voltar à opção sem dithering caso apareçam ruídos, paletas inadequadas ou limite de espaço.

## Atualização gráfica C7: grades transparentes em meia resolução

As **grades/vazados** são duas-sided midtextures com máscara de opacidade, desenhadas no renderer pela rotina `draw_mask_column` em `src/render.c`. Na C6 esse código avaliava textura e transparência para **cada coluna e linha lógica** e ordenava grades/sprites por coluna para preservar a oclusão correta.

- A macro de compilação `DREAD_GRATE_HALF_RES` ativa **amostragem em blocos lógicos 2×2** somente onde há máscara de transparência (`m->mask != NULL`): usa uma coluna de textura para cada duas colunas lógicas e um texel vertical por par de linhas, replicando a cor somente nos pixels dentro do recorte original.
- Reaproveita entre duas colunas consecutivas o resultado de projeção U e o ponteiro de textura num cache **por parede**, reinicializado a cada trecho colocado na fila.
- Projeção das bordas, limites `ceilclip/floorclip`, cálculo de profundidade e **ordenação de cada coluna contra os sprites permanecem intactos**. As paredes opacas e sprites não são reduzidos.
- `gameplay/build.sh` ativa a macro por padrão. **Para comparação A/B**, configurar `DREAD_GRATE_HALF_RES=0` durante uma futura compilação autorizada; isso retorna o caminho original de alta resolução sem mudar as demais configurações da C7.
- Essa redução tem **metade da resolução linear horizontal e vertical nas grades** (até um quarto das consultas verticais por área mascarada), mas não garante ganho equivalente de FPS: a classificação por coluna, as colisões e o DMA do framebuffer ainda custam CPU.
- A textura mais grosseira pode fechar vazados estreitos, causar moiré e padrões de transparência diferentes. Testar grade próxima/longe, em diagonal, com inimigos na frente/atrás, portas, modos 80×72, 160×72, 80×144 e 160×144 e ambas as ROMs NORMAL/SSF. Se comprometer a visibilidade ou a jogabilidade, desativar a macro.

**Status:** código atualizado; sem ROM compilada, sem teste de emulador, sem medição de desempenho ou garantia de fidelidade visual. A C6 estável permanece intacta.

## Alterações realizadas

- `src/actors.c`: `DREAD_COMBAT_12_20` habilita dois acumuladores independentes de tempo lógico, ambos em VBlanks: **IA a 12 Hz** (5 VBlanks por passo) e **projéteis a 20 Hz** (3 VBlanks por passo). Acumuladores preservam os restos entre quadros renderizados; são zerados por `Actors_Init` em cada fase. Nenhum relógio depende da velocidade de emulação.
- O código já limita `dt` a 8 VBlanks por frame; esse limite original não foi alterado. Portanto, quando FPS de renderização é baixo, o tempo simulado continua sendo limitado como antes. Passar `dt=8` agora pode provocar 1–2 varreduras de IA e 2–3 chamadas de projéteis, em vez de 8 varreduras completas por VBlank; a contagem exata depende dos restos acumulados.
- A rotina `tick_proj(pl,3)` **mantém 3 subpassos de deslocamento/colisão de parede**, para evitar atravessar paredes finas; portanto reduzir a frequência de chamadas não elimina os 3 testes internos de percurso de cada janela. A checagem final do dano contra o jogador permanece no fim de cada bloco de 3 VBlanks e merece validação manual em alta velocidade.
- Barris explosivos permanecem com temporização por VBlank, animações e acionamentos encadeados. Teste de coleta de drops agora é feito uma vez por frame renderizado (em vez de até 8 vezes por frame).
- `DREAD_EASY_MODE`: dano recebido passa a metade, arredondando para cima, antes do cálculo de armadura; não modifica dano das armas do jogador.
- `tools/conv.py`: opção `--skill easy|medium|hard`, com default `DREAD_SKILL` do ambiente ou `medium` para retrocompatibilidade; filtra os monstros e demais THINGS conforme as flags **originais** do WAD (bits 1,2,4 correspondendo a easy/medium/hard), excluindo objetos apenas de multiplayer como antes. A tabela de sprites é gerada para os monstros de fato incluídos.
- `gameplay/build.sh`: habilita `DREAD_SKILL=easy`, `-DDREAD_COMBAT_12_20` e `-DDREAD_EASY_MODE`. Os scripts de conversão **não** devem reutilizar caches médios da C6; para impedir mistura de população, o script rejeita `DREAD_PREPARED_MAPS` nesta experiência e exigirá regeneração das tabelas quando a C7 for compilada, após autorização.

## Atenções técnicas antes de liberar ROM

1. **Não houve compilação, execução no BlastEm/Genesis Plus GX, ROM gerada ou validação no console.** Revisão realizada apenas por inspeção e checagens textuais no GitHub.
2. **A IA e os estados/frames dos monstros são processados a 12 Hz**; como os cronômetros internos são em VBlanks, mudanças de quadro em fases curtas (p.ex. morte 8 VBlanks) terão quantização de até um passo de 5 VBlanks. Isso pode tornar algumas animações ligeiramente mais lentas: verificar visualmente e separar animações de decisões se necessário.
3. **Os projéteis são atualizados a 20 Hz**, preservando três subpassos para colisão com paredes e com monstros atingidos pelo foguete. Testar explicitamente impactos contra o jogador, barreiras finas, portas, chão/teto e barris; não presumir que taxa menor garante colisão idêntica.
4. O filtro easy original pode manter muitos inimigos em determinadas fases. Medir contagens totais por mapa e eventuais monstros no boss E1M8; nunca inventar porcentagem de redução.
5. O benchmark publicado da C6 (80x72 4,09FPS versus 160x72 3,21FPS) foi medido **sem IA** e não prova ganhos desta alteração. Executar um **novo benchmark com IA/combate ativo** em cenas de alta densidade, em modos 160x72 e 80x72, hardware sem SRAM, nos dois layouts (4MiB e SSF10MiB), evitando comparar mapas/dificuldades diferentes.
6. A C7 fácil é uma proposta de ROM separada. **A C6 NORMAL e a C6 SSF não foram alteradas**; para comparações justas, incluir uma compilação controle C6 com a mesma população easy e toggles individuais da nova IA, quando permitido.
7. Checar memória do Mega Drive e compilação real do 68000 somente após o usuário autorizar.
8. Se causar piora da jogabilidade, preservar timers e duração da animação, ou voltar à C6.

## Resultado esperado (hipótese, não resultado medido)

Menor quantidade de monstros provenientes da flag easy do WAD, menos passagens globais de IA por quadro, frequência conhecida dos projéteis sem depender da taxa de renderização. O FPS pode melhorar mais em salas com vários monstros ativos; porém gargalos em renderização de sprites, `try_move` (O(natores)) e detecção de colisão ainda permanecem.
