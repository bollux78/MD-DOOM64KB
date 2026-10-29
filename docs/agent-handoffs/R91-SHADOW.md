# R91 — experimento de Shadow/Highlight rápido

Base: R90-control (sem flats novos), todas as otimizações da R89-all, AI Normal
por padrão. Somente A2 e L3 em Options, A2 inicial. As tabelas de cores base
permanecem intactas; as candidatas S/H usam o remapeamento experimental R79.
Não inclui a alternância temporal de CRAM em desenvolvimento pelo Claudio.

## Três PLAY

- r91-control: base sem S/H no jogo, com menu A2/L3.
- r91-sh1: S/H R79 de intensidade 1, decisões conjuntas pré-calculadas.
- r91-sh2: S/H R79 de intensidade 2, decisões conjuntas pré-calculadas.

Esta é uma alternativa ao kernel integrado, não uma implementação de sombra
independente por amostra. No Pair-V, a prioridade de A afeta o bloco conjunto.
Modificar esse atributo durante uma coluna pode alterar outra superfície.
Para preservar a decisão conjunta, ainda há uma passagem final, antes de
publicar o framebuffer. O cálculo de custos foi removido do caminho normal.

## O que muda

Cada par de bytes A/B indexa uma tabela ROM de 65.536 palavras longas. O valor
contém os dois tiles finais, com códigos e prioridade. Duas tabelas (A2/L3)
usam 512 KiB extras de ROM, sem novo buffer ou estado em WRAM. Para flashes de
dano/coleta e outras paletas p>0, usa-se o caminho original R79, pois tabular as
14 paletas excederia o orçamento de ROM. Não há promessa de custo zero ou ganho
sobre o controle; isso deve ser medido.

As candidatas são visualmente equivalentes ao pós-processamento R79 na paleta
normal, não uma nova quantização de texturas. Elas preservam suas limitações de
brilho compartilhado por bloco 8x8 e aproximação dos códigos já quantizados.
O objetivo é medir se o mesmo efeito agora fica barato o suficiente.

## Testes

O gerador compara exaustivamente 131.072 decisões (todas as combinações A/B nos
dois modos) com a fórmula R79. Compila o código C real e compara 80 framebuffers
com a rotina anterior, incluindo bordas e sentinelas. Isso ocorre após gerar
as tabelas reais no runner. Os testes locais verificam aplicação dos patches,
seleção A2/L3 e AI Normal.

O workflow confere limite de 4 MiB de ROM e BSS <=57.920, exige BSS igual entre
as variantes, testa save/load em E1M1/E1M7 e captura inicialização/gameplay.
O pacote é R91-SHADOW-ROMs.zip, com três ROMs e este documento.

Faça benchmarks E1M1 e E1M7 em AI Normal e no mesmo modo de cor. No CRT, confira
bordas entre superfícies claras/escuras, inimigos, arma, grades, HUD, menu,
retorno ao jogo, flashes de dano/coleta, troca A2/L3, mudança de fase e save/load.
Apenas os benchmarks e a avaliação visual podem aprovar uma candidata.
