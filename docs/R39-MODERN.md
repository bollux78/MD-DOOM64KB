# R39f modernizada — recursos da R105

Base de recursos: R105-twoface, commit
`9b5996d6a439dac7e1683f3a4d3d4d87efe88ac1`.

Esta ROM restaura o modelo gráfico original da R39f: projeção 38×22,
uma palavra de tile por amostra de 8×8, as quatro paletas de `genpal.py`
e as tabelas/padrões originais de dithering Off / Checker / Vertical.
Não usa Pair V para desenhar a cena e não compila Shadow.

Mantém HUD, fonte, menus, telas estáticas, música, SFX, save/load,
cheats, AI Normal/Low e benchmark E1M1/E1M7 da base atual. AI Normal
é o padrão. O menu Dithering substitui as opções A2/L3 e Shadow,
que pertenciam ao renderer 4×4. Não é a Cell8 híbrida anterior.

Mantém a correção R104 que impede interrupções dentro de acessos à SRAM,
as multiplicações R98 de sprites, a especialização twoface e as otimizações
compatíveis de lógica/dados. As buscas de cor por segmento foram adaptadas
para palavras completas de tile. O kernel de pixels é o ADDX original
R20/R39, e os flats usam preenchimento de palavras com DBRA.

## Paletas da cena e do HUD

A cena R39 usa quatro bancos de CRAM; o HUD moderno usa dois desses bancos.
O VBlank restaura as quatro paletas da cena. Um HInt, no espaço preto abaixo
da cena, carrega as duas paletas originais do HUD. O display fica brevemente
desligado durante essa escrita, dentro do espaço preto. Menus e telas
estáticas desativam a troca. É necessário reservar pelo menos 8 pixels de
recorte vertical; as demais opções de tamanho permanecem disponíveis.

Essa integração de paletas é nova e precisa de avaliação no Mega Drive,
especialmente a borda superior do HUD, H32/H40, menus, save/load e transições.
Não declarar estabilidade em hardware com base apenas no emulador.

## Validação

O teste de host compara 40 mil colunas com um oráculo de palavras de tile,
incluindo bits de todas as paletas, clipping, fase de textura e sentinelas.
O runner compila PLAY e uma PERF interna e verifica no disassembly que o
callback HInt retorna com RTE (ABI de interrupção do SGDK). Capturas parciais da PERF verificam
os índices e os quatro bancos de paleta nos três modos de dithering.
Isso não é benchmark completo nem validação visual do hardware.

O pacote entrega a ROM PLAY. Testar E1M1/E1M7, AI Normal/Low,
Off/Checker/Vertical, armas, objetos, automap e as funções atuais.
Medir desempenho no mesmo aparelho e com as mesmas opções.
