# SH1: CRAM re-quantizada com tabelas reais

Estudo offline executado sobre r59_color_tables.h original SHA-256
38b4319bce37ac31164b757bd8525cf4d71015873b697d61c1aca6a6f1eb03cc,
extraído do artefato R92 (run 40983021976, variante full). A base é a mesma
R89/R91 validada pelo Claudio. Nenhuma ROM foi criada; o build R92 não muda.

## Resultado medido do gerador

| Perfil | Cores CRAM alteradas p=0 | Entradas conjuntas alteradas | Estados de sombra alterados |
|---|---:|---:|---:|
| A2 | 6 | 38.440 | 10.190 |
| L3 | 4 | 31.285 | 5.276 |

As contagens são enumeração não ponderada das 65.536 chaves possíveis, não
frequências de pixels/cenas reais. Ao incluir os 14 efeitos de paleta, são
67 e 66 palavras de CRAM alteradas, respectivamente. O índice transparente 0
é preservado como na SH1 atual, em todos os efeitos. Os slots cinza de p=0
não mudaram; isso NÃO prova a preservação visual dos detalhes, porque o
remapeamento e o estado do bloco também podem mudar.

O marrom original (3,2,1), hoje SH1 (4,3,1), torna-se (4,3,2) nos slots
A2 pal0#2/pal1#12 e L3 pal0#2/pal1#14. A2 pal1#7, original (4,2,1),
passa do SH1 (5,3,1) para (6,3,2). São componentes de CRAM de 3 bits.

## Objetivo explícito

Normal: ideal contínuo min(255, original x1,35).
Sombra: metade desse ideal. Busca nas 512 palavras, minimizando o erro
Lab quadrático ponderado dos dois estados. Pesos 0,5/0,5 são uma hipótese,
não uso medido. Mantém o propósito do ganho SH1, sem tentar igualar normal
e sombra ao mesmo alvo original. Há guardas de matiz/luminosidade/neutros,
mas seus limites continuam hipóteses de estudo. O proxy é o R79 sRGB/Lab,
não DAC medido do Mega Drive nem simulação do CRT.

Depois da quantização, o R79 foi executado novamente para recalcular códigos,
custos e decisões, seguido do R91 para a tabela conjunta. Os geradores de
produção não foram editados: uma cópia temporária substitui exclusivamente
a atribuição de CRAM A2/L3. A CRAM Hybrid não muda; HN segue L3 e não é usado.
Não há reaproveitamento da refit de pares que produziu zero mudanças.

## Reprodução

```
python3 scripts/lab/r93_cram_evaluate.py --tables CAMINHO/r59_color_tables.h --out dist/cram-review
```

Pasta de saída deve ser nova. Requer NumPy e compilador C de host.
Gera baseline/candidate com r79_shadow_tables.h completos, relatórios, logs,
slots.csv e SUMMARY.json. Os headers candidatos incluem mapas para todos os
14 efeitos; a tabela conjunta p=0 permanece com 512 KiB. Não compila ROM.
Os testes R79 reais passam nos 4 perfis x14 efeitos e os testes R91 passam
nos dois caminhos, incluindo 80 comparações de framebuffers em C para cada um.
Isso valida a consistência das tabelas com o algoritmo, não melhora visual.

Arquivos anexados no repositório:
- docs/analysis-r93/CRAM-SUMMARY.json
- docs/analysis-r93/CRAM-CANDIDATE.json (paletas apenas)
- docs/analysis-r93/CRAM-SLOTS-P0.csv (todos os slots p=0, incluindo inalterados)

## Avaliação seguinte

Claudio: revisar objetivo, limites, slots e contagens antes da integração.
Se aprovada para teste, substituir os dados gerados no build SH1, mantendo
O1/toggle/menu da R92. Evitar inserir cópias original e candidata juntas.
Comparar imagens pós-passe, mesmos tics/enquadramentos, A2 e L3, nas portas,
paredes cinza e última sala de E1M1 (chão e paredes). Testar outras fases,
marrons legítimos, pele, verdes e flashes de dano/coleta. Avaliação final no CRT.
Custo do loop não muda em estrutura; FPS e preservação dos detalhes ainda
precisam de teste. Não afirmar que o bege foi corrigido antes dessa avaliação.
