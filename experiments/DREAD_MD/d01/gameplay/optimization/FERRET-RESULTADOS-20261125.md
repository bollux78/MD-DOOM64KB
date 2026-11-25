# C7 — resultado dos experimentos Ferret (2026-11-25)

Execução: https://github.com/bollux78/MD-DOOM64KB/actions/runs/45543891282
Commit compilado: 50dff70b06d89a29ae602469e8420c3b7ef6d2e2
Base: 114a4147073c7c7ce3aa314d2ad93b57d2a15bae, mantendo as grades otimizadas.

As quatro compilações, os quatro benchmarks e o empacotamento terminaram com sucesso. Cada ROM tem 4194304 bytes. Não houve promoção para a versão estável.

## Medição

MAME genesis (NTSC), frequência medida 59,922743404 Hz, primeiros 312 quadros da DEMO3/E1M7. Mesmo WAD, geometria, IA e configuração inicial da rodada.

| Variante | FPS sem IA | VBlanks sem IA | Diferença | FPS com IA | VBlanks com IA | Diferença |
|---|---:|---:|---:|---:|---:|---:|
| CONTROL | 3,6487 | 5124 | referência | 3,3547 | 5573 | referência |
| CACHE2 | 3,6127 | 5175 | -0,99% | 3,3249 | 5623 | -0,89% |
| SPARSE | 3,6092 | 5180 | -1,08% | 3,3225 | 5627 | -0,96% |
| FERRET_ALL | 3,5741 | 5231 | -2,04% | 3,2927 | 5678 | -1,85% |

CACHE2 usa cache de vértices de duas vias na mesma capacidade de 256 entradas. SPARSE prepara somente runs de colunas abertas no caminho nativo, com limites para amortizar setup. FERRET_ALL combina ambos. São adaptações experimentais, não código copiado da ROM Ferret.

## Imagem e limites

Todas as variantes experimentais tiveram hashes finais diferentes do CONTROL nos dois modos. Portanto o gate de igualdade da imagem final falhou e nenhuma variante foi validada como exata. Essa diferença não foi localizada visualmente nesta rodada; o hash de tela inclui HUD/efeitos e, sozinho, não demonstra erro de geometria. A igualdade de todos os quadros/mapas não foi testada.

O preflight do código real do cache passou em milhões de pares de endpoints com colisão. Também passou a checagem da equivalência modular das alturas ao reiniciar interpolantes. Isso não substitui os resultados do emulador.

Os três experimentos foram mais lentos nesta cena; não há melhoria de desempenho demonstrada por estas adaptações. O custo extra de busca/manutenção do cache e de identificação/reinício dos runs é uma hipótese para a regressão, não um custo inclusivo isolado medido. Não extrapolar o resultado para todas as técnicas do Ferret ou todas as vistas.

## Decisão

Manter a C7 base com grades otimizadas como referência. Preservar estas ROMs somente como experimentos para estudo. O ZIP da execução contém as quatro ROMs, hashes SHA256, metadados, relatórios de geometria e resultados CSV/JSON.

SRAM não foi habilitada nesta rodada. Seu possível uso para liberar RAM interna exige experimento separado e verificar o mapeamento com a ROM de 4 MB; não se deve transferir à C7 o ganho que o Ferret obtém ao trocar escrita direta no VDP por buffer/DMA.
