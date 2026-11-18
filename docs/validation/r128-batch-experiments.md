# R128 Shareware — testes de otimização em lote

Base com nova amostragem tonal, verdes da armadura e preto restaurado. Arma desenhada no viewport.

| ROM | Alteração | BSS adicional |
|---|---|---|
| control | Controle | 0 B |
| block | Cache de 8 cabeçalhos do blockmap, escrita imediata na SRAM | 48 B |
| nodes | Cinco campos de vínculos objeto/setor lidos em uma janela SRAM | 0 B |
| shot | Reaproveitamento da origem vertical dos tiros com validação da posição e altura | 24 B |
| openings | Última abertura consultada, validada pelas alturas atuais dos setores | 32 B |
| effects | Sangue omitido e fumaça de impacto limitada a 192 unidades | 0 B |
| all | Cinco alterações combinadas | 104 B |

## Medições no Genesis Plus GX

Cada teste cobre 2400 atualizações NTSC, cerca de 40 segundos. Entrada igual por tempo emulado. As simulações podem divergir quando o número de quadros muda. O teste de disparos inclui a morte do jogador e deve ser tratado como cenário limitado. Uma janela adicional de 720 atualizações testa o início dos disparos.

| Variante | E1M1 parado | E1M2 disparando | E1M3 girando |
|---|---|---|---|
| control | 4.419 | 2.547 | 6.716 |
| block | 4.419 | 2.522 | 6.716 |
| nodes | 4.419 | 2.497 | 6.716 |
| shot | 4.419 | 2.522 | 6.716 |
| openings | 4.419 | 2.522 | 6.716 |
| effects | 4.419 | 2.522 | 6.716 |
| all | 4.419 | 2.522 | 6.716 |

Os testes não demonstraram aumento consistente de FPS. As diferenças em E1M2 foram pequenas e algumas variantes renderizaram menos quadros.

As seis variantes modificadas abriram E1M1–E1M9 e responderam ao movimento. A cache do blockmap passou por 500000 acessos comparados com a memória subjacente, com colisões de entradas, valores nulos, escrita e reinicialização entre níveis. A combinação usa 58134 bytes de BSS, 104 bytes adicionais.

A supressão de cada efeito mantém os quatro sorteios de sua criação. A remoção altera a população de objetos e pode afetar a simulação posteriormente. O limite de 192 unidades é uma escolha inicial para teste visual. A cache de tiros cobre apenas o cálculo da altura de origem. Cada projétil mantém sua trajetória e seu dano.

O encerramento antecipado de tiros, a remoção de cadáveres e o teste/marcação de linhas em uma janela SRAM já faziam parte da base.

## Reprodução

Use o construtor scripts/lab/build_r128_shareware.sh com o DOOM1.WAD shareware esperado e o SGDK compatível. Defina R128_TONE_RESAMPLE=1, R128_ARMOR_TONES=1 e R128_BATCH com o nome da variante. R128_SGDK211_COMPAT=1 foi usado nestes builds.

## SHA-256 das ROMs

- control — 5d368ac72f3b41072b8264aad820599068ea1a52aa97337b943bc7f873fe7f13
- block — de063afea5e030763845744be87422fa6b133c9e8c93e69e616b6136163d72cf
- nodes — 3525e0279fa80de44ba426a1202bad595b3e8159bdba26417b36be6f8d8ec8f6
- shot — d8351414c772f760aedc64b201a5ff7e723005108919615f3f54012407ae508f
- openings — 0ea6663c97e534b181867096d07e6409ab5f4e8753eb7f9d671a57e344f1cf60
- effects — 2aa107f9244f92f60f69902747f3ee92ca014b7377f5f941a4b13af9df4782b0
- all — 75647a76f243e3d70b434c6dbbce8e6706bbac7f82530e42866a1b3dee069421
