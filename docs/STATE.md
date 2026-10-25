# MD-DOOM64KB — estado do projeto (documento vivo)

Atualizado em 25/10/2026. Quem muda o estado atualiza este arquivo no mesmo PR. Fonte única para Claude, GPT e o dono.

## Objetivo de produto
Um DOOM jogável de ponta a ponta no Mega Drive real, rodando o máximo possível do código original, reconhecível visualmente e com geometria, colisão e gameplay corretos. A precisão matemática do rasterizador **não** é prioridade; a identidade visual e a jogabilidade são. Meta de referência: 8–10 FPS médios.

## Baselines e referências
| Nome | Branch / commit | FPS DEMO3 (2.134 quadros, H40, crop 16/16, 7,67 MHz) | Status |
|---|---|---:|---|
| R60 PairASM | `exp-r60-wall-pair-asm` `c670a08` | 6,72 | referência imutável |
| R64A | `exp-r60-r64a-prologue-memory-safe` `b6e7746` | 6,91 | referência imutável (precisão) |
| **R66** | `exp-r66-claudio-colpair` `f5a9daa` | **7,21** | **baseline vigente** (visualmente indistinguível da R64A) |

## Limites duros
BSS ≤ 57.920 B. ROM ≤ 4 MiB. Preservar kernel R60, Pair-V Fast, LUT composta, CM6/R59, menus, H32/H40, crop. ROMs de diagnóstico só no BlastEm, nunca como resultado de desempenho.

## Regras de aceite
1. Medir sempre com 3 repetições, mesmo clock, DEMO3 completo antes de afirmar ganho; prefixos (tic 64/128/256) só triam.
2. Qualidade visual é julgada pelo dono em movimento. **Ganho pequeno não compra perda visual perceptível.**
3. Aproximação aceita só com ganho material e imagem reconhecível; geometria, clipping, portas e gameplay não podem degradar.
4. Nada entra na baseline sem PR, README do experimento e veredito. Uma branch por experimento (`claude/…`, `gpt/…`).

## Registro de experimentos
| ID | Ideia | Resultado | Veredito |
|---|---|---|---|
| R64A | contexto por quadro hoistado no prólogo de `R42_DrawPackedWall` | +2,83% (6,72→6,91), framebuffer idêntico | aceito (referência) |
| R64D | contadores diagnósticos | achou B1/B2 ≈0,1–0,2% | encerrado |
| R65-P1 | corte precoce de parede | −0,72% | rejeitado |
| R65-P2 | frente fina de `R42_DrawPackedWall` | `moveml` continuou com 8 registradores (objdump) | **rejeitado**: critério de descarte atingido, sem FPS |
| R66 | par de colunas reaproveita textura/escala/fonte | **+4,34%** (6,91→7,21) | **aceito** |
| R67 | grupos de 4/8/16 colunas | +1,9% / +3,6% / +4,4% sobre R66 | **rejeitado**: perda visual perceptível crescente |
| R68 | log por quadro + amostrador de PC (diagnóstico) | em preparo, branch `claude/r68-profiling` | pendente de build e captura |

## O que aprendemos
- Setup de textura/recíproca já é pequeno: com o grupo de 16 quase todo o setup some e o ganho é só +4,4%. O tempo está em outro lugar (BSP, setup de segmento, sprites, lógica, desenho).
- `R_PointToAngle16` já usa DIVU em 16 bits; ~180 chamadas por quadro, teto de ganho ≈2%.
- O FPS médio é dominado pelos quadros lentos (mínimo 2,9, máximo 13 FPS em janelas de 1 s).

## Plano atual: qualidade adaptativa
Em vez de degradar a imagem sempre, degradar só os quadros pesados: um governador mede o custo do quadro anterior (VBlanks) e, acima de um limiar, o seguinte usa um nível mais barato (grupos de colunas, limite de sprites, corte de segmentos distantes, menos checagens de visão). Passos: (1) R68 mede distribuição de custo e a carga que explica os quadros lentos; (2) desenhar o governador e escolher níveis; (3) o dono julga os quadros em que ele atua.
Ideias de maior escala, depois dos dados: janela menor com resolução 2x2 (custo por amostra ainda não medido; ver experimento de tamanho de janela: FPS contra número de amostras em H40 sem crop, 8/8, 16/16, 24/24 e H32 16/16).

## Quem faz o quê
- Claude: patches, testes em host, modelos de custo, leitura dos dados devolvidos.
- Compilação, execução no BlastEm e hardware: CI/self-hosted e o dono; resultados voltam como comentário no PR.
