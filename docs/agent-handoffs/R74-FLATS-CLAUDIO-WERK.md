# HANDOFF R74 — Cláudio + Werk: flats sem faixas verticais

**Data:** 27/10/2026  
**Origem:** R73-M (MicroDither M25) aprovada visualmente; R73-F rejeitada por quadriculado grosseiro.  
**Base técnica:** R71A12MUL-HUD (benchmark histórico 7,32 FPS), HUD-WAD e margens H40 obrigatórios.  
**Status:** especificação; nenhuma R74 compilada, medida ou aprovada.

## Observações confirmadas em hardware
- A R73-M é a melhor em riqueza cromática e detalhes; preservar suas paredes e sprites.
- A R73-F apresenta padrão 2D quadriculado muito visível. NÃO reutilizar sua alternância x/y.
- O problema prioritário é o contraste entre colunas pares/ímpares no chão e teto, ambos visualmente sem texturas na configuração testada.
- Não confundir FPS instantâneo nas fotos com o benchmark DEMO3 de 7,32 FPS.

## Evidência de código e intervenção proposta
Na branch `exp-chatgpt-r73-r53-palette-tests-20261027`:
- `src/r22_video.inc`, `R_DrawColumnFlat`: as superfícies planas têm **caminho próprio**. Com R64A, `r52map=cx->flat[x&1u]`; fora do R64A usa `flat_even`/`flat_odd`. A coluna é preenchida com `sample=r52map[c]&15`, replicada pelo caminho Pair-V Fast.
- Paredes selecionam `wall_even`/`wall_odd` e LUTs `comp_even`/`comp_odd` por outros caminhos. Preservá-los.
- `scripts/lab/gen_r73_r53_fixed.py`: `r73_flat_even=r52_even` e `r73_flat_odd=r52_odd`. **Separar estas LUTs é a intervenção mínima proposta**, sem alterar o loop de pixels.
- `R47_LoadPairTiles` monta os pares de cores físicos dentro dos tiles. O padrão M25 já foi aprovado; conservá-lo.
- `src/r_plane.c` separa `skyflatnum` (chama `R_DrawSky`) de flats comuns. Embora não haja texturas discerníveis nos pisos da ROM testada, verificar a origem de `c` antes de assumir que todo o pipeline de flats dispensa amostragem.

**Hipótese a testar:** construir tabelas estáticas `r74_flat_even[256]` e `r74_flat_odd[256]` específicas para flats e apontar `R64A_Fill().flat[0/1]` para elas. Custo por pixel deve ficar idêntico, a confirmar via assembly e benchmark. O número de cores por paleta/CRAM não aumenta.

## Cláudio — geração de LUTs (trabalho principal)
1. Usar **CRAM efetivamente quantizada do Mega Drive** nas duas paletas R73-M (`near25`, `zero-policy=forbid`).
2. Para cada índice de cor fonte `c`, enumerar pares PAL0[i], PAL1[j] para i,j de 1 a 15, e medir: erro da cor média em relação à cor-alvo, diferença perceptual entre colunas (`ΔE`), luminância (`ΔL`) e, quando útil, chroma/matiz. Ponderar pelas cores efetivamente presentes nos flats.
3. Testar função-objetivo do tipo `erro_alvo + λ·ΔE_colunas + μ·|ΔL_colunas|`; penalizar pares de alto contraste com maior força em superfícies grandes. Evitar desbotar azul/verde/cinza.
4. Entregar três políticas **com as mesmas CRAM e paredes intactas**:
   - **C1 Flat-Nearest:** prioriza cores pares/ímpares mais próximas.
   - **C2 Flat-Balanced:** equilíbrio entre homogeneidade e fidelidade à cor-alvo.
   - **C3 Flat-Strict:** diferença entre colunas fortemente limitada, com relatório dos casos inviáveis.
5. Só se necessário, **C4 Flat-CRAM**: realocar algumas entradas de paleta em experimento separado, documentando regressões de paredes e sprites.
6. Entregar gerador reprodutível, LUTs 256×2, relatório JSON com hashes, métricas antes/depois, exemplos de faixas de cor e testes de índices 0..15. Zero continua reservado/transparente.

## Werk — integração, compilação e sky
1. Partir da R73-M, manter `DOOM_R71_MUL_ASM`, R64A, HUD-WAD, H40 e MicroDither M25. NÃO levar a correção de checkerboard da R73-F.
2. Introduzir define isolado (sugestão: `DOOM_R74_FLAT_NEAR`). Fazer só a seleção dos mapas de **flats** apontar para as LUTs do Cláudio, sem alterar as de paredes ou sprites. Verificar escolha via `cx->flat[x&1u]` e os dois caminhos do renderer.
3. Compilar PERF/PLAY para C1, C2 e C3 (seis ROMs) em diretórios isolados. IDs curtos: evitar `R60 ROM ID exceeds header limit`; incluir flags, SHA-256, manifesto, BSS <= 57.920 B e ROM <= 4 MiB.
4. Testar no mesmo enquadramento a homogeneidade do chão/teto e integridade das paredes, HUD e sprites. Rejeitar quadriculado grosseiro.
5. **Céu (experimento separado):** localizar `R_DrawSky` invocada em `src/r_plane.c`. Se tecnicamente viável, usar fundo sem perspectiva de piso e rolagem horizontal discretizada por 8 pixels físicos (um tile). Verificar costuras, repetição, viewport, avanço angular, VRAM, custo real; primeiro conferir se essa simplificação já existe. Não misturar com C1–C3 na primeira avaliação.

## Critérios de aceitação
- Piso e teto visivelmente mais homogêneos, com menor distância de luminância/matiz entre colunas pares e ímpares.
- Fidelidade cromática próxima da R73-M. Piso “uniforme”, porém com cor errada, é reprovação.
- Paredes, colunas, sprites e detalhes preservados; nada de checkerboard R73-F.
- HUD intacto e FPS medido com relógio original em hardware real (mesmo percurso/DEMO3 da R71); até 10.000 frames bastam.
- Registrar diferença antes/depois e métricas; não alegar ganho de FPS sem medidas.

## Handoff entre os agentes
**Cláudio:** entrega LUTs e métricas + gerador. **Werk:** integra essas LUTs mantendo renderer otimizado e publica ROMs e benchmarks. Se forem mudar CRAM ou céu, cada alteração deve gerar uma variante isolada. Escolha final feita pelo usuário após avaliação no Mega Drive.

**Referências:**
- Repositório: https://github.com/bollux78/MD-DOOM64KB
- Branch de partida: https://github.com/bollux78/MD-DOOM64KB/tree/exp-chatgpt-r73-r53-palette-tests-20261027
- R73 workflow: https://github.com/bollux78/MD-DOOM64KB/actions/workflows/r73-r53-tests.yml
