# Revisão do Cláudio: "SH1 com pares protegidos" (Werk, `review-chatgpt-sh1-guarded-20261030`)

Rodei o gerador do Werk com as tabelas reais da R91-SH1 (`r59_color_tables.h` sha `38b4319b…`, saída do run 40965815781). Gerei `gen_r79_shadow.py --strength 1` e `gen_r91_shadow.py` numa cópia descartável. Nada foi integrado e nenhuma ROM foi criada.

## Opinião 1 — Como está, o gerador não muda nada (resultado medido)

```
test_r92_guarded_shadow.py : PASS (testes sintéticos, 1670 mudanças)
r92_guarded_shadow.py      : changed_rows 0, changed_blocks [0, 0]
```

O motivo é matemático, não um bug:

- O R79 escolhe cada código, por amostra e por estado, como o **argmin do dE** contra o mesmo alvo e com o mesmo proxy (`to_lab`/`avg_rgb` do `gen_r52_claudio`, CRAM esticada, parceiros M50). Conferi: nos 4 casos (A2/L3 × normal/sombra), os 30 códigos atuais são exatamente o argmin por amostra (30/30).
- A guarda do Werk exige `ea <= olderr[0]` **e** `eb <= olderr[1]`. Com o código antigo já sendo o mínimo de cada amostra, só um empate passaria. Portanto nenhuma alternativa pode ser aceita, por construção.
- Os testes do Werk passam porque usam cores sintéticas, onde o código antigo não é ótimo. Isso não representa a tabela real.

O problema existe e o detector dele o vê: **142/225 linhas suspeitas no A2 normal (56 com bege), 126/225 no L3 normal (56 bege)**; no estado sombra só 16 e 24. Mas, dentro desse modelo, a cor bege já é a "melhor" possível, então o defeito não está na escolha dos pares.

## Opinião 2 — A causa provável é a CRAM esticada; corrigir lá

O bege aparece quase só no estado **normal**, que mostra a CRAM esticada ×1,35. O esticamento hoje é por canal, com arredondamento: `min(7, floor(c*1.35+0.5))`. Na grade de 3 bits, isso puxa os marrons para amarelo:

| Slot | Original | Esticado hoje | Mudança de matiz | Croma | L |
|---|---|---|---|---|---|
| A2 pal0 #2, A2 pal1 #12, L3 pal0 #2, L3 pal1 #14 | (3,2,1) | (4,3,1) | **+14° (amarelo)** | ×1,49 | +14 |
| A2 pal1 #7 | (4,2,1) | (5,3,1) | **+14°** | ×1,24 | +14 |

O G passa de 2 para 3 (×1,5) enquanto o R passa de 3 para 4 (×1,33). O marrom do Doom vira bege-amarelado, e isso nos tons mais usados de E1M1 (paredes, portas, chão marrom). Saturação no 7 quase não acontece (só L3 pal1 #3 e #6), então o problema é o arredondamento, não o limite.

Escolhendo a palavra pela distância Lab ao ideal ×1,35, em vez de canal a canal, existem opções melhores. Por exemplo, para (3,2,1) a mais próxima é (4,3,2), com +2° de matiz em vez de +14°. Para (4,2,1), (6,3,2) dá −7° e (5,2,1) dá −6°, contra +14° hoje. Isso é proxy sRGB/Lab, não DAC medido.

**Proposta (substitui a refit de pares):**

1. **Re-quantizar a CRAM SH1 por Lab, slot a slot**, no `gen_r79_shadow.py`. Para cada slot, escolher entre as 512 palavras a que minimiza o erro **nos dois estados**: normal = palavra, sombra = palavra/2, cada um contra o alvo original e ponderado pelo uso dos blocos. Preservar matiz e croma como guardas, no espírito da R90 rodada 5: nunca virar cinza claro, |ΔL| e matiz limitados.
2. Rodar o R79/R91 normalmente sobre a CRAM nova: códigos, custos e **decisão de estado** são recalculados de forma consistente. A tabela conjunta continua com 512 KiB, e o custo de execução é idêntico (só muda o conteúdo das tabelas).
3. **Opcional, se ainda sobrar bege:** no custo da decisão normal/sombra (`cost`), somar uma penalidade de desvio de matiz para alvos marrons e neutros. Assim o bloco pode escolher o estado sombra, mais escuro mas com o matiz certo. A versão do Werk mantém o estado fixo, e isso tira justamente essa saída.
4. Se quiserem manter a refit de pares como segunda etapa, a guarda precisa mudar de "nenhuma amostra piora em dE" para um objetivo explícito, por exemplo dE + peso × erro de matiz/croma, com tolerância de dE. Senão ela continua sem efeito.

**Pontos menores do código do Werk** (se ele seguir com a refit de pares):

- O contraste entre colunas só considera A(x)↔B(x), o par dentro da chave. O vizinho da esquerda de A(x) é B(x−1), que está em outro bloco e fica fora da avaliação.
- `beige_bad` tem limiares fixos (+8 em b*, +6 em L, croma > 18), sem calibração. Como detector para o relatório serve; como critério de aceitação é frágil.
- A verificação de identidade da tabela (`rewrite_table` com as linhas originais reproduzindo `r91_joint`) é boa e vale manter em qualquer variante.

## Ordem que eu sugiro

1. Primeiro, o trabalho já aprovado da R92: O1 (recorte compartilhado com o DMA) + Shadow On/Off + menu sem S/H. Isso não depende da cor.
2. Em paralelo, gerar só as tabelas da **CRAM SH1 re-quantizada** (sem ROM) e um relatório por slot: matiz, croma e L antes/depois, e quantos blocos mudam de estado.
3. Com a aprovação do usuário, uma ROM SH1 com a CRAM nova, comparada contra a SH1 atual nas mesmas regiões que ele marcou (porta/parede cinza e a última sala de E1M1), sempre com captura **depois** do passe. A palavra final é do CRT.
