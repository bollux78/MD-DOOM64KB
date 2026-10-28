# R81 — fonte, save/load e cheats

## Base e isolamento

Base de código: R79 `31807c0355298f35ec36ab0c42a847a2493d92e4`, variante sem shadow adaptativo de gameplay. Branch: `exp-chatgpt-r81-menu-save-cheats-20261028`. A análise de desempenho R80 do outro agente segue em branch próprio. Não misturar as mudanças antes de comparar os resultados.

## Comportamento

- Fonte pequena original `STCFN` extraída do IWAD shareware fixado pelo CI, em máscara branca. Maiúsculas e minúsculas usam os mesmos desenhos. Glyphs maiores que 8×8 são reduzidos por vizinho mais próximo. 96 tiles no banco de fonte existente, sem framebuffer adicional.
- Menus mantêm a pedra inferior sem emenda e seu shadow estático.
- Um slot de save completo na SRAM de 32 KiB. Salva posição, inventário, saúde, cheats, objetos dinâmicos, alvos, setores, paredes alteradas, portas, pisos, plataformas, luzes, rolagem de paredes, botões, itens removidos, contadores e RNG. Os ponteiros são convertidos em IDs e reconstruídos ao carregar.
- Menu Cheats: IDDQD liga/desliga invencibilidade; IDKFA liga/desliga munição infinita e concede armas disponíveis no episódio, chaves, munição e armadura 200; IDCLIP liga/desliga colisão. Os switches exigem uma partida ativa com jogador vivo.
- Load inválido ou corrompido deve apresentar mensagem e preservar a partida atual.

## Persistência e limites

A área de mapa usa os bytes lógicos `0..26623`; o save ocupa `26624..32767`. Linhas usam 6 bytes, lados usam 8 físicos e tokens de 16 bytes; nós de contato continuam com 12 bytes. E1M6 preserva capacidade para 423 nós, contra 405 antes da alteração. O bit ML_MAPPED muda somente na representação runtime de `r_flags`; as flags dos mapas em ROM permanecem no formato anterior.

O slot tem cabeçalho de 16 bytes, identificação/versionamento e CRC16. O serializador mede primeiro: se o estado não couber nos 6128 bytes de payload, recusa o save sem apagar o anterior. Só então grava os dados, verifica a leitura e confirma a identificação do cabeçalho por último. Não há dois bancos; interrupção durante uma gravação pode invalidar o slot, e será detectada no próximo load.

São usados no máximo 512 IDs de objetos, em 2048 bytes do framebuffer já existente enquanto o jogo está parado. Não existe alocação permanente de um buffer de save. A redução do menu de oito slots antigos para um recupera 56 bytes de WRAM.

SRAM/FRAM persistente depende do cartucho/emulador gravar o arquivo de save da ROM. Os stubs antigos de SaveSettings/LoadSettings permanecem sem escrita: seus offsets antigos não podem ser habilitados sobre a área de trabalho do mapa.

## Reprodução

O checkout original recebe `python3 scripts/lab/apply_r81.py` **uma única vez**. Ele executa a cadeia R72–R79 e aplica R81. Os fontes no GitHub são a entrada desta cadeia, e não devem receber manualmente as mesmas alterações duas vezes.

O workflow `.github/workflows/r81-menu-save.yml` gera fonte/HUD/artes, compila PERF e PLAY, exige BSS ≤ 57920 e ROM ≤ 4 MiB, executa smoke de 800 frames e o teste funcional em BlastEm. Shadow adaptativo permanece desligado.

## Verificação

- `test_r81_codec.py`: inteiros assinados e sem sinal, extremos, RLE de zeros, campos, CRC e limites.
- `test_r81_sram.py`: compila a implementação real contra memória de teste, exercita todos os 1352 registros de linha e 805 de lado de E1M6, acessos agrupados, nós e preservação dos bytes de save.
- `test_r81_cheats.py`: executa o handler real dos switches e suas restrições.
- `test_r81_rom.py`: chama as funções reais no processador emulado, altera posição/saúde/piso, carrega e exige serialização canônica idêntica. Corrompe um byte e exige rejeição sem alterar o jogador. Aprovado em nove mapas × três dificuldades e mais três casos com porta, piso e plataforma ativos. A corrupção foi rejeitada nos 27 casos de mapa/dificuldade. Os payloads iniciais ficaram entre 662 e 4409 bytes; isso não garante que qualquer estado posterior de combate caiba nos 6128 bytes disponíveis.

Cada caso usa uma sessão independente. A automação usa no máximo 10000 frames por execução e não representa benchmark completo. Validação visual do menu, disparos com munição infinita e persistência após desligar/religar em cartucho ainda exigem teste de uso. Os relatórios do artefato são a fonte de confirmação da compilação e dos testes, não este plano.
