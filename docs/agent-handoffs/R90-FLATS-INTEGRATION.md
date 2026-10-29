# R90 flats — integração sobre R89-all

Duas ROMs PLAY: `r90-control-pl` e `r90-flats-pl`.
Ambas usam todas as sete otimizações aprovadas da R89-all, AI Normal por padrão
(Low opcional) e o menu original de Options da cadeia R88/R89. O atalho incorreto
na primeira camada foi removido. Os quatro modos permanecem: Hybrid Blue, A2,
L3 e HN. Uma futura R91 poderá reduzir os modos após avaliação do usuário.

A diferença entre as duas ROMs é exclusivamente o conteúdo dos oito arrays de
flats fornecidos pelo Claudio, além da identificação do build. CRAM, pares M50,
paredes, sprites e HUD não são alterados. Não há pré-conversão de texturas nem
novo kernel Pair-V nesta rodada.

Fonte: https://github.com/bollux78/MD-DOOM64KB/blob/exp-claudio-r90-palmap-analysis-20261029/docs/analysis-r90/R90-HANDOFF-FLATS-CLAUDIO.md

O hook roda depois dos geradores e testes originais R77. Exige o SHA-256
`38b4319bce37ac31164b757bd8525cf4d71015873b697d61c1aca6a6f1eb03cc` antes de alterar
qualquer byte; exige oito âncoras únicas e 256 códigos 1..15 por array. A máscara
dos oito corpos deve deixar todo o restante do arquivo byte-idêntico.
O controle também verifica o hash, sem modificar a tabela.

## Teste pelo usuário

- Compare os quatro modos pelo menu Options, sobretudo chão/teto e faixas.
- Confira paredes, inimigos, objetos, HUD, mudanças de fase e save/load.
- Benchmark E1M1/E1M7 com AI Normal e as mesmas configurações em ambas.
- A revisão visual final deve ser no CRT.

## Evidência automática e limites

O workflow verifica ROM/BSS, exige BSS igual, testa save/load em E1M1/E1M7 e
captura os framebuffers das duas PLAY no mesmo job. O relatório compara os tics
em comum e fornece as capturas brutas. Não há máscara de propriedade de pixel;
portanto o relatório NÃO certifica automaticamente que toda diferença de imagem
é chão/teto. Essa parte do handoff ainda requer inspeção visual. A garantia
estrutural automatizada é de que somente os oito arrays autorizados mudaram.
Não se alega ganho ou ausência de perda de FPS antes dos benchmarks.

O pacote R90-ROMs.zip contém as duas ROMs e este guia. O artefato completo inclui
headers gerados, hashes, relatórios de memória, save/load e capturas.
