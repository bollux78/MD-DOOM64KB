# DREAD C7 - matriz A/B de otimização

Base congelada: `c816e6c72a8fc6a3bc989b347ea7166fda835893` (última C7 NORMAL validada no boot). Nenhuma alteração na C7 estável. Handoff de referência: DREAD-OTIMIZACAO-HANDOFF.zip enviado pelo usuário em 22/11/2026.

| Variante | Mudança isolada | Consequência importante |
|---|---|---|
| CONTROL | C7 original, easy, IA 12Hz, projéteis 20Hz | Controle |
| AI6 | IA 6 Hz (10 VBlanks) | Desacelera movimento/animação dos monstros |
| AI4 | IA 4 Hz (15 VBlanks) | Idem, ainda mais |
| TEX2 | Paredes opacas amostradas em 4×2 texels | Menor detalhe, CPU não necessariamente menor |
| TEX4 | Paredes opacas amostradas em 8×4 texels | Perda maior de detalhe |
| GEO_SAFE | Remoção conservadora de limites invisíveis, tentativa de fusão exata dentro da folha | Reduções pequenas previstas |
| GEO_STEPS | GEO_SAFE mais simplificação de degraus | **Altera pisos e colisões** |
| ALL | AI6 + TEX2 + GEO_SAFE | Combinação conservadora (sem degraus) |

AI4 e AI6 são alternativas incompatíveis (não se executam simultaneamente). TEX2/TEX4 também. A variante ALL combina as três alternativas conservadoras conforme o handoff, e não finge incluir alternativas contraditórias ou mudanças de colisão.

**Dados da investigação do handoff:** reconstrução de 216 BSPs ZDBSP não trouxe melhora convincente; simplificação de contornos não deu redução útil mantendo fidelidade; colapso convexo retirou só três nós e zero segs. Essas técnicas ainda são **pesquisa** e por isso não foram incluídas como ROMs supostamente otimizadas. Uma futura investigação de cache por parede e de separação de IA/física também depende de implementação e medições, não é implementada nesta matriz.

Todas as variantes usam exatamente os mesmos assets e o mesmo código C7 de intermission, paleta verde 0x4C4, armas originais, grades 2×2 e quatro modos. As texturas das grades vazadas e os sprites não são degradados no teste TEX. `geometry/E1M*.json` preserva os números de SEGS por mapa, não é medida de FPS.

**Comparabilidade:** medir a mesma rota E1M1 em NTSC e resolução idêntica. Bench 1 sem IA mede custo principalmente gráfico; bench 2 com IA+tiros é essencial para a sensação de jogo. Registar `bench_frames`, `bench_vints`, FPS, SHA-256, tamanho da ROM, segs por mapa. Em cenas com IA 4/6 Hz, os inimigos podem parecer menos difíceis por agir menos, o que é um trade-off, não ganho puro de eficiência. Testar manualmente em BlastEm e no console antes de promover.

Workflow: `.github/workflows/dread-c7-optimization-matrix.yml` (runner self-hosted compila, runners hospedados fazem benchmark e montam o ZIP).
