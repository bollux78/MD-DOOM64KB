# R105–R109: velocidade e assets (Cláudio para o Werk)

**Base atual do E1 shareware: R107 direct** (R105 twoface + colunas pré-montadas lidas direto da ROM).
Branch `exp-claudio-r107-direct-20261031`. Cadeia: … R98 sprmul → R100 (modo f1t) → R104 (SRAM com IRQ mascarada) → R107.

## Resultados (benchmark completo DEMO3 E1M1, AI Normal)
| ROM | BlastEm Off | BlastEm On | Console On | ROM usada |
|---|---|---|---|---|
| R104 mask (correção SRAM) | ~+0,9% sobre a R100 | — | — | 3,60 MB |
| R105 twoface (duas faces em 4 cópias) | — | 274,85 s | 276,77 s | 3,60 MB |
| R105 bits (muls 16 bits na lógica) | — | 277,53 s | — | descartada |
| **R107 direct** | **252,18 s** | **271,53 s** | **273,17 s** | 3.598.309 B |
| R108 halfwall (paredes meia altura) | +0,99% (A/B) | — | — | −151 KB |
| R109 halfsprite (sprites meia altura) | 252,85 s | 272,37 s | — | −130 KB |

## Decisões do usuário
- R107 direct é a base. Imagem idêntica à R105.
- **halfwall e halfsprite só nas ROMs do Doom registrado (E2/E3)**, como ferramenta de espaço. O E1 shareware fica com assets em altura cheia.
  A piora visual foi considerada insignificante (só em algumas texturas bem de perto).
- HUD e intermission nunca são reduzidos.
- Uma ROM por episódio. Sem Shadow (ou Shadow só R79) se algum episódio não couber.

## Notas técnicas
- A conversão herdada já guardava sprites com 1/2 largura e paredes com 1/4 largura; R108/R109 cortam a **altura**.
- Coordenadas do mundo (alturas, offsets, pegging) continuam em unidades cheias; só a amostragem cai pela metade:
  kernel `R108_WallColumn` (máscara 63, fase/passo >> 1), caminhos C `source[f>>10]`, posts mascarados com `<<1`
  na posição/texturemid, composição com `originy>>1`. O conversor roda depois dos geradores de cor
  (`build_r35_linear.fish`, após `r89_align_maps`), então as paletas não mudam.
- Meia altura não acelera: o custo é por pixel na tela. O ganho real veio de eliminar cópia/preparação (R107).
- Auditoria do WAD completo (R106): E2M7 tem 323 setores e E3M5 tem 268 (limite 254); o E2 usa 196 texturas
  e o E3 158 (limite 127); faltam no motor Cacodemon, Lost Soul, Cyberdemon, Spider, Plasma/BFG, chaves de
  caveira e várias decorações. O WAD completo fica fora do git, no runner; workflows só publicam números.
