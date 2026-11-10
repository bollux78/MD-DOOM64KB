# Manifold E1M1 M08 — câmera, portas temporárias, escadaria (2026-11-10)

## Referências
- Branch ativa: `exp-manifold-e1m1-m01`.
- Base estável M06: `exp-manifold-m06-baseline` (commit `0cf6b1090407542b1155fc61fc06f30e544a8ebd`).
- Build pós-M06 aprovada pelo usuário **apenas em BlastEm gráfico**, sem ZERO DIVIDE: [#42819417002](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42819417002).
- Build **M08 candidata**: [#42821454241](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42821454241) — SUCESSO, 3600 quadros autowalk, MAME screenshots, SHA256 `25b73c8535efbfc23b43550b34efba9164530bf20fc63455485ab5d6cbf1e1a7`.
- ROM M08: `/home/dan/Projetos/Personal/manifold-e1m1/run-42821454241-1/doom-md-manifold-e1m1-m02-hintfix.bin`.
- Baseline M08 congelada em `exp-manifold-m08-doors-eye-baseline` (commit `82e483dcad5cdcea3126e9affcaa6bc45e56a532`).
- Release `manifold-e1m1-latest` não foi sobrescrita; segue a M06.
- R128 e Sega CD intocados.

## Pedido do usuário
1. A câmera ficou muito alta/perto do teto.
2. A escadaria fica muito lenta.
3. Sem abertura de portas o jogador não consegue explorar a fase normalmente; a área externa só era acessível caindo da janela.
4. Correção anterior do ZERO DIVIDE funciona no BlastEm real do usuário, e a diagonal externa diminuiu.

## Mudanças implementadas
1. `stage_rom.py`: altura ocular de **82 → 64** unidades na fase com altura vertical 2×. Todas as 4 ocorrências (spawn, atualização do jogo, cálculo de pés para colisão, câmera do tour) mudadas conjuntamente. Não mexer isoladamente na altura sem conferir colisão.
2. `emit_portal_map.py`: no protótipo, ajusta o teto dos setores fechados conectados a vizinhos válidos — **portas permanentemente abertas** por enquanto, sem botões/triggers. No WAD E1M1 detectados exatamente: `(setor, piso, teto antigo, teto novo)` = `(4,0,0,72)`, `(68,-24,-24,48)`, `(76,-24,-24,48)`, `(81,-24,-24,48)`. A conversão multiplica alturas por 2. As paredes sólidas sem portal permanecem sólidas; **não há prova ainda de que todos os caminhos da E1M1 se tornaram transitáveis**.
3. `stage_rom.py`: `limit_repeated_sector_overdraw` restringe limite de revisitas BSP por quadro de `sector_rendered_cache >=14` para `>=10` — aproximadamente 7→5 revisitas no pior caso. Evita custo excessivo mas precisa ser auditado quanto a occlusão e buracos.

## Testes e desempenho: sem ganhos substanciais até aqui
- M06 MAME screenshots: posição em corredor longo/escadaria `frame_e1m1_f0180.png` ~4,0 FPS, `frame_e1m1_f0420.png` ~4,3 FPS.
- M08 MAME: `f0180` 3,8 FPS, `f0420` 4,4 FPS. **O limite de revisitas não resolveu a lentidão.** Diferenças de posição/tempos/contagem podem afetar estas amostras; não declarar ganho ou perda conclusivos.
- Tentativa subsequente M09: `distant_wall_flat_lod` que converte paredes opacas a mais de 768 unidades em cores médias. [#42822447632](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42822447632) passou 3600 quadros, mas F0180 foi 3,9 FPS e o tour externo F0300 caiu de 4,0 para 2,9 FPS e perdeu detalhes. **Rejeitada e revertida** pela atualização `f4376531`. A branch ativa voltou ao conteúdo do `stage_rom.py` da M08.

## Próximas tarefas
- O usuário deve testar a M08 interativamente no BlastEm: altura da câmera, quais portas estão atravessáveis, FPS exato na escadaria, possíveis buracos/diagonal.
- Para FPS, instrumentar tempo por etapa (clip/perspective, colunas texturizadas, recursão de portais, VDP DMA e objetos). Não especular a partir de um único contador de FPS em screenshot. Procurar gargalo concentrado nos muitos portais estreitos e degraus. Evitar substituição global de texturas por cor: experimento M09 não deu ganho.
- Para circulação integral, verificar a conectividade do grafo de células a partir do spawn e da lógica de colisão, inclusive alturas/portas ainda bloqueadas e gatilhos. Abertura provisória de quatro setores pode ser insuficiente.
- Usar testes reproducíveis com câmera estacionária e coordenadas idênticas para benchmarks de FPS; comparar MAME e BlastEm interativo.
- Após aprovação do usuário, implementar abertura de portas por botões/linhas Doom (sem atropelar o trabalho de objetos/arma).
