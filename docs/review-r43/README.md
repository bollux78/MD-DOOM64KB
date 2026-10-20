# R43 — Cores cinzas no DOOM-MD 4×4 para CRT (variante isolada)

Solicitação: na imagem do usuário, quase todos os marrons das grandes áreas de piso/teto e partes de paredes deveriam ser **cinza como no DOOM original**. No renderer pixel4, `r22_palette.h` tinha apenas 16 entradas (preto, 14 cores do PLAYPAL, branco). Os tons neutros muito escuros/médios podiam mapear para paletas marrom/oliva.

## Implementação, separada do desempenho

- Base: **R42 ASM** validada em benchmark (3,88 FPS / 550,32 s na DEMO3). Não modifica os kernels de paredes, pixels 76×44, fontes, menus ou dados do jogo.
- **R43 gray** altera **somente** a paleta 4×4 3D (16 entradas ×14 subpaletas, para flash de dano) e `r22_color[256]` de PLAYPAL→paleta. Original `r22_palette.h` permanece gerado pelo R22 sem modificação.
- O novo mapeamento reserva dois tons cinza escuro/médio nos slots #1 e #4 (que antes eram preto duplicado e marrom escuro) e trata como neutros os valores PLAYPAL com diferença máxima entre canais R/G/B de até **24**. Esses índices passam a escolher exclusivamente uma rampa de cinzas `0,1,4,8,11,14,15`. Cores originalmente saturadas continuam sendo quantizadas às cores disponíveis. É uma compensação cromática numa paleta de 16 slots; outros marrons reais podem permanecer ou deslocar-se.
- Os slots reservados usam cores da PLAYPAL original em cada subpaleta de flash, escolhidos por tons quase neutros (chroma ≤20) de baixa/média luminância.
- O efeito se aplica a **chão, teto, paredes, sprites e arma que usem os mesmos índices neutros**, pois o 4×4 compartilha uma única lookup cromática para todo o 3D. Não há distinção semântica por textura e portanto não é possível garantir que 100% dos marrons se tornem cinza nem manter todas as cores cromáticas sem perda.
- **Título, intermissão, arte Bayer8 320×224 e texto da WINDOW R40b permanecem intactos**.
- Não cria LUT em RAM nem gasta tempo por pixel: a nova lookup é constante ROM; custo esperado ≈0, mas medir.

## Conteúdo do pacote
1. `doom-md-r43-control-p4perf.bin`: R42 ASM original, paleta 4×4 original (controle exato de código).
2. `doom-md-r43-gray-p4perf.bin`: mesma ASM e assets, nova paleta cinza.
3. `doom-md-r43-gray-p4play.bin`: testável no CRT, nova paleta cinza.

As duas PERF são 2134 frames na DEMO3 e devem ser comparadas a ~3,88 FPS (R42 asm); as ROMs não são a futura R40c dual. O novo shader/cor é um experimento R43, não se transfere automaticamente para outras branches.

## Como testar
1. Abra a nova gray-play na mesma cena de referência da captura e compare com R42 asm-play **em ângulo e posição semelhantes**. Observe se piso, teto e frisos das paredes ficaram neutros sem perder o contraste.
2. Verifique arma, sprites, portas e iluminação (escala de claridade das 14 subpaletas). Marrom original que for realmente cromático pode continuar marrom; se não bastar, ajustar a detecção no gerador numa próxima variante com screenshot comparativa. Evitar recolorir a palette inteira indiscriminadamente.
3. Confira título/Options/WIMAP0 sem flicker e texto residual, as correções aprovadas na R40b.
4. Rode as duas PERF completas e informe FPS/tempo. Mudança apenas cromática não deveria afetar a performance materialmente, mas validar.
5. Reporte `R43-GRAY-PALETTE-REPORT.txt` para ver quantas cores neutras foram protegidas e o efeito da remap.

**Importante:** alteração estrutural para 8×8/4×4 runtime na R40c ainda é trabalho distinto. Qualquer integração futura de uma paleta cinza precisa preservar a paleta R39f do 8×8.
