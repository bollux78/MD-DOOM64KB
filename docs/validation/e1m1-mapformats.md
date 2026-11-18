# Laboratório E1M1 — formatos de mapa

Três ROMs jogáveis da E1M1, com Benchmark E1M1 na primeira opção do menu. Start abre o menu, A executa o teste e Start retorna da tela de resultados. Ao concluir o mapa, a navegação retorna à E1M1.

Comparação de formatos consumidos pelo render Pair-V. A geometria BSP e o restante da lógica da R128 ainda são usados. O experimento cobre a preparação dos dados das paredes.

| Variante | Dados | FPS médio | Diferença | ROM |
|---|---|---|---|---|
| control | Formato atual da R128 | 8.279 | +0.00% | 3.000 MiB |
| side8 | Tabela alinhada de 8 bytes por lado de parede, em ROM | 8.353 | +0.90% | 3.000 MiB |
| seg32 | Segmentos expandidos para 32 bytes com dados de parede embutidos | 8.362 | +1.00% | 3.125 MiB |

O benchmark no Genesis Plus GX percorreu os mesmos 2134 quadros nas três ROMs. Cinco capturas do viewport nos quadros 64, 256, 512, 1024 e 2000 foram idênticas pixel a pixel. Navegação livre também foi verificada.

A E1M1 tem 273 lados de parede e 732 segmentos. Os 37 lados ligados a linhas com especiais ou tags usam o caminho dinâmico de SRAM. Nos demais, os candidatos consomem os dados preparados em ROM. As alturas dos setores vêm do estado dinâmico. As tabelas originais de colisão e tiros continuam fazendo parte do mapa.

Estas primeiras conversões deram cerca de 1% de ganho. Uma conversão mais abrangente do percurso de visibilidade e preparação das paredes ainda exige outro experimento.

As ROMs contêm dados jogáveis de apenas um mapa. Os índices das outras fases foram mantidos com dados vazios para preservar as referências dos recursos. Os gráficos, áudio e telas compartilhados explicam o tamanho de 3 a 3,125 MiB.

## Compilação

Primeira preparação usa scripts/lab/build_r128_shareware.sh com R128_TONE_RESAMPLE=1, R128_ARMOR_TONES=1, R128_SGDK211_COMPAT=1 e R128_MAP_FORMAT=control. O checkout preparado fica em OUTPUT/prepared/r128-all-sw-pl.

Depois use scripts/lab/r128-shareware/build_maplab_fast.py PREPARED SGDK FORMAT OUTPUT, com control, side8 ou seg32. As recompilações medidas neste ambiente levaram 10,1 s para side8 e 12,3 s para seg32. Os recursos e as paletas são reaproveitados.

## SHA-256

- control — 3777d5a0fdc834929fbcd7aa1c107b0e0cffe64a7f6757da9f11f79af0977294
- side8 — d3fbf7e7576e37722929d323668bb994fb56d64c753b5eef949dade4033299e9
- seg32 — a48b4b1b0467a8d87ab7ffaf67873014c873144960890423f811ca5a559bfa7b
