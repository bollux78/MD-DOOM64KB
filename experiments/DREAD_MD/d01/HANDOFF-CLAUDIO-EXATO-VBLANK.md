# Dread D01 — textura exata e leitura do controle no VBlank

[Baixar as ROMs e os vídeos](builds/Dread-D01-Exato-VBlank.zip?raw=true)

Base do Cláudio no commit 0681cb0, com o handoff 2e11bb8. A ROM 00 veio diretamente do artefato do run 44930721164. As outras três foram compiladas localmente a partir dessa base, com o SGDK e o toolchain disponíveis neste ambiente.

## O que foi encontrado

A imagem da referência 0681cb0 difere da d4f9f4b em todas as nove poses amostradas do benchmark (quadros 1, 20, 45, 70, 95, 120, 150, 250 e 312). No quadro 70, 1.827 dos 11.520 bytes do framebuffer são diferentes. Em câmera parada no início de E1M1, posição e ângulo são iguais, mas 1.467 bytes diferem.

Os hashes de paleta, banco de texturas, banco de sprites e PVS são iguais nas duas builds. A diferença já está na build b1ba593, anterior à reescrita c9aa748. Os nove framebuffers de b1ba593 são idênticos aos de 0681cb0. O principal ponto a revisar é 6c8c512, que substituiu a origem vertical em 16.16 pela origem inteira relativa à borda da parede.

A correção conserva os registros sequenciais de colunas e os saltos diretos para os escalonadores. Ela calcula novamente a origem vertical com a mesma precisão 16.16 e o mesmo arredondamento da d4f9f4b, inclusive no caminho mascarado. Isso requer recuperar a multiplicação da origem por coluna.

A variante rápida conserva o limite por potência de dois do Cláudio. Quando esse limite não permite decidir, usa a verificação exata original. As três ROMs corrigidas produziram o mesmo framebuffer da d4f9f4b nas nove poses comparadas, 27 comparações no total. Essa é uma validação amostral.

## ROMs e resultados

As ROMs contêm E1M1–E1M9 do Doom shareware, música, HUD, pistola, combate e os menus existentes. As três novas ROMs ocupam 3,375 MiB cada. Funcionam sem mapper e foram exercitadas com a SRAM indisponível no emulador.

| ROM | Benchmark E1M1, 312 quadros | Giro inicial de E1M1, 1.500 atualizações de vídeo |
| --- | --- | --- |
| 00-Claudio-0681cb0.bin | 3,73 FPS, com a diferença de imagem descrita acima | referência do Cláudio de 6,39 FPS |
| 01-Textura-Exata-Controle.bin | 3,58 FPS | 6,00 FPS |
| 02-Textura-Exata-Rapida.bin | 3,62 FPS | 6,11 FPS |
| 03-Textura-Exata-Input-VBlank.bin | 3,57 FPS | 5,98 FPS |

Genesis Plus GX NTSC. O giro usa LIMITE LIVRE, jogador na posição inicial, IA ativa e direcional direito durante 1.500 atualizações. A média usa os intervalos completos entre apresentações, identificadas pela troca da tabela de tiles. As trajetórias angulares dependem da cadência e da limitação de dt da lógica. Os dados completos estão em final-results.json.

O controle exato permite medir o limite rápido com a mesma imagem e o mesmo toolchain. Os números novos incluem o custo de corrigir a aproximação anterior e ainda ficam abaixo do alvo de 7,77 FPS da Alpha 2 com SRAM de 16 bits.

## Interrupções e controle

JOY_update do SGDK desliga as interrupções enquanto lê o controle. A base chama essa função durante a área visível, interrompendo a cadência das escritas de VSRAM mesmo com hint_b baseado em tabela.

A ROM 03 move a leitura para o callback de VBlank e deixa a lógica ler o estado em cache. O jogo utiliza a porta 1. A sondagem da porta 2 fica desligada nessa variante para reduzir o custo de leitura a 60 Hz. O orçamento de DMA diminui 512 bytes por VBlank para reservar tempo à leitura do controle. As ROMs 01 e 02 continuam sendo controles para essa mudança.

No vídeo de dez segundos, o detector sinalizou 39 quadros na ROM 02 e zero na ROM 03. Num teste mais longo de 2.000 atualizações por mapa, a ROM 03 ainda teve 6 quadros sinalizados em E1M1 e 4 em E1M2, concentrados nas linhas 19–23 do topo. A arma central é excluída do detector, que procura diferenças nos pares de linhas. Os dados brutos estão em vblank-stress-results.json. Os vídeos foram capturados do emulador.

H40/H32 e linhas/colunas foram exercitados entrando e saindo da pausa. A tela preta ao trocar de modo não reapareceu. O início automático após 15 segundos também foi verificado nas builds de teste. START permite abrir o menu antes do início automático.

## BlastEm e pendências

O script test_d01.py reproduziu BlastEm RSP EOF na ROM 0681cb0 depois da entrada no render 289 e 4.461 amostras de VBlank do profiler. Na variante VBlank anterior ao ajuste final de porta 2, o erro reapareceu depois da entrada no render 275. O erro de RSP não determina, por si só, que a ROM travou em execução normal. A variante final de porta 2 foi validada no Genesis Plus GX.

Faltam teste no X7, investigação dos resíduos do topo e diagnóstico do EOF no BlastEm. O teste A de SRAM de 16 bits não foi executado nesta ROM de episódio porque ela supera o limite de 2 MB definido no handoff. Nenhuma das três variantes utiliza SRAM.

O pacote contém ROMs, resultados e capturas. Os WADs e ELFs permanecem locais.

## Reprodução

Na raiz do checkout, configure GDK e execute o script com o WAD shareware e o diretório de saída.

```bash
GDK=/caminho/sgdk bash experiments/DREAD_MD/d01/tools/build_exact_tests.sh /caminho/doom1.wad /caminho/saida
```

DREAD_COPY_SEGA_S=1 foi necessário no SGDK local. DREAD_PREPARED_MAPS pode apontar para os nove mapas já convertidos com uma paleta compartilhada e pad de 32 texels. Os flags das três variantes estão no script.
