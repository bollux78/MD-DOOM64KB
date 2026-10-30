# R93c — teste do compromisso do Claudio

Duas PLAY sobre R92 recortada, ambas com menu normal e Shadow On/Off:

- r93c-reference: SH1 atual, referência.
- r93c-candidate: compromisso R93c do Claudio.

A2/L3, A2 inicial, AI Normal e Shadow Off por padrão. Para avaliar as cores
novas é necessário ligar Shadow em Options. Com Off, ambas usam as cores
normais do controle. Não inclui R93 do Werk nem busca livre/full do estudo.

Fonte exata: docs/analysis-r93b/R93C-COMPROMISE.json da branch
exp-claudio-r93b-cram-study-20261030, copiada para assets/r93c-compromise.json.
O gerador verifica as palavras SH1 anteriores e as palavras finais completas.
Só sete slots de CRAM p=0 mudam: quatro A2, três L3. Nenhuma palavra p>0 muda.
Mapas, custos e tabela conjunta são regenerados pela cadeia R79/R91. Não há
novas cópias de tabela no binário nem novo código no caminho de desenho.

## O que comparar

Mesmo modo de cor, recorte e Shadow On nas duas. Conferir especialmente:

- Porta e paredes cinza: detalhes que o usuário gostou na SH1.
- Faixas bege/escuro, paredes e chão da última sala de E1M1.
- Pele, vermelhos, verdes, marrons legítimos, arma e HUD.
- Troca A2/L3, On/Off e flashes de dano/coleta (p>0 usa SH1 original).

O benchmark deve usar AI Normal, mesmo modo de cor, mesmo recorte e mesmo
estado de shadow. A alteração é nos dados; medir para conferir o resultado.

## Limitações explícitas

Esta candidata é um compromisso, não uma correção aprovada. Viola as guardas
estritas em dois códigos de luminosidade no A2 e quatro códigos no L3
(luminosidade/matiz/croma); o maior grupo afetado no L3 representou 10,4% das
amostras da captura estudada. A captura do Claudio cobriu tics 2..704, não a
última sala de E1M1. Os pesos não cobrem justamente essa cena crítica.
As métricas LIN/HW são modelos, não medição do CRT. A aprovação é visual.

## Validação automática

Teste local com LUTs reais: exatamente sete slots p=0 alterados, p>0 e modos
inativos intactos, testes C R79 e testes exaustivos/C R91 aprovados. O runner
repete a geração/validação com tabelas reais, confere ROM/BSS e save/load
E1M1/E1M7. Captura de inicialização é pré-passe e com Off padrão; não equivale
à comparação visual pós-passe com On. A verificação pós-passe das cenas acima
continua necessária. O ponto R92_AfterPass existe, mas só é atingido quando o
caminho de gameplay/presentação roda; o PLAY inicial pode estar no menu.

Pacote: R93C-CRAM-ROMs.zip. Não usar o r92-full como referência de desempenho
para esta rodada: ambas as R93c usam O1/recorte e o mesmo toggle.
