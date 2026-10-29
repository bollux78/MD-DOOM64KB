# R89: renderer e outros processos

Base aprovada: `542501f7c516a56c60899e22cf1e9f6ef5a2e4ac` (R89, AI Normal/Low).
Branch de experimentos: `exp-chatgpt-r89-renderer-routes-20261029`.

Todas as ROMs são PLAY, com AI Low por padrão e seleção Normal/Low preservada.
Color mode é a segunda opção do menu de Start; use esquerda/direita. O atalho
em Options permanece. A tela do jogo continua congelada durante o menu.
As ROMs PERF históricas não são substituídas.

## ROMs

O arquivo `R89-ROMs.zip` reúne as nove ROMs e este guia.

| Sufixo | Alteração sobre a R89 |
|---|---|
| control | Somente o atalho de cores compartilhado por todas |
| cull | Rejeita sprites inteiramente nas margens recortadas antes de consumir uma vaga |
| clip | Limita as colunas examinadas no recorte de sprites à janela visível |
| cache | Reconhece a última coluna em RAM antes de pesquisar a tabela do cache |
| rom | Lê colunas completas diretamente da ROM nos acertos de cache, preservando seu histórico |
| map | Alinha registros de paredes em 32 bytes na ROM, mantendo todos os campos |
| spatial | Agrupa teste e marcação das linhas visitadas em uma janela de acesso à SRAM |
| video | Reduz a preparação dos registradores e dos endereços das transferências ao VDP |
| all | Combina os sete experimentos |

Não há vhalf, farwalls nem céu fixo. A IA não foi modificada nesta rodada.
`all` é experimental: ganhos isolados não garantem que a soma seja mais rápida.

## Comparação

1. Reinicie cada ROM para partir dos mesmos padrões (AI Low, H40, recortes 16/16).
2. Execute Benchmark → E1M1 e Benchmark → E1M7.
3. Mantenha o mesmo perfil de cores, recorte, áudio e modo de IA em todas.
4. Registre FPS médio, mínimo e máximo, tempo total e quadros. Ganhos muito
   pequenos merecem repetição, especialmente contra o novo `control`.
5. Confira sprites perto das bordas, inimigos atrás de grades, portas,
   elevadores, projéteis, colisões, save/load e mudanças de fase.
6. Em `video` e `all`, confira também a imagem no Mega Drive real: testes do
   cálculo dos endereços não substituem a verificação do VDP.

## Implementação e evidências

Sequência: R81 → R80 P1+F1 → R83 sprites → R85 all → R88 ai → R89 →
`R89_ROUTE=<sufixo> python3 scripts/lab/apply_r89_routes.py`.

`test_r89_routes.py` monta todas as variantes e verifica:

- 49.788 chamadas ao código C real de composição/cache, com repetições,
  colisões, substituições, colunas incompletas e cópias curtas; pixels,
  SRAM e tags idênticos ao controle.
- 5.000 cenas com o código C real de recorte de sprites, até 64 segmentos:
  recorte visível e ordem das paredes transparentes idênticos.
- Os nove mapas mantêm cada campo original. O alinhamento adiciona 7.472
  bytes ao WAD convertido; não cria uma segunda cópia dos mapas em RAM.
- ABI das paredes: tamanho 32, tag no offset 26 e especial no offset 30.
- Teste/marcação da SRAM: 2.048 linhas, visitas repetidas, campos vizinhos
  intactos e abertura/fechamento balanceados do mapeador.
- Interseções do recorte, avanço das origens de DMA e IA idêntica à R89.

O workflow verifica limites de ROM/BSS, captura a inicialização de cada PLAY
no BlastEm e executa save/load em E1M1/E1M7 nas variantes map/all. Os resultados
reais desses testes ficam no artefato da execução; esta documentação não é uma
alegação de aprovação antecipada do runner nem de ganho de FPS.

A opção `rom` mantém as escritas do cache SRAM nos misses. Nos hits seguros,
o conteúdo lógico do buffer pode permanecer em ROM até uma coluna parcial
precisar dele. Não lê ROM através da janela SRAM habilitada.

A opção `cull` pode permitir que um sprite visível antes excluído pelo limite
de oito vagas apareça, pois sprites das margens deixam de consumir vagas.
Isso é uma correção de seleção, não uma promessa de framebuffer idêntico.

A opção `map` muda apenas o formato imutável na ROM. O estado mutável na SRAM,
a numeração das linhas e o codec de save permanecem iguais. O teste de save do
runner usa o stride correto para cada variante.

A opção `video` depende do formato Pair-V e do framebuffer contido na WRAM;
o build rejeita outros formatos. Os benchmarks continuam sem instrumentação
extra de desempenho.
