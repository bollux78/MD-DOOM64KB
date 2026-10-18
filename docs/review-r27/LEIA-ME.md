# R27 — custo da SRAM e agrupamento de acessos

Base R26, validada pelo usuário em funcionalidade: abertura, fases e músicas.
R26 episode-perf: 10,29 FPS / 207,33 s / 2134 frames.

Todas as ROMs de benchmark usam DEMO3 em E1M1. Todos os diagnósticos do
episódio têm os mesmos mapas completos e a mesma faixa E1M1 compilada.

## Ordem dos testes

1. `doom-md-r27-episode-perf.bin`: referência R26, trilha completa, acessos individuais.
2. `doom-md-r27-low-window.bin`: todos os mapas, apenas E1M1 musical, ROM até 2 MiB; alterna ROM/SRAM por acesso.
3. `doom-md-r27-low-fixed.bin`: igual à low-window, mas SRAM permanece habilitada. Esta comparação isola o custo da troca do mapper.
4. `doom-md-r27-group-side.bin`: trilha completa; agrupa offset e três texturas de cada lado de parede.
5. `doom-md-r27-group-line.bin`: trilha completa; agrupa flags/validade das linhas e atualização do automapa.
6. `doom-md-r27-group-perf.bin`: combina os dois agrupamentos, trilha completa.
7. `doom-md-r27-group-play.bin`: versão jogável da combinação, com abertura, seletor e trilha completa.

Também inclui `control` e `play-control`, os controles 8×8 da arquitetura antiga.
As duas ROMs low são diagnósticos; todas as solicitações de música nelas
apontam para a mesma E1M1. Não substituem a versão jogável com trilha completa.

## O que muda

Os grupos não mantêm SRAM aberta enquanto o jogo lê dados de mapas na ROM.
Copiam apenas os cinco bytes necessários do lado da parede para a pilha;
flags e contador de render são lidos/escritos na mesma transação quando possível.
O cálculo e a geometria permanecem os mesmos. Não há cache persistente novo.

A low-fixed só é aceita pelo auditor se a ROM inteira couber até 2 MiB.
Não use esse modo numa ROM maior: o WAD alto ficaria encoberto pela SRAM.
A SRAM continua com heads, estado dos mapas, contatos e cache em todas
as variantes do episódio. O teste não remove SRAM do jogo.

## Evidência e limites

O build confere payload de todos os mapas, DEMO3 e bytes compilados de E1M1
idênticos nas variantes. Os diagnósticos internos de CPU geram quadros em
18 carregamentos médio/difícil, permitindo comparar hashes e acessos ao mapper.
Testes de CPU não substituem o timedemo e a inspeção no hardware.
Anotar tempo, média, mínimo/máximo e qualquer diferença visual/sonora.

## Resultado interno desta build

Build das ROMs: 6ef1d1c959ee093be2fbb81b11faf9f54b458c6a.
CI: https://github.com/bollux78/MD-DOOM64KB/actions/runs/39136756073

Os 36 hashes de quadros (duas vistas em cada um dos 18 carregamentos)
foram idênticos entre baseline, agrupamento combinado e SRAM fixa.
Nenhum erro de heap ou acesso indevido à janela ROM/SRAM.

| Diagnóstico CPU | Ciclos dos 36 renders | Escritas do mapper no teste inteiro |
| --- | ---: | ---: |
| Baseline | 23672760 | 468950 |
| Agrupado | 23047024 | 465962 |
| SRAM fixa | 23454728 | 36 |

Agrupamento: 2.64% menos ciclos de render.
SRAM fixa: 0.92% menos ciclos de render.
Isso mede somente renderização nesses pontos, sem lógica do jogo, VDP ou Z80
concorrentes. As contagens do mapper também incluem os carregamentos.
Não converter estes percentuais em previsão de FPS do timedemo completo.
A comparação low-window × low-fixed no hardware ainda é necessária.

A variante fixa encerra o teste com SRAM habilitada; as outras restauram ROM,
como esperado. Não houve aumento de memória da zona nos agrupamentos.
