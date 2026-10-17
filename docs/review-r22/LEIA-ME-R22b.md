# R22b — propriedade do VDP, tiles sólidos e LUT

Base: R22 `19b5e24a2b2cebbcb9230a5ad72418ddd3f3e406`, mantendo a projeção real 76×44 e amostras 4×4. Música E1M1; sem SRAM. Testar no BlastEm primeiro; depois hardware real a 7,67 MHz.

## O que motivou esta leva

Na R22, p4 e diag-p4 completaram os 2134 frames (914,00 s e 918,05 s); diag: erros 0, pico 2368/2560. O controle 8×8 fez 172,48 s. A play-p4 já apresentava linhas pretas na abertura e, ao apertar Start para abrir o menu, corrupção extensa. A pattern-p4 era intencionalmente uma imagem estática diagonal, não um travamento.

O código permitia uma troca de tilemap pendente enquanto a próxima abertura limpava BG_B. A espera anterior era condicional ao texto estar sujo; o título sem menu podia escapar dela. Isso permite colisão nos registradores/portas do VDP. É um defeito identificado por inspeção; não afirmar que explica sozinho todos os sintomas sem reproduzir e testar a correção no emulador.

## Mudanças comuns às variantes 4×4

- Espera incondicional pela troca pendente no início de D_Display, antes de limpar planos ou desenhar texto. FinishUpdate continua esperando antes de reutilizar o mapa/banco.
- Escrita de texto própria, limitada a 38 colunas, com interrupções mascaradas somente durante a transação; substitui o temporário de 256 bytes na pilha usado por VDP_drawTextEx. Caracteres fora de 32..127 viram espaço.
- Limpeza protegida somente de BG_B linhas 0..21; não limpa mais o trecho FC00 que contém SAT/HScroll. Espera DMA terminar e restaura incremento 2.
- Inicializa explicitamente 16 padrões sólidos em VRAM, incluindo tile0 transparente para o plano de texto. Não depende do estado inicial desses tiles após realocação da fonte.

## Variantes no ZIP

Todos os nomes começam com `doom-md-r22b-` e terminam com `.bin`.

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

`test_r22_pixel4.py`: primitivas, colunas reais extraídas do backend, guardas e projeção; UBSan. `test_r22b_video.py`: executa o uploader e o escritor de texto extraídos do código de produção com portas VDP simuladas; percorre as 65536 combinações de quatro amostras nos dois bancos, verifica equivalência de imagem e preservação da fonte/mapas, zero upload de padrões em tela sólida, espera na abertura/menu, limites de caracteres e preservação da área FC00. Três configurações (fix/solid/lut).

CI: compila nove ROMs/ELFs, audita identificação/flags/limites, orçamento de descompressão da fonte no boot e espaço restante após openings. Inclui probe MC68000 de primitivas, seleção de tile sólido e LUT, para execução em harness CPU (não é uma ROM de jogo).

Os testes host não emulam temporização nem o VDP real. A compilação e o orçamento de memória não equivalem a validação da demo/hardware. O ganho de FPS e a resolução da corrupção ainda dependem do teste das ROMs.
