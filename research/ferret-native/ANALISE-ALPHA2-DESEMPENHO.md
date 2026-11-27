# Análise de desempenho: Alpha2 x FERRET-MD R08 (Cláudio, 26/11/2026)

Para o Werk. Medições no MAME 0.264 local (não console). Branch `research-ferret-r07-perf-claudio-20261126`, commit `d9d2f93` (R08).

## 1. Como foi medido
- **Câmeras iguais nas duas engines.** Contrato de coordenadas medido na RAM da Alpha2 (andando e girando no spawn):
  x Alpha2 = x WAD; y Alpha2 = y WAD + 3456; z Alpha2 = 1 - altura do olho; ângulo Alpha2 (0..255) = -ângulo Doom.
  Câmeras: spawn (Alpha2 1056,-160,-40,192 = WAD 1056,-3616, olho 41, Doom 90) e as poses de debug zigzag
  (Alpha2 2980,170,-16, ângulos 0/64/128/192 = WAD 2980,-3286, olho 17, Doom 0/270/180/90).
  As 12 poses da R04 NÃO são essas câmeras (o "zigzag-walkway" da R04 é 1504,-2938).
- **Alpha2:** um *write tap* na porta de dados do VDP (0xC00000). A Alpha2 escreve a imagem pela CPU direto na porta
  de dados (cerca de 11.500 escritas de word por quadro, ~23 KB, a tela 3D inteira, em 1 a 2 VBlanks). O início de cada
  rajada marca um quadro novo; o intervalo entre rajadas é o tempo de quadro inteiro (jogo + render + envio).
- **R08:** `mame_render_time.lua` (tempo exato entre os estágios 3 e 4 da mailbox) = só o render.

## 2. Resultados
| Câmera | Alpha2 (quadro inteiro) | R08 (só render) | R08/Alpha2 |
|---|---|---|---|
| spawn | 7,54 VBlanks = 0,126 s | 0,421 s | 3,3x |
| zigzag 0 | 8,47 = 0,141 s | 0,318 s | 2,3x |
| zigzag 64 | 9,35 = 0,156 s | 0,397 s | 2,5x |
| zigzag 128 (céu) | 11,76 = 0,196 s | 0,713 s | 3,6x |
| zigzag 192 | 9,22 = 0,154 s | 0,344 s | 2,2x |
- Variação: Alpha2 1,55x entre a cena mais leve e a mais pesada; R08 2,2x.
- O primeiro render da R08 (0,656 s no spawn) inclui preparação única; o valor da tabela é o render seguinte.
- Geometria: nas 5 câmeras a R08 bate com a Alpha2 (paredes, aberturas, janela de céu no mesmo lugar).
- Cores: diferem porque a Alpha2 recolore texturas (BROWNGRN fica marrom-avermelhada; no Doom é oliva). Não é erro da R08.

## 3. O que já sabemos da Alpha2
- Perfil antigo da ROM: ~15% num laço que junta duas words e grava cada long duas vezes (metade das colunas, duplicadas
  na hora de escrever), ~20% no renderer, ~7% em barramento/VDP.
- `scaler.fsc` extraído dela: 2048 escalas fixas (desenho de coluna sem checagem por pixel).
- Envio da imagem: CPU -> porta de dados do VDP, não DMA.

## 4. Onde está o tempo da R08 (fases medidas por marcadores, 12 poses)
paredes: desenho 1,8 s, preparação 0,39 s, passada de colunas 0,41 s; projeção e transformação 0,85 s; travessia 0,26 s.
Pixels: 138 mil nos 12 quadros, sem sobreposição; kernel de textura (assembly) ~18% do render.
Candidatas: ~235 paredes por pose passam no PVS e são transformadas/projetadas; ~47 são desenhadas.

## 5. Hipóteses (não confirmadas)
1. A Alpha2 toca em muito menos paredes por quadro (rejeição barata antes da projeção ou listas por região mais finas).
2. Cada coluna usa rotina pré-montada por escala (o `scaler.fsc`), com custo só proporcional à altura.
3. Metade das colunas calculadas.

## 6. O que o Werk pode fazer em paralelo (no x360)
1. Repetir a medição de quadro da Alpha2 no núcleo libretro autenticado (mesmo método: contar rajadas na porta de dados
   do VDP) nas 5 câmeras, para confirmar os números do MAME.
2. Perfil de PC da Alpha2 por câmera (amostras durante o render), separado por faixa de endereço: quanto vai para
   travessia/BSP, quanto para desenho de coluna, quanto para a escrita na VRAM. Isso confirma ou derruba as hipóteses 1 e 2.
3. Contar quantas vezes por quadro a rotina de coluna/escala da Alpha2 é chamada (tap de execução ou contagem por
   amostra) e comparar com as ~300 colunas-de-parede por quadro da R08.
4. Rodar o workflow `ferret-r07-alpha2.yml` (abrir PR da branch R07 para a R06) para os números oficiais de comparação.
5. Testar no console as ROMs R08 BENCH e VERIFY.
Só números e relatórios no GitHub; imagens e dumps ficam em `~/.local/share/ferret-research`.

## 7. O que eu (Cláudio) faço agora
Reduzir as paredes candidatas antes da transformação/projeção sem mudar a imagem (rejeição barata e exata),
medindo com `mame_render_time.lua` e conferindo a mailbox contra a R04 no modo de céu legado.
