# R77 — pedra em shadow, texto branco e Hybrid Blue com CRAM própria

Data: 27/10/2026. Base funcional: R76 ad843e09be27f3568e1df454a5fe10d22bd1c94d.

## Menu

- Shadow real do VDP ativo somente no menu congelado durante a partida PLAY.
- Fundo derivado dos dois tiles de pedra usados nas margens do HUD; convertido para quatro níveis neutros adequados à sombra.
- Texto branco normal, independente da paleta de jogo.
- O VDP decide a intensidade também pela prioridade dos tiles transparentes. Por isso cada glyph usa fundo opaco, com níveis normais equivalentes aos níveis shadow da pedra. Sem essa compensação surgiriam retângulos claros atrás do texto.
- Regra digital verificada: shadow de componente 2*k = normal de componente k, k=0..3. Não depende de assumir brilho linear da TV.
- Duas fases de pedra e 96 glyphs por fase: 194 tiles. Alocação após HUD/face, com guarda antes da fonte em 1440.
- WINDOW cobre só as primeiras 22 linhas de tiles; HUD em PAL2/PAL3 permanece com prioridade alta e intensidade normal.
- Entrada gera os tiles uma vez; navegação mantém o fundo e retira somente glyphs antigos. A saída restaura shadow desligado, CRAM de jogo e scroll Pair-V antes de desenhar a partida ou telas nativas.
- Não há sprites operadores de highlight. A API do SDK habilita o modo combinado S/H, mas esta implementação usa somente shadow e normal.

## Hybrid Blue+

A tentativa R76 só remapeava índices dentro da CRAM L3. Isso não eliminou as faixas azuis no teste do usuário.

R77 modifica a CRAM **apenas no Hybrid**. Compartilha quatro azuis puros com palavras 0x200, 0x400, 0x600 e 0x800 entre PAL0/PAL1. Os companions formam os pares (1,2), (2,3), (3,4) desses níveis de azul, produzindo as mesmas três médias M50 encontradas nos flats A2 normais.

As colunas pares e ímpares usam a mesma mistura física, mantendo o checker fino e eliminando a diferença de cor entre colunas para os 15 índices azuis selecionados. Os dois índices originalmente azuis que A2 converte em cinza não são forçados a azul.

Resultados offline no banco PLAYPAL 0:

- Erro médio dos 15 azuis em relação ao A2: 9,405 → 0,000 ΔE76.
- Diferença entre colunas nesses azuis: 0,000 ΔE76 no novo Hybrid.
- Isso é igualdade no modelo/CRAM normal, não uma medição de TV ou confirmação visual.
- As tintas PLAYPAL 1..13 têm erros diferentes, publicados no JSON; não alegar identidade em flashes/dano.

Custos: algumas entradas de CRAM e companions mudam; paredes/sprites do Hybrid são remapeados para minimizar a distância à aparência L3 com histograma proxy do WAD. A busca mudou 38 entradas do mapa PAL0 e 78 do PAL1. Distâncias médias ponderadas por esse proxy: 3,792 e 1,549 ΔE76 por banco. Esses números não são histograma de pixels medidos no jogo.

**A2 Full, L3 Detail e HN Smooth permanecem controles sem alterações cromáticas.** O Hybrid não deve ser apresentado como paredes L3 idênticas. A comparação real decide se a troca vale a pena.

## Cálculos de shadow/normal — sem highlight

Referência primária: Genesis_MiSTer, commit adc0c42cfb1fa5d484cc8566767f7d68982bc44a, rtl/vdp.vhd. Normal leva componente c de 3 bits à entrada DAC 2*c; shadow usa c. Isso não significa metade do brilho percebido na TV.

No universo inteiro de CRAM: 512 triplas normais + 512 shadow, com 64 em comum, resultam em **960 triplas digitais possíveis**, sem highlight. Não são 960 cores simultâneas nem uma paleta de seleção livre. A união dos níveis de um canal tem 12 valores, mas os três canais mudam de estado juntos; portanto não se pode elevar 12 ao cubo como se fossem independentes.

Por perfil, foram enumerados 15×15 = 225 pares opacos para cada estado NN, SS, NS, SN. O índice transparente 0 foi excluído, inclusive para A2. N/S refere-se à intensidade da coluna inteira, incluindo base e companion M50.

| Perfil | Médias M50 únicas NN | União NN+SS | Médias adicionais sobre NN |
|---|---:|---:|---:|
| Hybrid Blue+ | 189 | 376 | 187 |
| A2 Full | 203 | 399 | 196 |
| L3 Detail | 210 | 417 | 207 |
| HN Smooth | 210 | 417 | 207 |

São **médias ópticas candidatas** sob aproximação de luz linear/Lab; não contagem de cores físicas simultâneas. Os CSVs enumeram códigos, médias RGB, contraste ΔE e os melhores pares candidatos para cada azul.

NN/SS podem ser usados em regiões uniformes com uma máscara de prioridade adequada. Isso ainda não foi integrado ao renderer do mundo nesta versão. NS/SN exigiriam controle independente de intensidade entre metades de quatro pixels, que a organização Pair-V atual não fornece livremente.

No Pair-V, a prioridade de um tile transparente também participa da intensidade da outra metade. Por exemplo, com prioridade A[k], B[k-1], B[k], as metades recebem normal quando A[k] ou o respectivo B é alto. Não é possível repetir NS em todos os pares simplesmente atribuindo uma prioridade fixa a cada plano. Os números NS/SN no JSON são limite teórico de máscaras independentes, não funções já disponíveis.

## Validação / entrega

- Teste host compila os helpers reais de pedra/atributos; cobre palavras CRAM, equality de fundo e limites de glyphs.
- Controles A2/L3 comparados com CRAM, mapas, companions e LUTs compostas de origem.
- Guarda ROM 4 MiB e BSS 57.920 bytes mantida.
- Duas ROMs PLAY/PERF com HUD e seleção dos quatro modos.
- Smoke BlastEm previsto: 800 frames PERF; não cobre menu, troca de cores nem benchmark completo.
- Usuário valida fundo/legibilidade, ausência de retângulos claros, volta de H32/H40, título/partida, flashes e o novo piso azul. Nenhuma alegação de FPS sem benchmark físico.

Arquivos de cálculo: r77_profiles_report.json, r77_shadow_report.json, r77_shadow_pairs.csv e r77_blue_comparison.csv, incluídos nos artefatos por ROM.
