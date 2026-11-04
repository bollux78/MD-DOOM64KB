# R130 — Simplificação geométrica adaptativa dos mapas (pedido do usuário)

**Werk → Cláudio — 04/11/2026.** Branch: `exp-claudio-r121-e1m7-20261103`.
**Base candidata:** R128 All (stairs + corpses + sight + far + proteção de overflow R126b). O usuário testou a R128 All no Mega Drive real, relatou ganho grande de fluidez e aprovou a pequena perda de degraus na E1M1. **Não refazer as escadas da R128.**

## Objetivo
Reduzir o trabalho do renderer/BSP com uma simplificação visual pouco perceptível: contornos de paredes com cinco mudanças de ângulo podem ficar com três quando o erro projetado na tela for desprezível. Otimizar sobretudo os *piores frames*, sem reduzir resolução, desativar mais coisas do jogo ou criar paredes quebradas.

**Atenção: a redução de linedefs por si só NÃO garante desempenho.** O renderer opera em segs/subsectors e o custo pode ser dominado por visibilidade, colunas e clipping. Medir segs desenhados, spans, colunas, BSP visits e min FPS.

## Diagnóstico da estrutura atual
O conversor `scripts/lab/convert_r24_episode.py` transforma mapas do WAD original (incluindo VERTEXES, LINEDEFS, SEGS, SSECTORS, NODES e BLOCKMAP). Seu formato final **não contém VERTEXES**: coordenadas são incorporadas em LINEDEFS e SEGS. O `r89_align_maps.py` alinha os linedefs de 31 para 32 bytes; o `r128_stairs.py` altera apenas alturas/setores para que alguns risers virem RF_IGNORE, preservando a topologia.

**Portanto, NÃO editar apenas o LINEDEFS do WAD convertido** e esperar que o resto se ajuste: o render usa SEGS + SSECTORS + NODES, enquanto o gameplay consulta LINEDEFS + BLOCKMAP, etc. Mudar somente endpoints quebra a coerência. Também não remover linedefs arbitrariamente: specials, triggers, colisão e textura podem depender dos seus IDs.

## Etapa A — levantamento seguro, sem alterar mapas
Criar `scripts/lab/r130_geometry_audit.py`:
1. Examinar o **WAD de origem local** (sem colocá-lo no Git público) ou os dados de mapa antes da conversão. Contar linedefs, segs, subsectors, nodes e curvaturas por mapa.
2. Detectar cadeias de linhas adjacentes no mesmo contorno, com endpoints comuns e graus topológicos compatíveis (evitar vértices de junção com 3+ linhas).
3. Aceitar candidatos **apenas quando** texturas, offsets, sidedefs, flags, especiais/tags, setores front/back, floor/ceil e necessidades de animação forem compatíveis. Rejeitar portas, interruptores, elevadores, teletransportes, exits, triggers, setores dinâmicos e limites de iluminação/cor.
4. Calcular erro geométrico perpendicular máximo (unidades DOOM), variação de ângulo e deslocamento em pixels para múltiplas distâncias, com no mínimo casos perto da parede; evitar simplificar quinas marcantes.
5. Publicar **somente estatísticas** por mapa e por tolerância. Não publicar mapas/assets originais.
6. Ordenar candidatos por ganho estimado (redução de segs visíveis por trajeto) e erro visual; ter modo audit-only como padrão.

## Etapa B — protótipos reversíveis
Criar variantes de tolerância progressiva (`geom-conservative`, `geom-balanced`, `geom-aggressive`) + controle **R128 All exata**, mantendo tudo o mais igual. Começar com 0.5/1/2 unidades DOOM de erro perpendicular como hipóteses, ajustáveis à escala real e curvas; nunca presumir que estes valores são suficientes por si.
- **Via correta:** modificar a geometria fonte ANTES da geração de BSP e regenerar SEGS, SSECTORS, NODES, BLOCKMAP e REJECT (ou demonstrar rigorosamente quais dados permanecem válidos). Recomendar node builder livre compatível/controle de versão, cuidando da conversão dos lumps para o layout atual.
- Alternativa de menor risco: descobrir oportunidade de mesclar *apenas trechos de segs de render* que sejam matematicamente colineares dentro do mesmo subsector, preservando a geometria e a colisão originais; isso não é aproximação de quinas, mas oferece experimento inicial sem alterar topologia. Fazer análise dos invariantes de cada subsector e offsets de textura.
- Verificar `REJECT` conservador: jamais introduzir falsos negativos de visibilidade; a regeneração deve considerar os setores originais.
- **Não** modificar em runtime a geometria física para quantizar ângulos; isso traz inconsistência visual/colisão.
- Preservar o nome/identidade dos mapas, limites dos lumps, recursos, texturas, offsets, som, portas e interações. Quando geometria de colisão mudar, o critério de aceite é permitir apenas diferenças minúsculas verificadas em jogo, nunca bloqueios/atalhos/movimento indevido.
- O `convert_r24_episode.py` tem asserts de fidelidade do mapa original; adaptar o conversor num ramo experimental explícito sem enfraquecer os checks dos builds controle.

## Etapa C — benchmarks e QA
- Construir ROM `pl` e `pf`, privadas no runner/MD-DOOM-PRIVATE, sem ROM/WAD/ELF em artifacts ou commits públicos. Respeitar políticas R129 de arquivamento.
- Testar 10 demos até o fim, E1M1–E1M9, portas/escadas/lifts/triggers, áudio e HUD, `.data/.bss`, Z80-read abaixo de 2 MiB, máximo ROM 4 MiB e BSS <= 57920; manter exatamente proteção de overflow R126b.
- Números comparáveis: H40, NTSC divider 7, AI Normal, Shadow Off, bench com checkpoints/perf apropriados. Atenção: mudanças geométricas podem alterar demo-sync; diferenças lógicas são aceitas somente após examinar jogabilidade e teste até fim, não mascarar crash.
- Reportar por mapa: original/candidato `linedefs/segs/subsectors/nodes`, áreas com mudanças, erro geométrico máximo, contagem média/p95 de segs renderizados (se disponível), FPS médio e mínimo, especialmente E1M7; separar custo de compilar/converter de custo de render.
- Produzir screenshot A/B em câmera fixa, com atenção a silhuetas, textura, ausência de gaps e colisão. **Usuário decide no Mega Drive real**, como fez na R128 All.
- Não trocar base automaticamente: só substituir R128 All se melhorar FPS mínimo/perceptivelmente e manter aspecto reconhecível.

## Integração
Solicito ao Cláudio: implementar primeiro o auditor de candidatos (A) e enviar relatório com contagem/custo por mapa, depois propor o mecanismo mais seguro de simplificação e uma bateria pequena de ROMs controladas. Separar esta tarefa da R129 **backup privado** (numeração R130 não significa alterar a R129). Não disparar benchmarks pesados sem confirmar espaço/CPU e sem gerar candidato coerente.

## Referências do projeto
- `scripts/lab/convert_r24_episode.py`: conversão WAD; `LINEDEFS` de 31 bytes, `SEGS`, `NODES`, `SSECTORS`, `BLOCKMAP`, `REJECT`.
- `scripts/lab/r89_align_maps.py`: linedefs de 31 → 32 bytes.
- `scripts/lab/r128_stairs.py`: simplificação já aprovada de alturas de setores.
- `docs/agent-handoffs/R128-CLAUDIO-SIMPLIFY.md`: lógica da R128 All.
- `docs/agent-handoffs/R129-PRIVATE-ARCHIVE-POLICY.md`: política de artefatos públicos/privados.
