# R87 — trocas de qualidade por desempenho, inspiradas em FastDoom

Base: **R85 all**. R86 não adotada. O usuário autorizou perda de imagem e mudanças de comportamento. O céu deve permanecer texturizado, fixo na tela, sem perspectiva angular ao girar a câmera, e ser amostrado apenas em trechos visíveis.

| Nome | Mudança | Comparador |
|---|---|---|
| control | R85 all, incluindo céu original | referência original |
| sky | Céu texturizado fixo, x linear da tela, recorte antes da origem | control |
| farwalls | Céu fixo + paredes distantes chapadas | sky |
| vhalf | Céu fixo + metade das amostras verticais de textura no kernel | sky |
| decor | Céu fixo + descarte de decoração distante | sky |
| sprites | Céu fixo + posts de sprites distantes sem detalhe vertical | sky |
| ai | Céu fixo + decisões distantes em cadência reduzida | sky, com simulação diferente |

Todos geram PLAY/PERF com nome próprio. Não há combinação automática dos experimentos: medir os ganhos e escolher a qualidade primeiro.

## Céu

O carregamento R_LoadSkyPatch já era vazio. O renderer chama R_DrawSky somente para intervalos expostos do teto. Agora os limites físicos/viewport são intersectados antes de resolver a coluna da textura. O índice x usa uma tabela constante de 76 bytes em ROM (céu SKY1 de 256 colunas dos assets atuais), sem divisão por coluna, linear nas coordenadas da tela e não depende de viewangle nem de xtoviewangle. A posição vertical e o passo são fixos. Não há passe de céu de tela inteira, buffer novo ou cálculo offline por frame oculto. O céu ainda custa amostragem e escrita nos trechos efetivamente visíveis; não é uma imagem gratuita instalada em outro plano VDP.

## Limites e perdas específicas

- **farwalls:** fracstep >=4096 seleciona a simplificação (limiar de escala/projeção, não distância euclidiana). O conversor escolhe o índice de cor mais frequente das colunas compostas completas ou, na ausência delas, do primeiro patch. Guarda uma origem constante de 128 bytes por textura em ROM. Isso permite também o reaproveitamento de origem da R66. O caminho simplificado evita resolução/composição da coluna e usa o preenchimento rápido de flat. A iluminação é aplicada uma vez; o perfil usa o mapeamento de cores dos flats. Posts mascarados distantes que passam pelo mesmo escritor podem perder detalhe vertical, preservando os limites do post. Bypassar composições também muda o histórico de bytes residuais do cache; diferenças visuais adicionais são permitidas nesta experiência.
- **vhalf:** substitui as duas amostras de cada par vertical por uma, com avanço de fase dobrado modular. Reduz o trabalho do kernel de paredes e sprites com LUT composta. O viewport, projeção, clipping e geometria continuam em **76x44**; não se apresenta isso como um motor geométrico 76x22 ou uma redução completa de resolução. As amostras repetidas acompanham o começo dos spans/posts; o alinhamento pode variar nas extremidades. Fallbacks C e fuzz continuam no caminho normal. Pisos/tetos de cor constante já não tinham textura para reduzir.
- **decor:** descarta antes da projeção objetos não atiráveis, não projéteis e não coletáveis, além de 384 unidades em x ou y (distância quadrada/Chebyshev). Inclui cadáveres; os objetos continuam na simulação. Itens, inimigos e projéteis não são descartados por esse filtro.
- **sprites:** abaixo de escala FRACUNIT/6, substitui a amostragem vertical de cada post por sua cor central. Preserva os contornos, clipping, luz e transparência entre posts. Fuzz não recebe esse tratamento; arma próxima não atinge esse limiar. Há perda de textura interna e possível listramento entre colunas.
- **ai:** a mais de 512 unidades em x ou y do jogador, adia decisões em três das quatro fases de leveltime, escalonadas por tipo. A_Look fica menos frequente. A_Chase continua reação, threshold e rotação; quando há alvo vivo e não está em JUSTATTACKED, pode saltar a decisão de ataque/retarget diretamente para o caminho normal de movimento/P_Move/P_NewChaseDir e som ativo. O thinker, a colisão e o avanço dos estados continuam ativos. Isso muda ataques, aquisição de alvo, RNG e pode mudar decisões de movimento posteriores: **não é uma simulação equivalente nem uma medida de aceleração pura do mesmo trabalho**. A cadência das ações de estado pode interagir com as quatro fases. Não há estado persistente novo a salvar.

## Verificações

`test_r87.py` prepara R81 -> P1F1 -> R83 sprites -> R85 all em cópias descartáveis e aplica cada um dos sete patches. Compila a função C real de céu com mocks e testa 4.560 combinações de x/y; trechos invisíveis usam patch nulo para detectar acessos indevidos. Compila o seletor C real da IA e verifica limiares positivos/negativos, fases e jogador nulo. Verifica as 125 origens constantes completas. A decomposição do passo dobrado do kernel é conferida para todos os 65.536 valores de step. Esses testes são host; não substituem o m68k compilado e a inspeção visual.

O workflow compila 14 ROMs, exige ROM <=4 MiB, BSS <=57.920 B e inicialização/captura no BlastEm, com limite de 8.000 frames por processo. Há relatório de pixels diferentes (esperados), timing parcial dentro do mesmo job e diagnóstico parcial de pilha. Compara tanto com control quanto com sky sem repetir capturas. O wrapper aceita diferenças visuais e exige ao menos 100 tics comuns. Não escolhe vencedor por equivalência de pixels. O benchmark completo e a escolha da perda visual ficam com o usuário. O resultado AI deve ser separado dos candidatos só visuais.

Preparação de um conjunto em checkout limpo: apply_r81.py; R80_EXPERIMENTS=P1+F1 apply_r80_performance.py; R83_CANDIDATE=sprites apply_r83.py; R85_CANDIDATE=all apply_r85.py; R87_CANDIDATE=control|sky|farwalls|vhalf|decor|sprites|ai apply_r87.py; build_r71a12mul_hud.py no ambiente do workflow.

FastDoom consultado: viti95/FastDoom `9b7ad30dce6f9a902a42fbac3f76e9578bd3773b`. Ideias de paredes chapadas, simplificação de sprites e descarte de distantes são adaptadas ao backend do Mega Drive; a cadência reduzida de IA é proposta própria, não uma função atribuída ao FastDoom.
