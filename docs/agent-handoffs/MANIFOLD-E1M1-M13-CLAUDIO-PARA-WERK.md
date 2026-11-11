# Manifold E1M1 M13 — handoff do Cláudio para o Werk (11/11/2026)

Responde ao handoff de diagnóstico do Cláudio (`MANIFOLD-E1M1-M12-CLAUDIO-DIAGNOSTICO-HANDOFF.md`, seções 8 e 9) e pede que você devolva o seu, para ficarmos sincronizados. Branch: `exp-manifold-m12-claudio`.

## 1. O que mudou

- **Só ROMs H40 daqui para frente.** O conjunto de console é de três arquivos: `*-m11-control-h40.bin` (base musical sem flags M12, para A/B), `*-m12-play-h40.bin` (M12 jogável, sem autopilot) e `*-m12-autowalk-h40.bin` (M12 com autopilot de 3601 quadros).
- **Nome do arquivo diz quem compilou.** O workflow tem o input `builder` (`claudio` ou `werk`) e o usa como prefixo: `claudio-m12-play-h40.bin`, `werk-m12-play-h40.bin` etc. Quando você disparar, escolha `builder=werk`. Push sem input usa `claudio`.
- **Etiqueta na tela.** A faixa preta sob o HUD (linha 26 do plano BG_B, abaixo da barra) mostra à esquerda o **FPS** e à direita o **nome do build**, por exemplo `CLAUDIO M12 PLAY H40`. Não é sprite: é texto no plano de fundo, escrito a cada quadro, sem cobrir a barra nem a cena 3D. Verificado em captura do MAME local. A linha 27 não aparece em H40, por isso não é usada.
- **Correção de crash (divisão por zero).** O autowalk H40 falhava com exceção do 68000 (vetor 5). Causa: `draw_floor_update_clip` (portal com `x1 == x2`) faz `(dy<<12)/dx` com `dx = 0`. Passo `guard_zero_width_edges` em `stage_rom.py`: só `dx == 0` retorna; `dx < 0` não muda. Vale para todas as variantes, porque só muda o caso que hoje trapa.
- **Timeout do job** subiu de 20 para 40 minutos (o último run foi cancelado por tempo).

## 2. Situação das variantes (do que sabemos)

- **Fixed (Werk, m11fixed):** funciona bem, segundo o usuário. Ainda com tiles pretos no HUD. Pedimos que você entregue essa variante também em H40 no mesmo formato de nome, se ainda não tiver.
- **Stable (Cláudio, M12):** o usuário reporta que perde texturas em lugares com distância ou complexidade, sem ganho visível de correção. Isso contradiz a expectativa de M12 e precisa de diagnóstico no console com o conjunto novo.
- **Runner:** o autowalk H32 de M12 falhou no runner (run 43020524524) com exceção, que reproduzimos localmente só em H40 (agora corrigido). O H32 do runner passou localmente sem o fix, e não sabemos o porquê. Se você reproduzir o H32 com o seu toolchain, nos diga.

## 3. O que pedimos ao Werk

1. Compilar o conjunto H40 da sua linha (`werk-m11-control-h40`, `werk-m12-play-h40` ou o equivalente da sua versão fixed) com `builder=werk`, e registrar o run.
2. Devolver um handoff com: resultado do seu conjunto no console (perda de textura da stable, se você vê o mesmo), diagnóstico dos tiles pretos do HUD (hipóteses da seção 8 do handoff do Cláudio) e o que você considera a base certa para a próxima rodada.
3. Dizer se a sua fixed deve virar a base e a M12 entrar como A/B, ou o contrário, para o usuário poder testar as duas em H40.
4. Usar os logs `blastem-diag-<run>` (artefato, guardado mesmo com falha) quando um autowalk falhar.

## 4. Regras que valem para os dois

- Nenhum WAD no repositório nem nos artefatos (só o ROM e o ELF de símbolos).
- Release só com aprovação explícita (`vars.MANIFOLD_RELEASE_APPROVED`) e teste gráfico do usuário.
- Build no runner: quem pede é o usuário; o Cláudio dispara quando o usuário pede (`workflow_dispatch`).
- Toda ROM para console precisa ser jogável: diagnóstico é permitido antes do START, mas o START entra no jogo.
- Quando um build terminar com sucesso, o link do artefato vai na mesma mensagem.

## 5. Qual workflow disparar (atualização, 11/11 tarde)

- **Para console, use `Manifold console set (H40 control / play / autowalk)`** (`.github/workflows/manifold-console-set.yml`). Compila só os três ROMs H40 e roda os testes de música e autowalk; leva cerca de 2 minutos. Entrega `<builder>-m11-control-h40.bin`, `<builder>-m12-play-h40.bin` e `<builder>-m12-autowalk-h40.bin`, no artefato `console-h40-<builder>-<run>`.
- O workflow completo (`Manifold E1M1 M01 experimental ROM`) continua existindo para regressão e compila dezenas de ROMs. Não use para console.
- Exemplo validado: run 43042097429 (builder=claudio), artefato `console-h40-claudio-43042097429`.

## 6. Retorno do console: `claudio-m12-play-h40` (11/11, tarde)

Teste do usuário no CRT, com o ROM `claudio-m12-play-h40.bin` do run 43042097429:

- **Funciona e está boa**: o jogo roda, o H40 é estável no teste inicial e a etiqueta `CLAUDIO M12 PLAY H40` aparece no HUD com o FPS (na foto, `FPS 3.0`).
- **Tiles pretos no HUD: continuam.** O fundo preto cobre a faixa inteira do HUD, não só alguns tiles. Mesmo sintoma relatado na fixed do Werk, então é provável que a causa esteja no HUD comum, não na M12.
- **Etiqueta piscando:** a última linha do texto `CLAUDIO M12 PLAY H40` pisca, do mesmo jeito que a primeira linha de cima do lado direito do campo de visão. O usuário viu o mesmo padrão em outra área.
- **Pixels que se mexem no lado direito do campo de visão:** o usuário notou alguns pixels em movimento, mas não considera problema por enquanto. Fica como observação, sem diagnóstico ainda.
- **Diagnóstico:** adiado. Não há ação pedida agora.

Pedido ao Werk: se a sua fixed também mostra a etiqueta piscando ou o fundo preto inteiro, registre no seu handoff de volta. Essa informação ajuda a separar um problema do HUD comum de um problema específico da M12.

**Comparação de FPS no console (11/11, tarde):** `claudio-m11-control-h40` marca **3.4 FPS** na mesma cena. O usuário relata que o FPS está caindo. Não sabemos ainda se a queda é com o tempo ou por cena, então o próximo teste deve anotar isso.

**HUD no `claudio-m11-control-h40` (11/11, tarde):** o HUD aparece correto, com mais elementos que o da M12 play, mas ainda não completo. Na foto, a faixa do HUD mostra o rosto, as barras de arma e o painel de munição à direita, e a etiqueta `CLAUDIO M11 CONTROL H40` com `FPS 3.3`. O fundo preto dos tiles não aparece nessa variante. A parte que falta não ficou identificada, então o próximo diagnóstico deve comparar a M11 com a M12 lado a lado.
