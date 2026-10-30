# SH1 com pares protegidos — código para o Claudio avaliar

Estado: gerador experimental, sem integração, sem workflow e sem build de ROM.
Não altera nem substitui headers de produção. Mantém a CRAM SH1 e a decisão de
brilho compartilhada de cada bloco; propõe apenas novos códigos dos pares.

## Uso numa cópia descartável

Partir do build R91-SH1 A2/L3 **depois** de `gen_r91_shadow.py`, com os headers
reais e o relatório R79 gerados na mesma cópia:

```bash
python3 scripts/lab/test_r92_guarded_shadow.py
python3 scripts/lab/r92_guarded_shadow.py --out dist/sh1-guarded-review
```

Saídas: `r92_guarded_joint.h`, `changed-rows.csv`, `REPORT.json`.
A saída deve ser uma pasta nova. O gerador exige o hash original R89/R91 das LUTs
base e relatório SH1 (ganho 1,35), verifica a CRAM e o formato A2/L3 compacto.
Não aceita as LUTs de flats R90 rejeitadas. O parser aceita hex e decimal.

## Algoritmo

Para cada estado normal/sombra e cada par horizontal de códigos base, calcula:

- Cor efetiva base e SH1 considerando os parceiros M50.
- Suspeita de amarelo/clareamento introduzido, coloração de alvo neutro, ou
  contraste entre colunas maior que o contraste do alvo mais uma tolerância.
- Busca exaustiva dos 225 pares opacos possíveis **no mesmo estado de brilho**.

Só aceita alternativa quando nenhuma das duas amostras piora em dE76, no desvio
de luminosidade ou no desvio de croma; o contraste não aumenta e a alternativa
não dispara a heurística de bege. Exige melhora mínima no objetivo. Pares não
suspeitos e linhas com entrada transparente ficam como estavam. As metades
verticais são tratadas separadamente; atributos e estado do bloco permanecem
idênticos. A tabela final mantém 2 x 65.536 palavras longas (512 KiB).

Parâmetros de estudo: `--stripe-weight` (0,35) e `--min-gain` (1,0). Os limiares
heurísticos de bege estão na função `beige_bad` e precisam da revisão do Claudio.

## O que ainda NÃO está demonstrado

- O alvo é a cor já quantizada do R91-control, não a textura original do Doom.
- O modelo é o proxy RGB/Lab da R79, não o DAC medido nem uma simulação do CRT.
- As regiões marcadas pelo usuário ainda não foram correlacionadas aos códigos
  reais. A imagem sozinha não identifica todas as entradas.
- As restrições conservadoras podem deixar pares ruins sem correção. Como o
  estado de brilho é fixo, o gerador pode não encontrar alternativa aceitável.
- Não há prova visual de preservação dos detalhes cinza; há preservação exata
  das linhas não sinalizadas e restrições numéricas nas alteradas.
- Somente p=0 recebe a proposta. Efeitos p>0 continuam no fallback R79.

## Integração posterior, apenas se aprovada

Substituir o conteúdo de `r91_joint` pelo resultado aprovado ou redirecionar o
consumidor para a nova tabela, evitando manter as duas no binário. Não copiar
códigos SH2 para SH1: as CRAMs diferem. Não mudar a CRAM nem o kernel nesta
experiência de cores. Isso permite custo de execução igual em estrutura, mas o
benchmark continua necessário. O1/toggle/menu da R92 são trabalho separado.

Antes de integrar: gerar com headers reais, revisar CSV e quantidade de mudanças,
comparar capturas **depois** do passe, em especial porta/parede cinza e última
sala E1M1 (paredes e chão). Verificar A2/L3 separadamente, outras fases, sprites,
arma, marrons legítimos, verdes, vermelhos e pele. Aprovação final no CRT.

Testes executados localmente: caso dirigido de bege, proteção de pares aprovados
e transparência, 3.000 casos de restrições e comparação independente de todos
os 65.536 blocos empacotados. Sem execução do gerador com os headers reais nesta
entrega, sem alegação de correção visual ou de ganho de FPS.
