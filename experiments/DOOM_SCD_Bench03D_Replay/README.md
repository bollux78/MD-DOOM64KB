# SCD 03D — replay de colunas

O teste usa os bytes de máquina de R60/R113 extraídos da R128. Cada
chamada é comparada com os bytes observados na R128. Pixels dos passes
fora do kernel são compostos a partir da captura, e o quadro resultante
é comparado byte a byte no sub e no principal. A medição seguinte repete
64 quadros sem comparar pixels por chamada e testa o transporte 1M.

O fixture e a ROM do replay contêm dados privados. O workflow os monta e
grava na pasta Personal do runner. A tela apresenta resultados do teste e
os acumulados. A saída de DMA é o framebuffer bruto da R128 em VRAM,
sem reproduzir o tilemap e a apresentação final do jogo.
