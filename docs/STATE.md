# MD-DOOM64KB — estado do projeto (documento vivo)

Atualizado em 25/10/2026. Fonte única do estado atual. Quem muda o estado atualiza este arquivo no mesmo PR.

## Objetivo de produto
Um DOOM jogável de ponta a ponta no Mega Drive real, rodando o máximo possível do código original, reconhecível visualmente e com geometria, colisão e gameplay corretos. A precisão matemática do rasterizador **não** é prioridade; a identidade visual e a jogabilidade são. Meta de referência: 8–10 FPS médios.

## Baselines e referências
| Nome | Branch / commit | FPS DEMO3 (2.134 quadros, H40, crop 16/16, 7,67 MHz) | Status |
|---|---|---:|---|
| R60 PairASM | `exp-r60-wall-pair-asm` `c670a08` | 6,72 | referência imutável |
| R64A | `exp-r60-r64a-prologue-memory-safe` `b6e7746` | 6,91 | referência imutável (precisão) |
| **R66** | `exp-r66-claudio-colpair` `f5a9daa` | **7,21** | **baseline vigente** (visualmente indistinguível da R64A) |

Regras permanentes (limites de BSS/ROM, regras de aceite, branches, CI, handoffs): ver [`AGENTS.md`](../AGENTS.md).

## Registro de experimentos
| ID | Ideia | Resultado | Veredito |
|---|---|---|---|
| R64A | contexto por quadro hoistado no prólogo de `R42_DrawPackedWall` | +2,83% (6,72→6,91), framebuffer idêntico | aceito (referência) |
| R64D | contadores diagnósticos | achou B1/B2 ≈0,1–0,2% | encerrado |
| R65-P1 | corte precoce de parede | −0,72% | rejeitado |
| R65-P2 | frente fina de `R42_DrawPackedWall` | `moveml` continuou com 8 registradores (objdump) | **rejeitado**: critério de descarte atingido, sem FPS |
| R66 | par de colunas reaproveita textura/escala/fonte | **+4,34%** (6,91→7,21) | **aceito** |
| R67 | grupos de 4/8/16 colunas | +1,9% / +3,6% / +4,4% sobre R66 | **rejeitado**: perda visual perceptível crescente |
| R68 | log por quadro + amostrador de PC (diagnóstico) | pronto para revisão, branch `exp-claudio-r68-profiling-20261025`; sem compilação m68k nem captura ainda | pendente de build e captura |

## O que aprendemos
- Setup de textura/recíproca já é pequeno: com o grupo de 16 quase todo o setup some e o ganho é só +4,4%. O tempo está em outro lugar (BSP, setup de segmento, sprites, lógica, desenho).
- `R_PointToAngle16` já usa DIVU em 16 bits; ~180 chamadas por quadro, teto de ganho ≈2%.
- O FPS médio é dominado pelos quadros lentos (mínimo 2,9, máximo 13 FPS em janelas de 1 s).

## Hipótese experimental: qualidade adaptativa (NÃO é decisão de implementação)
Hipótese: o FPS médio é dominado por poucos quadros pesados (mínimo 2,9, máximo 13 FPS em janelas de 1 s), então uma redução de custo aplicada **só** a esses quadros poderia elevar o FPS médio com pouco efeito visual. Nada disso está decidido nem autorizado.
- A rejeição da R67-G4/G8/G16 **continua válida** e não autoriza reutilizar grupos maiores de colunas nos quadros lentos. Os níveis de redução, se vierem a existir, não estão definidos e podem nem envolver textura.
- Qualquer redução adaptativa precisa demonstrar ganho relevante com medição e ser submetida à avaliação visual do mantenedor antes de qualquer promoção.
- Primeiro passo, só diagnóstico: R68 (`exp-claudio-r68-profiling-20261025`) mede a distribuição de custo por quadro, a carga que a explica e o perfil de funções nos quadros lentos e rápidos. Os dados podem apontar para otimizações sem perda visual, preferíveis a qualquer degradação.
- Hipótese de escala maior, depois dos dados: janela menor com resolução 2x2. O custo por amostra ainda não foi medido (experimento sugerido: FPS contra número de amostras em H40 sem crop, 8/8, 16/16, 24/24 e H32 16/16).

## Quem faz o quê
- Claude: patches, testes em host, modelos de custo, leitura dos dados devolvidos.
- Compilação, execução no BlastEm e hardware: CI/self-hosted e o dono; resultados voltam como comentário no PR.
