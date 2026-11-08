# S2d — input MD, G_Ticker CD e estado por tic em Word RAM

## Aprovação posterior no console

O usuário confirmou que a S2d funcionou corretamente no console e relatou aproximadamente1FPS. Essa é uma aprovação funcional geral, sem nova foto ou medições por fase; não atribuir um teste físico individual de cada botão. O trabalho autorizado seguinte é melhorar desempenho, preservando esta ROM como referência. Os testes físicos sugeridos abaixo ficam como registro histórico.

## Base e limite do marco

S2c confirmada no console pelo usuário, com autorização para seguir. A S2d substitui o replay offline por execução interativa sincronizada: controle no MD, lógica original no sub, apresentação no MD. Primeiro protótipo de E1M1: uma troca por tic e um estado completo por troca. Não há garantia de cadência35Hz, benchmark de FPS offloaded ou campanha completa. Áudio de eventos do sub ainda não é transportado.

O MD usa direção para andar/girar, A para usar, B para atirar, C+direção para correr/strafe e START para sair. JOY_update é chamado explicitamente, como exigido pelo caminho de input R128 no console. Não chama G_Ticker/P_Ticker MD durante a execução CD.

## Inicialização e continuidade

O sub inicializa transporte/WAD/metadados/P_Init e carrega E1M1 com G_InitNew original. DTE1M1 também é lido como verificação da base; seus comandos não dirigem o jogo S2d. Publica assinatura51B1/marcador5A9D e espera o latch de início do MD em FF8010; o diagnóstico pode ficar aberto sem timeout da primeira transação.

O MD mantém o boot S1b e o servidor WAD. Após o diagnóstico, inicializa uma cópia local do mapa para render, libera START e publica D04D em A12010. O sub produz estado0 e pede SCD_CMD_TIC. Cada troca entrega ao MD o estado do banco anterior do sub e entrega ao sub o próximo comando MD. O sub aplica netcmd por um setter externo ao G_Ticker original, executa exatamente um G_Ticker, incrementa gametic, produz o próximo estado e repete. O corpo G_Ticker continua idêntico à fonte original. O índice do comando é ecoado no estado seguinte.

START envia stop no comando da próxima troca. O sub confirma a transação, publica D04F e para num laço, sem nova execução de lógica. O MD restaura o estado local e retorna ao título. A fronteira de saída de nível/intermissão também encerra este protótipo, em vez de fingir suporte à campanha ou aos menus no sub.

## Protocolo e ownership

Reutiliza o protocolo S1 de sequências nãozero, ACK/DONE e swaps 1M. MD é o único iniciador via A12018. O sub nunca escreve DMNA. Os requests DIR/LUMP continuam atendidos no mesmo loop. O comando TIC escreve16 bytes de input na área0100 do banco MD: magic53324449, tic esperado32, forward/side8 assinados, turn16 assinado, buttons16 e stop16. O servidor preenche o hash FNV de bytes no campo de integridade do pacote; o sub confere tamanho, magic, tic e hash antes de usar.

O frame completo é preparado pelo sub no offset1000 de seu banco Word RAM, antes de publicar o pedido. Cabeçalho32: magic53324446, versão1, tic, total, worldbytes, actorbytes, status, checksum. Câmera32 no offset32, player24×u32 no64, dois psprites16 no160, input eco16 no192. Blobs começam no256: um frame completo de mundo e um de atores/R24 nos formatos S2b/S2c, com count1. Limite combinado16384 bytes e limite8192 por blob. Checksum do frame cobre todos os bytes, zerando o próprio campo. Limites são conferidos antes de copiar.

A cada tic os produtores S2b/S2c reiniciam seus buffers e emitem estado completo; não acumulam os2600 tics anteriores e não conservam snapshots em lote. A variante SCD_LIVE altera apenas essa política e o count; os builds anteriores seguem com27 amostras. Os limites anteriores de atores e IDs continuam explícitos e falham fechados quando excedidos.

## MD e bancos alternados

Depois de ACK/DONE e mudança real de ownership, o MD valida o frame recebido em601000. Salva o cabeçalho/câmera/player em61A000, copia mundo para600000 e atores para608000, aplica os campos nativos e reconstrói listas de sprites pelos mesmos validadores S2b/S2c. As regiões de cópia são ordenadas e os limites impedem sobreposição destrutiva com a origem dos atores.

Os dois bancos1M alternam a cada transação. Dados persistentes em Word RAM não podem ser considerados estáveis entre swaps. O runner guarda os backups originais de R24/listas/jogador num temporário MD de256 palavras32 (1024 bytes de stack), com bound de contagens; reinstala esses backups no banco recém-recebido antes de aplicar o frame. Proxies e relatórios são reconstruídos a cada troca. O sub não toca a região de backups. A saída pode ocorrer em qualquer paridade de banco.

Aplica câmera, saúde/armor/ammo, arma/owned, contadores/powers e psprites com stateID remapeado para states local; ações de estado não rodam no MD. G_Ticker MD só pode voltar após o encerramento. Não há alegação de sincronização de todos os campos internos de player ou de áudio.

## Testes

`test_live.py` verifica boot18 requests/0errors/marcador5A9D, injeta botões pela mesma função de tradução usada pelo pad físico (override de depuração padrão desativado), confere a sequência/input eco, checksums, valores de mundo/atores aplicados, listas nativas por setor e framebuffer. Exige movimento, giro e consumo de munição após ataque, alternância real dos dois bancos, ausência de G_Ticker/P_Ticker MD durante o modo CD e saída restaurada ao G_Ticker original. START físico e sensação do controle ficam para o teste de console.

## Resultado integrado — 2026-11-08

Commit `adbe47283f1dd9daf1ca15342b9db776e6870871`, Actions run `42480397654`, job `128730857363`: build e gate completo PASS, incluindo Z4/Z5/Z7/Z8/S2a/S2b/S2c.

- Sub: payload87324 bytes, `_end=0x5CE10`, abaixo do limite0x68000; heap128 KiB. A ROM inteira permanece linear,4063232 bytes, dentro de4 MiB. Nenhum snapshot em lote é exigido para jogar.
- Boot confirmado pelo teste: stage5,18 requests,0errors, marcador5A9D. O diagnóstico desta variante é de prontidão para jogo interativo; não imprime hash da demo nem diz2600TICS/REBIRTHPASS. A regressão separada S2c continua provando os2600 tics e o reinício.
- Recebidos/aplicados estados0–97:98 estados,97 quadros renderizados e97 G_Ticker sub entre o estado inicial e o stop. Câmera, mundo, atores/R24 e listas nativas MD foram conferidos por estado; arma/flash também comparados nos campos MD após remapeamento.
- Comandos de avanço/giro/disparo foram ecoados corretamente pelo sub no estado seguinte. Movimento/ângulo e imagens realmente mudaram; munição50→45, com efeitos novos e removidos no conjunto de atores. Máximo50 atores dinâmicos nessa amostra. O bit de uso também foi enviado e ecoado; não alegar que o percurso automatizado abriu uma porta.
- Ownership alternou4/5 a cada troca TIC, sem congelar o sub por pedido de barramento PRG-RAM. Nenhum G_Ticker/P_Ticker MD durante o modo CD. Saída instrumentada pelo mesmo flag stop usado por START restaurou o estado local previsto e alcançou G_Ticker MD: PASS.
- O override de controle de depuração começa emFFFF (desativado); sem o teste, os comandos vêm de JOY_update/JOY_readJoypad. O teste automatizado comprova a tradução e execução dos comandos injetados; o pad físico/START e a sensação de controle ainda precisam do console.
- Nenhuma conclusão de FPS,35Hz ou latência é extraída do tempo do teste com debugger. O caminho atual envia estado completo e deve ser otimizado após a validação física. Áudio de eventos, troca de nível e inventário completo não estão cobertos como jogo final.

ROM privada: `/home/dan/Projetos/Personal/scd-subport-s2d-live/run-42480397654-1/doom-md-scd-s2d-live.bin`.
Mesmo diretório: `live_report.json`, `live-frame-001.bin`,016/032/064/096, ELF e relatórios de link. ROM/WAD/ELF/frames permanecem privados.

## Teste físico

Sega CD ligado/conectado. Abrir a ROM, aguardar S2D LIVE SUB LOGIC READY / TRANSFER PASS /18requests0errors. Apertar e soltar START ou aguardar o início automático. Deve aparecer S2D LOGIC ON SEGA CD / LIVE INPUT. Direcional anda/gira; A usa portas/reativa após morte, B atira; C+direção corre/strafe. START sai para título/menu MD. Agora o percurso depende do controle; não é a demo de100 em100tics.

Este primeiro teste é de funcionamento e controle. Registrar se andar/girar/atirar/usar funcionam, se a arma/HUD acompanham e se START retorna. Não exigir velocidade final: o próximo passo é reduzir bytes/escritas, desacoplar render da cadência de tics e medir tempo de CPU, transferência e latência. Preservar S2c aprovada como referência.

As primeiras iterações desta etapa corrigiram o acesso ao inicializador privado e o sentinel wp_nochange (NUMWEAPONS+1). O gate final acima passou integralmente. Um processo BlastEm encerrou com EOF numa regressão S2a de uma tentativa anterior; a execução integral final, incluindo essa regressão, passou sem relaxar checks ou adicionar retries de runtime.
