# Manifold E1M1 — pós-M06, correções da área externa (2026-11-10)

Branch ativa: `exp-manifold-e1m1-m01`. Referência congelada: `exp-manifold-m06-baseline` (commit `0cf6b1090407542b1155fc61fc06f30e544a8ebd`). **R128 e Sega CD intocados**.

## Bugs reportados pelo usuário na M06
1. `ZERO DIVIDE` em região externa — screenshot BlastEm `Offset: 003530`, `Hint: 0086E6`, registrador `d4=0`.
2. Quebra diagonal/triângulo azul-escuro na vista externa do ácido, ainda presente na M06.
3. Céu desloca horizontalmente rápido demais ao virar.

## Diagnóstico comprovado do ZERO DIVIDE
No ELF da M06, o `0x003530` segue imediatamente `0x00352E: divu.w %d4,%d2` em `calculate_tex_coords_for_wall`. O divisor `d4` é `one_over_z_16_span_end`, obtido a partir de um inverso da profundidade Q16. Em paredes distantes, ele pode arredondar/descer até **zero**. A captura do usuário mostra `d4=0`, fechando o diagnóstico. `0x0086E6` é `bmp_do_hblank_process_vertical`, mas **não** é a origem deste `ZERO DIVIDE`.

Em `experiments/DOOM_Manifold_E1M1/m01/stage_rom.py`, `guard_zero_reciprocal_in_texture_columns` impede divisor zero nos escalonadores (inicial e nos finais dos blocos de 2/4 colunas), usando o recíproco anterior quando possível. O conserto remove a exceção específica e exige teste interativo no mesmo local do erro.

## Céu
No gerador `install_sky`:
`cur_player_pos.ang >> 3` → `>> 4`. Metade da velocidade angular; padrão de 16 colunas de tiles agora repete em 90° em vez de 45°. Posição do céu e mapa de VRAM mantidos.

## Diagonal ao ar livre — hipótese e patch
No `far_portal_fog`, o Manifold transformava qualquer portal além de ~1600 unidades em parede sólida escura. Isso pode criar uma linha diagonal artificial cruzando setores externos. O novo código **não aplica esse corte** quando o teto do setor atual ou do setor vizinho tem índice 0 (F_SKY1 transparente). O corte continua para setores interiores; as guardas de profundidade/stack permanecem. O custo de render externo pode subir.

**Atenção:** ainda não é correção visual comprovada. As capturas de tour do MAME exibem cenários externos, mas a primeira vista (`frame_tour_f0060.png`) ainda apresenta extensa região azul-escura uniforme. Isso pode ser um piso sem textura, oclusão ou outro bug de recorte; comparar no mesmo ponto e ângulo da foto do usuário antes de declarar resolvido.

## Validações
- [Action M06 diagnóstica #42817830480](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42817830480): símbolos/disassembly do `0x3530`.
- [Action final #42819417002](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42819417002): **SUCCESS**, ROM 1.835.008 bytes, SHA-256 `04c15361c5ddcf40e8f4c6747c41e402033461fa616bebc660bb9affa0445b3a`, BlastEm 90/1500/3600 quadros (autowalk), MAME tour de setores com céu (900 quadros), capturas em artefato.
- ROM no runner: `/home/dan/Projetos/Personal/manifold-e1m1/run-42819417002-1/doom-md-manifold-e1m1-m02-hintfix.bin`.
- **Ainda não testada interativamente pelo usuário nem no console real.**

## Publicação
A release `manifold-e1m1-latest` deve permanecer na M06 até aprovação do usuário. Workflow agora só publica quando `vars.MANIFOLD_RELEASE_APPROVED == 'true'`; execução anterior tentou publicar e recebeu `HTTP 403 Resource not accessible by integration` (permissões para releases precisam ser corrigidas separadamente). Compilação/artefatos e ROM no runner não dependem da release.

## Próximo passo
Usuário testar ROM #42819417002 no BlastEm gráfico, caminhar para o mesmo ponto externo e verificar: ausência de `ZERO DIVIDE`, velocidade do céu, persistência/localização da diagonal e FPS. Se a diagonal continuar, isolar renderização de floors/portais com captura pareada nas mesmas coordenadas/câmera; não aumentar globalmente distância de fog sem benchmark. Corrigir visual antes de promover a release.
