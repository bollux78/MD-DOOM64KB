# R22c — correção do plano de texto Window

Base: R22 `19b5e24a2b2cebbcb9230a5ad72418ddd3f3e406`, mantendo a projeção real 76×44 e amostras 4×4. Música E1M1; sem SRAM. Testar no BlastEm primeiro; depois hardware real a 7,67 MHz.

## Falha confirmada na R22/R22b

O usuário reportou corrupção em TODAS as play da R22b: linhas pretas na abertura reconhecível e corrupção extensa ao abrir o menu. A tentativa de sincronização da R22b foi insuficiente. Os benchmarks anteriores completarem a demo não validava abertura/menu.

**Erro concreto:** R22/R22b pediam BG_B em 0xF000, mas SGDK `cb114ac` faz `bgb_addr = value & 0xE000` em VDP_setBGBAddress. O endereço efetivo era 0xE000, igual ao BG_A. Limpar BG_B apagava a imagem do BG_A; escrever texto alterava seu tilemap. As validações antigas tratavam o endereço pedido como efetivo e não detectavam esse alias involuntário.

O usuário depois confirmou que, insistindo nos botões, chegava à fase e ela funcionava. A falha se concentra na abertura/menu piscando preto; não assumir falha geral do raster da fase.

## Correção desta leva

- BG_A e BG_B ficam **explicitamente espelhados em 0xE000**. Nenhuma rotina limpa ou escreve no BG_B como se fosse um overlay separado.
- O texto usa o plano **Window em 0xF000**, endereço válido em H40. Fonte continua D400..DFFF; os dois bancos de gráficos continuam abaixo D300. SAT/HScroll permanecem FC00, com Window linhas24..31 reservadas/zero.
- Quando há texto de menu, ativa Window horizontalmente a partir da coluna0. Pixels transparentes do Window deixam aparecer o BG_B, que usa o mesmo tilemap e scroll do BG_A. O overlay continua vendo a imagem por baixo sem precisar de outro tilemap RAM.
- Ao limpar o overlay, somente as primeiras22linhas do Window são apagadas e ele é desativado. A imagem em E000 é preservada. A tela final de benchmark/erro também limpa Window, não BG_B.
- O menu anterior permanece no Window enquanto a CPU calcula a próxima imagem. A limpeza ocorre somente no primeiro texto substituto do quadro; um quadro sem texto desativa o overlay no FinishUpdate. Isso evita deixar a tela sem menu durante o cálculo lento da abertura.
- A inicialização verifica os endereços **efetivos** do SDK (A=B=E000, Window=F000), além do índice da fonte1696.
- Mantém as correções de propriedade do VDP, escrita limitada de texto, tiles sólidos e LUT da R22b. Não altera a projeção/paleta ou os kernels de amostras nesta correção.

O erro de endereçamento está demonstrado no código do SDK. Confirmar que a correção resolve todos os sintomas ainda requer testar as ROMs no BlastEm/hardware.

## Variantes no ZIP

Todos os nomes começam com `doom-md-r22c-` e terminam com `.bin`.

| Sufixo | Finalidade |
|---|---|
| control | Controle 8×8 R21 V2c, sem as alterações do backend 4×4 |
| p4-fixed | DEMO3 4×4, correções de VDP/texto, envio completo de tiles |
| play-fixed | Mesma versão corrigida, jogável com menu e música |
| solid | DEMO3, reutiliza os 16 tiles sólidos sem enviar seus padrões |
| diag-solid | Solid + diagnóstico de pilha/heap; resultado deve ter erros zero |
| play-solid | Solid jogável, menu e música |
| solid-lut | Solid + LUT ROM de 256 pares para expandir cada linha de pixels |
| play-lut | Solid + LUT jogável |
| pattern-lut | Padrão estático diagonal de quadrados 4×4; comportamento intencional |

`solid` tem um mapa RAM de 798 palavras (1596 bytes). Os tiles uniformes apontam para VRAM0..15, pré-carregada uma vez. Os mistos continuam em sua posição exclusiva no banco oculto. Portanto não há aproximação adicional de cor nem mudança visual. Isso serve para qualquer região uniforme, incluindo chão/teto; os tiles mistos nas bordas continuam sendo enviados. Não elimina o cálculo do chão/teto na CPU. O mapa (1596 bytes) ainda é enviado no VBlank; a economia é no envio de padrões (até 25536 bytes por quadro antes da otimização).

`solid-lut` acrescenta 1024 bytes de ROM para substituir a expansão aritmética dos pares. Não acrescenta buffer de pixels em RAM. Nenhuma alteração de paleta ou dither nesta leva.

## Ordem recomendada

1. Abrir `play-fixed`: observar a abertura; Start; abrir/fechar menus várias vezes; iniciar E1M1 e confirmar áudio e imagem.
2. Repetir com `play-solid` e `play-lut`.
3. Executar `p4-fixed`, `solid` e `solid-lut` até a tela final e comparar tempo, média, mínimos/máximos e 2134 frames. Não comparar FPS de `diag-solid` como se fosse sem instrumentação.
4. Executar `diag-solid` e guardar a tela de memória/pilha; testar `pattern-lut` se aparecer corrupção geométrica.
5. Usar `control` para confirmar as condições do teste (~172,48 s no BlastEm anterior).

Se a corrupção continuar, informar o sufixo e se acontece na abertura, ao abrir/fechar o menu ou somente na fase. Não há diagnóstico remoto de VDP a partir do probe CPU.

## Validação automatizada e limites

`test_r22_pixel4.py`: primitivas, colunas reais extraídas do backend, guardas e projeção; UBSan. `test_r22b_video.py`: executa o uploader e o escritor de texto extraídos do código de produção com portas VDP simuladas; percorre as 65536 combinações de quatro amostras nos dois bancos, verifica equivalência de imagem e preservação da fonte/mapas, zero upload de padrões em tela sólida, espera na abertura/menu, limites de caracteres e preservação da área FC00. A R22c acrescenta100ciclos de abrir/fechar menu preservando todo o mapa A/B e os glifos exibidos durante o cálculo do raster, usa Window no código de produção e verifica as máscaras reais de endereço do VDP/SDK. Três configurações (fix/solid/lut).

CI: compila nove ROMs/ELFs, audita identificação/flags/limites, orçamento de descompressão da fonte no boot e espaço restante após openings. Inclui probe MC68000 de primitivas, seleção de tile sólido e LUT, para execução em harness CPU (não é uma ROM de jogo).

Os testes host não emulam temporização nem o VDP real. A compilação e o orçamento de memória não equivalem a validação da demo/hardware. O ganho de FPS e a resolução da corrupção ainda dependem do teste das ROMs.
