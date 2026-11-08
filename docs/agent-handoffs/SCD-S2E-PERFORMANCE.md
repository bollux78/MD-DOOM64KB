# S2e — reduzir custo do primeiro modo interativo

## Base aprovada e problema medido

O usuário confirmou a S2d no console e relatou aproximadamente1FPS. A ROM aprovada permanece intacta em `scd-subport-s2d-live/run-42480397654-1/doom-md-scd-s2d-live.bin`. S2e é uma variante separada (`--fast`), sem alterar a lógica G_Ticker/P_Ticker do jogo ou reduzir IA.

A instrumentação usa o contador NTSC `_g_vblankCount` já existente no MD. Mede seis valores por troca: espera/sub+swap, verificação/cópia/backups, aplicação de mundo, aplicação de atores/player, render/DMA, total. Report em61B140. A comparação usa estados2–95 (94 amostras), excluindo inicialização e saída. O tempo de parede do debugger não é convertido em FPS. O resultado é uma medida emulada do contador da ROM, não um novo benchmark físico ou garantia35Hz.

A primeira medição, run42482801821, confirmou o gargalo: S2d1,014FPS equivalentes (59,16VBlanks/quadro), fase verificação/cópia27VBlanks; aplicação de mundo12; atores6; render14,16; espera0. A primeira S2e, ainda com auditoria completa nativa por quadro, caiu para28,59VBlanks/quadro (2,099FPS), cópia1, mundo7,01, atores5,99, render14,59. Pacote médio7730→2679bytes, redução65,35%. São valores emulados do roteiro fixo. Esse run teve falha de inicialização do BlastEm numa regressão Z7, portanto não foi tratado como gate integral aprovado; a medição S2d/S2e em si passou.

## Alterações de transporte

- Setores e sides completos apenas na primeira amostra. Depois, usa os deltas já disponíveis nos produtores S2b. Alturas, flats, luz, texturas/offsets continuam no contrato. O mapa persistente MD é RAM/SRAM nativa, portanto mantém os campos entre trocas de banco Word RAM.
- Atores dinâmicos ainda enviados completos por frame; R24 removed/delay passa a usar deltas após a primeira amostra. Recargas de E1M1 são comparadas ao estado anterior, incluindo restauração de itens e delays. Não é suporte a outro mapa.
- Cópias de buffers alinhados usam palavras32 em vez de loops por byte. Limites, alinhamento, sequenciamento, ownership e restauração por START permanecem.
- Os dois checksums de byte internos dos blobs são omitidos nesta variante e seus campos ficam zero. O pacote completo é validado antes de qualquer aplicação. S2d e variantes antigas mantêm seus algoritmos anteriores.
- Outer wire S2e tem magic53324546, versão2 e marcador de boot5AAD. Layout e input de16 bytes permanecem; input mantém seu FNV. Integridade do pacote usa todas as palavras32 big-endian, com palavra7 zerada: rotacionar acumulador5 bits, XOR com palavra e somar9E3779B9, módulo32. Não é hash criptográfico. Teste C/Python do mesmo valor numérico e352 corrupções de um bit PASS.

## Auditoria de estado e modo de uso

Checks de pacote/versão/tic/alinhamento/limites, tipos/IDs/índices de estado, reconstrução e validação das listas espaciais e integridade do comando continuam ativos em toda troca.

A auditoria completa FNV dos valores nativos aplicados no MD custava grande parte do restante do frame. Na S2e de uso, roda no frame0 e a cada32 tics. Nos demais, o relatório escreve hash aplicado0 e flag checked0, nunca copia o hash esperado fingindo que foi calculado. Mundo: flag em61B034; atores: em61B070. O CD ainda gera o hash canônico autoritativo de todo o estado em cada tic.

`s2e_test_deep` é um override de depuração volátil, padrão0. O teste de correção ativa1 no boot e exige auditoria completa em todos os98 estados. Um segundo processo roda o mesmo binário com o padrão0 (modo de uso), confere os checkpoints periódicos, todos os pacotes/inputs, câmera, arma, registros de atores e listas nativas; os deltas de mundo são reconstruídos em Python. A comparação exige trajetória, dados e hashes dos97 framebuffers renderizados idênticos aos do modo profundo. Somente esse segundo processo alimenta a comparação de desempenho com a S2d de controle. Os registros de atores continuam sendo extraídos dos campos nativos em todos os quadros para a validação independente.

## Resultado final

Commit de implementação `9d466431941339cd78c8746fc27baba1f9675d0b`, Actions run `42483932970`, job `128741595681`: gate integral PASS. Regressões Z4/Z5/Z7/Z8/S2a/S2b/S2c, S2d de controle, S2e profunda e S2e de uso, comparação de imagens/estado e de desempenho: PASS.

| Métrica emulada, roteiro fixo | S2d controle | S2e de uso |
|---|---:|---:|
| VBlanks totais em94 amostras | 5561 | 1790 |
| VBlanks/quadro, média | 59,160 | 19,043 |
| FPS equivalentes60Hz | 1,014 | 3,151 |
| Pacote médio, bytes | 7730,21 | 2678,55 |
| Espera/sub+swap, VBlanks/quadro | 0 | 0 |
| Checagem/cópia/backups | 27 | 1 |
| Aplicação/auditoria de mundo | 12 | 0,149 |
| Atores/player | 6 | 3,638 |
| Render/DMA | 14,160 | 14,255 |

Ganho emulado3,1067×; redução de bytes65,3496%. Os modos profundo e de uso do mesmo binário produziram trajetória, saúde/munição/contagens/tamanhos de pacote iguais e os97 framebuffers renderizados byte-equivalentes por SHA256. O modo profundo confirmou os98 estados nativos; o modo de uso confirmou os checkpoints0/32/64/96 e continuou verificando todos os pacotes, tipos, atores extraídos dos campos nativos, listas, câmera, arma e inputs. Ambos saíram pelo caminho de stop e alcançaram o G_Ticker MD original. Nenhum tick de simulação MD durante o modo CD.

Sub S2e: payload87424 bytes, `_end=0x60680` abaixo do limite0x68000, heap128 KiB. ROM linear4063232 bytes. Marcador de boot5AAD,18 requests WAD e0errors confirmados pelo teste. Limites originais de memória/atores/IDs continuam valendo.

ROM privada: `/home/dan/Projetos/Personal/scd-subport-s2e-fast/run-42483932970-1/doom-md-scd-s2e-fast.bin`.
Mesmo diretório: `live_deep_report.json`, `live_report.json` (modo de uso), `performance_comparison.json`, frames brutos, ELF e relatórios de link. Artefatos binários permanecem privados; este documento contém apenas protocolo, metodologia e resultados resumidos.

## Teste no console e próximo gargalo

S2d funcional/~1FPS foi relatada pelo usuário; S2e ainda não tem medição física. Abrir a ROM com Sega CD ligado, aguardar S2E FAST LIVE SUB LOGIC / TRANSFER PASS /18requests0errors. START e soltar ou aguardar auto-início. Controles mantidos: direção anda/gira, A usa, B atira, C+direção corre/strafe, START sai. Confirmar visual, portas/itens/tiros/arma e retorno ao título, comparando FPS na mesma cena após alguns segundos.

A projeção emulada não é promessa do FPS físico. Uma troca ainda corresponde a um G_Ticker; cadência35Hz desacoplada do render ainda não foi implementada. Áudio de eventos e campanha seguem fora deste marco.

Na S2e de uso, render/DMA representa aproximadamente74,9% do total medido. Com esse renderer intacto, remover todo o restante só levaria esta amostra a cerca de4,2FPS: o próximo trabalho precisa atacar renderização/apresentação MD e separar a cadência da lógica. Não confundir CPU CD em espera pelo MD com transporte lento. A medição de espera observada foi0VBlank neste roteiro, com o sub preparando o próximo estado enquanto o MD processa o atual. Preservar as ROMs S2d e S2e como referências separadas.
