# DREAD C7 - matriz A/B de otimização

Base congelada: `c816e6c72a8fc6a3bc989b347ea7166fda835893` (última C7 NORMAL validada no boot). Nenhuma alteração na C7 estável. Handoff de referência: DREAD-OTIMIZACAO-HANDOFF.zip enviado pelo usuário em 22/11/2026.

## Classes de variante

Cada variante tem uma classe. A classe diz o que o resultado significa. Só a classe `exact` é otimização no sentido estrito: mesmo jogo, mesmas colisões, mesmos pixels. As demais são trade-offs e só entram como ganho depois de decisão explícita do dono do projeto.

| Variante | Classe | Mudança isolada | O que muda para o jogador |
|---|---|---|---|
| CONTROL | baseline | C7 original, easy, IA 12Hz, projéteis 20Hz | nada (controle) |
| GEO_SAFE | exact | Remoção conservadora de limites invisíveis, fusão exata dentro da folha | nada esperado; **deve** dar pixels idênticos ao CONTROL |
| AI6 | gameplay_change | IA 6 Hz (10 VBlanks) | monstros mais lentos e menos agressivos |
| AI4 | gameplay_change | IA 4 Hz (15 VBlanks) | idem, mais forte |
| TEX2 | visual_change | Paredes opacas amostradas em 4×2 texels | textura de parede com menos detalhe |
| TEX4 | visual_change | Paredes opacas amostradas em 8×4 texels | perda maior de detalhe |
| GEO_STEPS | collision_change | GEO_SAFE mais simplificação de degraus | **altera pisos e colisões** |
| ALL | multi_change | AI6 + TEX2 + GEO_SAFE | combina um trade-off de jogo e um visual; não é otimização pura |

AI4 e AI6 são alternativas incompatíveis, e TEX2/TEX4 também. ALL usa AI6 e TEX2.

## Critérios de promoção

- **Otimização:** só `exact`. Precisa de `render_pixels_equal_control = True` no pack (hash do quadro final da rota de render igual ao da CONTROL) e de medição em pelo menos dois emuladores.
- **Trade-off:** qualquer outra classe. Não entra como "ganho de desempenho" no resumo. Só é promovida se o dono do projeto escolher a mudança de jogo ou de imagem.
- Nenhuma variante vai ao console como otimização antes de passar no teste manual em BlastEm e no console.

## Como ler os números

- **Render (modo 1):** IA desligada. Compara custo gráfico com a mesma cena. É a medição mais limpa.
- **Combate (modo 2):** IA ligada. Compara custo total com inimigos atuando. **Não é a mesma carga entre variantes de IA:** monstros mais lentos se posicionam e atiram de outro jeito, então a rota diverge. O `pack_matrix.py` marca `combat_comparable = False` para `gameplay_change` e `multi_change`. Para essas, reportar o custo da IA por quadro separadamente e tratar o FPS total como não comparável.
- **Histograma de VBlanks por quadro:** o FPS médio (`frames*60/vblanks`) esconde a distribuição. Quadros de 1, 2, 3... VBlanks aparecem em `vblank_histogram`. Um ganho de 0,1 FPS só vale se o histograma mudar de forma coerente. Nas medições do D01 o mesmo trecho variava de 4 a 15 VBlanks por quadro.
- **Hash visual:** `visual_hash` é o hash do quadro final de cada modo (amostragem de pixels em passo 2). Serve para detectar mudança de imagem, não para medir qualidade.
- **Emuladores:** o workflow usa MAME. MAME tem outra temporização de VDP, então FPS do MAME não é prova sozinho. Antes de promover, repetir o teste em GPGX ou BlastEm e no console.

## Protocolo

1. Mesma rota E1M1, NTSC, resolução idêntica e `-nothrottle` (o FPS vem dos contadores do jogo, não do tempo do host).
2. Registrar `bench_frames`, `bench_vints`, FPS, `vblanks_per_frame_mean`, histograma, `visual_hash`, SHA-256, tamanho da ROM e segs por mapa.
3. Rodar cada modo duas vezes e comparar a repetibilidade antes de tirar conclusões. Diferença menor que a variação entre as repetições não é resultado.
4. Confirmar a intermissão e o HUD com um quadro de referência por variante (mesmo quadro, mesma câmera).

## Arquivos

- `bench_mame.py` / `bench_mame.lua`: benchmark MAME. Gera `vblank_histogram`, `visual_hash`, `ai_active`.
- `compile_one.sh`, `variant.sh`: compilação independente por variante.
- `pack_matrix.py`: ZIP com as 8 ROMs, CSV/JSON com classe, FPS, deltas, `render_pixels_equal_control` e `combat_comparable`.
- `geometry/`: números de SEGS por mapa. Não é medida de FPS.

## Workflow

`.github/workflows/dread-c7-optimization-matrix.yml`: o runner self-hosted compila; os runners hospedados fazem o benchmark e montam o ZIP.

Atenção: o job de compilação roda em runner self-hosted em repositório público. Restrinja quem pode fazer push no branch, ou use runner dedicado ao seu repositório, antes de aceitar código de terceiros.
