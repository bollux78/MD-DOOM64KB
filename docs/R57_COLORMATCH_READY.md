# R57 ColorMatch — experimento preparado (NÃO COMPILAR AINDA)

Objetivo: comparar um catálogo Pair-V cromaticamente equilibrado com a R56 A6M e com os protótipos do Werk, preservando sua arquitetura e as seis âncoras sólidas usadas nos flats.

## Ideia

- Base: R56 A6 mixed de Cláudio e Werk; preservar PAL0/PAL1 nos índices 0..6 (seis âncoras e transparência).
- Usar as 56 cores-base da 8×8 como candidatos offline para os nove slots de CRAM restantes em **cada plano**.
- Reservar cobertura para famílias vermelho, laranja, amarelo, verde, azul e roxo quando a paleta original permitir.
- Usar o COLORMAP como proxy **não calibrado**; limitar o peso dos tons muito escuros, sem excluir sombras.
- Criar nove códigos adicionais por plano, com pares ABAB escolhidos por aproximação CIELAB da PLAYPAL e com limite de contraste.
- Permitir diversidade entre PAL0 e PAL1; penalizar diferença entre planos apenas para manter neutros coerentes (não forçar A≈B em toda parede).
- Preservar flats 1..6, transparência zero, formato das duas LUTs de 34×256, 512 tiles Pair-V, DMA e menu.
- Não mudar TICRATE, I_GetGameTime, render ou movimento.

## Entrega esperada ao disparar

ROMs previstas: doom-md-r57-cm6-play.bin e doom-md-r57-cm6-perf.bin. Relatório de LUTs e composição cromática, oráculo de invariantes e smoke curto no BlastEm.

Avaliar no mesmo enquadramento azul do chão, cinza do teto, marrom/bege do pilar, painel vermelho/verde/amarelo, padrões verticais, FPS e contraste. Nenhuma melhoria é presumida antes da comparação no emulador.

## Coordenação com o Werk

A branch é isolada: exp-r57-colormatch-prepared. Não disparar um novo job até conhecer os resultados do Werk. Comparar as hipóteses antes de fazer merge. O script experimental está em scripts/lab/gen_r57_colormatch.py e a integração do build em scripts/lab/build_r35_linear.fish. O workflow deve exigir ativação explícita por commit marcado [run-r57] e não deve instalar dependências ou capturar a área de trabalho.

## Limitações e verificações pendentes

O modelo usa o histograma do COLORMAP como proxy, não a distribuição real de pixels do timedemo. O gerador e sua integração precisam passar pelo pipeline de build antes de considerarmos a ROM pronta; nenhum desempenho ou fidelidade visual foi validado ainda. Uma instância de runner self-hosted executa normalmente um job por vez, e jobs concorrentes são enfileirados.
