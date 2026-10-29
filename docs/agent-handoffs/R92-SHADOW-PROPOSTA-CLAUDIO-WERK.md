# R92 — Shadow otimizada + On/Off no menu (proposta conjunta Cláudio + Werk)

Base: R91 (`exp-chatgpt-r91-fast-shadow-20261029`) com a correção do teste de save/load (`exp-claudio-r91-shadow-savetest-20261029`, commit `6751b20`).
Status: **proposta para o Werk implementar.** Nada foi implementado ainda. Decisões aprovadas pelo usuário estão marcadas.

## 0. Decisões aprovadas

1. **Ordem:** O1 (recorte) + toggle On/Off primeiro; O2 (assembly) só depois da medição.
2. **Menu sem S/H** (aprovado pelo usuário): o menu R77 nunca liga o S/H e mostra a pedra com as cores normais. A opção Shadow vale só para o jogo. Ao sair do menu, restaurar a CRAM e o estado S/H escolhidos para o gameplay.
3. **Uma intensidade só.** sh1 e sh2 têm a mesma velocidade (6,83 FPS) e duas tabelas conjuntas não cabem na ROM (ver §6). **O usuário escolhe sh1 ou sh2 pelo visual antes da build.**
4. Shadow **Off por padrão**; A2/L3 preservados; rótulo `SHADOW: ON/OFF` na tela do benchmark.

## 1. Fatos do código atual (verificados por mim no R91)

| Item | O que o código faz | Consequência |
|---|---|---|
| Custo | `R91_ConvertFast` inline em `I_FinishUpdate`; ~164 ciclos/bloco (contagem do disassembly) × 798 blocos (21×38, fixo) = 17,1 ms/frame | Medido: +17,6 ms/frame (274,70 → 312,27 s). O passe explica quase tudo; a medição ON/OFF na mesma ROM vai confirmar o resto. |
| Região do DMA | `R20_VBlankVideo`: com `r57_queued_crop`, transfere linhas `R57_TILE_YMIN..YEND-1` e colunas `R57_TILE_XMIN..XEND-1`; senão linhas 1..21 × 38 | Os blocos fora dessa região **nunca são transferidos** em gameplay. A borda da VRAM é zerada uma vez por `R57_ClearBorder()`. |
| Geometria padrão | `VIEW_MENU`, modo 0, hcrop=vcrop=16: x 6..72, y 6..40 → tiles x 3..35, y 3..19 | **33 × 17 = 561 blocos** (não 544, como escrevi no estudo). H32 usa as mesmas macros. |
| `r57_queued_crop` | Calculado em `I_FinishUpdate` logo antes do `R22_HUD()` e do passe | O passe pode usar exatamente o mesmo predicado e os mesmos limites. |
| Atributos | Em gameplay **não há limpeza por frame** (`R47_ClearPairBuffer` só roda em `V_ClearViewWindow`: wipe, menus, automapa, tela cheia). O renderer reescreve só o byte do código; o passe reescreve a palavra inteira (A 0x8100/0x0100, B 0x2200) | **Confirma a preocupação do Werk:** ao desligar a shadow, a prioridade fica no framebuffer. Prioridade alta em A esconde sprites de baixa prioridade, então é preciso restaurar. |
| `R47_ClearPairBuffer` | Escreve a palavra inteira (atributo base + código 0) | Também apaga os pixels. Para restaurar atributos sem buraco visual, usar uma restauração só do byte alto (§3). |
| Paleta de efeito | `p = r22_newpal==100 ? r77_last_palette : r22_newpal`; CRAM via `R79_PAL0/1[p]` (esticada) nos builds shadow | Off precisa de `R59_CURRENT.pal0/1[p]` com o **mesmo p** (flash ativo incluído). |
| Menu R77 | `R77_MenuEnter` liga S/H; a pedra de fundo usa `R77_StoneRow(p,y,1)` (códigos 1,3,5,6 sob shadow) e os tiles de texto usam a cópia normal; `R77_MenuLeave` desliga S/H e chama `R22_Palette(r77_last_palette)` | Com S/H fora, a pedra precisa de tiles normais (§4). |

## 2. O1 — converter só a região transferida

- **Fonte única de limites (pedido do Werk):** criar uma função ou struct única, p.ex. `R92_DmaRect(&y0,&y1,&x0,&x1)`, que devolve os limites que o DMA vai usar, e fazer o `R20_VBlankVideo` e o passe usarem os dois. Com `r57_queued_crop`: `R57_TILE_*`; sem crop: linhas 1..21, colunas 0..37.
- **Snapshot:** hoje o VBlank lê as macros `R57_*` vivas no momento do DMA. Gravar o retângulo junto com `r57_queued_crop` no `I_FinishUpdate` e usar o snapshot nos dois lugares. Assim o passe e o DMA nunca divergem se a view mudar entre a publicação e o VBlank.
- **Ganho esperado:** 561/798 → −29,7% do custo, ~5,1 ms/frame. Estimativa no DEMO3: ~300 s, ~7,1 FPS (hoje 6,83; control 7,77). Com a view menor o ganho é maior; com a view máxima, nenhum.
- **Equivalência:** dentro do retângulo, a saída deve ser idêntica byte a byte ao R91. Fora, pode diferir (e não é transferida).

## 3. Toggle Shadow On/Off (só jogo)

**Estado:** `static uint8_t r92_shadow_on=0;`, a preferência do jogo. Sobrevive a troca de fase e a save/load durante a sessão; não entra no formato do save. BSS +1–2 B (margem atual 56).

**Menu (`m_text.c`):** item `Shadow:` com `On/Off`, no mesmo padrão do `AI mode:` da R89 (enum, entrada em `OptionsDef`, texto em `M_DrawOptions`).

**Passe em `I_FinishUpdate`:**
```c
if(_g_gamestate==GS_LEVEL && !R76_InGameMenu() && r92_shadow_on){
    /* p>0: fallback R79 (como hoje); p==0: R91 joint, recortado em §2 */
    VDP_setHilightShadow(TRUE);
}
```
Com Off: nenhum passe, nenhum `VDP_setHilightShadow(TRUE)`. Fica o mesmo caminho do control.

**CRAM:** `R79_PAL0/1` deixa de ser fixa no build e vira a seleção `r92_shadow_on ? r79_pal[mode][..][p] : R59_CURRENT.pal..[p]`. Isso afeta `R22_Palette` (VBlank), o recarregamento do `r59_color_dirty` e as saídas de `r35_native4.inc`. Sempre com o **p vigente**: desligar durante um flash não pode voltar para a paleta 0.

**Transição (aplicada ao sair do menu, com o menu cobrindo a view):**
1. `R20_StopVideo()`: concluir qualquer apresentação pendente.
2. **ON → OFF:** restaurar só os bytes altos do framebuffer (A = 0x01, B = 0x22 em todas as 21 linhas), preservando os códigos. São ~1.600 escritas de byte, uma vez. Não usar `R47_ClearPairBuffer`, que apaga os pixels.
3. **OFF → ON:** nada extra; o próximo passe reescreve as palavras.
4. `R22_Palette(r77_last_palette)` já seleciona a CRAM pela preferência (§3).
5. S/H: Off → fica `FALSE`, já desligado pelo menu. On → o passe do próximo frame liga.
6. Só então publicar o primeiro frame: o jogo redesenha a view inteira no frame seguinte.

**Benchmark:** `SHADOW: ON/OFF` ao lado de `AI MODE` na tela de resultado (padrão da R89 em `r22_benchmark.inc`).

## 4. Menu R77 sem S/H (aprovado)

- `R77_MenuEnter`: remover `VDP_setHilightShadow(TRUE)`. A pedra de fundo passa a usar os mesmos tiles normais da pedra.
- **"Cores normais"**, como eu entendo: a pedra com as cores do HUD (`hudw_pal`), não a versão cinza de 4 níveis atual. O jeito simples é que o menu já carrega a própria paleta em PAL0 (`r77_menu_pal`). Construir essa paleta com as cores de `hudw_pal` usadas pela pedra, mais um branco para o texto, e compor os glifos sobre a pedra com esses índices. **Werk: confirmar que sobra um índice livre para o branco** e que os glifos continuam legíveis. Se o usuário quis dizer só "sem escurecer" (a pedra cinza atual sem S/H), basta trocar `R77_StoneRow(p,y,1)` por `(p,y,0)`. Pela matemática do R77, shadow(2k) = normal(k), então o brilho seria o mesmo de hoje.
- `R77_MenuLeave`: deixa de forçar o S/H; o estado vem da preferência (§3).
- Validar no CRT: contraste do texto, HUD visível abaixo, retorno ao jogo.

## 5. Validação

1. **Ponto de captura depois do passe:** tornar o passe uma função não-inline (`R92_ShadowPass`) ou adicionar uma função vazia `R92_AfterPass()` chamada logo depois dele, e dar ao `r70_capture.py` a opção `--break-symbol`. Hoje a captura na entrada de `I_FinishUpdate` **não vê o passe**.
2. **O1 × R91:** identidade dentro do retângulo transferido em todos os tics do DEMO3 (versões PERF das ROMs, ≤8.000 quadros). Fora do retângulo, diferença permitida.
3. **Off × control (mesma base, sem shadow):** framebuffer, atributos, paleta selecionada (`r22_queued_pal` e a fonte da CRAM) e estado S/H iguais em gameplay.
4. **Transições:** ON→OFF→ON no meio da fase, cada uma durante um flash de dano/coleta, troca A2/L3, retorno do menu, mudança de fase e save/load em E1M1/E1M7 (o teste corrigido de `test_r81_rom.py`).
5. **Medição:** a mesma ROM com ON e OFF no benchmark do usuário. Os números do BlastEm só valem no mesmo job.
6. Gates de sempre: ROM ≤ 4 MiB, BSS ≤ 57.920, nome correto da versão no `.bin`, no header e no título do benchmark.

## 6. Orçamento

- ROM atual com shadow: 3.670.016 B. As tabelas conjuntas da shadow (A2 + L3) ocupam 512 KiB; uma segunda intensidade somaria mais 512 KiB → ~4,2 MB > 4 MiB. **Por isso uma só intensidade.**
- BSS: +1–2 B (preferência) + o snapshot do retângulo (4–8 B). Margem atual 56 B.

## 7. Depois da medição: O2 (assembly)

Só se o custo restante ainda incomodar. Partir do assembly que o GCC gerar para O1. Remover `andil #65535` e o `moveal/addal` do ×4, separar as palavras sem `clrw/swap`, e desenrolar 2 blocos tratando largura ímpar e fim de linha (33 colunas no padrão). Minha estimativa é ~100–115 ciclos/bloco; com O1, ~7,7 ms/frame, ~7,3 FPS no DEMO3. Exigir identidade byte a byte com O1 em toda a saída processada.

## 8. Pendências do usuário

- Escolher a intensidade: **sh1 ou sh2**.
- Confirmar o sentido de "cores normais" da pedra do menu (§4): cores do HUD, ou só sem escurecer.
