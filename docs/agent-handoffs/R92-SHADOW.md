# R92 — SH1 com recorte e On/Off

Base R91 com correções dos testes de seleção A2/L3 e leitura dos mapas do
arquivo da ROM (Claudio). As cores de gameplay são as da SH1 atual, com seus
pontos fortes e o problema conhecido do bege. AI Normal, A2 inicial, L3 opcional.

Duas PLAY, ambas com Shadow Off por padrão:

- r92-full: toggle, menu normal e conversão completa R91 como referência.
- r92-toggle: toggle, menu normal e conversão recortada O1.

No menu Options: Shadow On/Off. A escolha permanece durante a sessão, não é
armazenada no save. O benchmark mostra SHADOW ON/OFF. Compare os dois estados
na mesma ROM e a mesma configuração de cor, recorte, áudio e AI Normal.

O retângulo de tiles é capturado em I_FinishUpdate e compartilhado entre o DMA
e a conversão O1. O fallback para paletas de efeitos também é recortado em O1.
O desligamento restaura os atributos A/B, sem apagar códigos. A atualização de
CRAM usa a seleção normal/esticada e o índice de efeito vigente. O menu nunca
liga S/H e usa a pedra do HUD; índice15 reservado para texto branco. O teste
pós-geração rejeita uma pedra que use esse índice com outra cor.

R92_AfterPass é um ponto estável para capturar o framebuffer após a conversão.
r70_capture.py aceita --break-symbol R92_AfterPass. A captura de inicialização
é com o padrão Off; não prova a transição nem equivalência de On no emulador.

Validação local: aplicação da cadeia de patches, comparação do código C do
passe com o comportamento integral dentro de vários retângulos, exclusão dos
tiles fora da janela e fallback. Runner: tabelas/ROM/BSS, menu pós-geração,
save/load E1M1/E1M7 e capturas pós-passe com configuração inicial.

Ainda requer avaliação: On/Off repetido, inclusive flashes de dano/coleta,
retorno do menu, troca A2/L3, H32/H40, mudanças de recorte e comparação de On
entre full/toggle no mesmo tic. No CRT: detalhes, bordas, arma, HUD e legibilidade
da pedra. Não há alegação de ganho medido ou validação completa das transições.

## Estudo separado da CRAM

O script r92_cram_study.py não participa do build. Uso com as LUTs reais:

```
python3 scripts/lab/r92_cram_study.py --tables src/r59_color_tables.h --out dist/cram-study
```

Produz candidate-palettes.json e slots.csv. Alvos explícitos: normal = ideal
contínuo original x1,35, limitado a 255; sombra = metade desse ideal. Pesos
normal/sombra iguais são uma hipótese, não uso medido. Busca 512 palavras com
restrições de matiz/luminosidade. Não recalcula ainda mapas/custos/estados nem
conta blocos alterados. Deve ser revisado pelo Claudio antes dessa próxima
etapa e antes de entrar em qualquer ROM. O modelo continua sendo o proxy R79.
