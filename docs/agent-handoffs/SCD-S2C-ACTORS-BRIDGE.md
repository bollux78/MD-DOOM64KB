# S2c — atores e itens do sub no renderer MD

## Escopo autorizado

S2b confirmada no console pelo usuário, com autorização para continuar. A S2c acrescenta o estado visual dos atores e dos itens estáticos R24 à câmera e aos setores/sides. Continua sendo replay em lote: o sub roda 2600 tics primeiro e o MD desenha as 26 amostras seguintes. Não há input ao vivo, áudio/HUD completo sincronizado, colisão local com proxies ou medida de FPS offloaded.

## Atores e IDs

Somente na variante S2c, o build do sub acrescenta observadores ao fim do P_SpawnMobj, após o filtro R24 do P_RemoveMobj e no início do P_InitThinkers. Cada criação recebe ID16 monotônico, sem reutilização durante a execução. O reset do mapa limpa referências vivas, mas não o contador de IDs. Limite explícito: 64 atores dinâmicos vivos e 65535 IDs criados; excesso falha com I_Error. Não há ponteiro ou endereço sub no wire. A lógica de spawn/remove, o corpo G_Ticker e o estado RNG não são substituídos pelos observadores.

Cada amostra inclui todos os atores dinâmicos vivos, inclusive jogador, decoradores dinâmicos e efeitos que existam naquele instante. Registro de 36 bytes big-endian: ID/type16; x/y/z32; angle/flags32; state/sprite/frame16; health/tics assinados16; sector16. IDs de estado e tipo são remapeados para as tabelas locais MD. Targets, thinkers e ponteiros de contato não são transmitidos.

## Itens R24

As variantes anteriores do sub não usavam R24; a S2c passa a usar a representação R24 dos itens estáticos, como o MD. Recompila P_SetupLevel, P_Mobj e P_Maputl com R24, além do módulo original r24_romthings. Os seis lumps de índices/itens vêm pelo transporte WAD. No helper de projeção sub, sector_index é substituído pela diferença de ponteiros na tabela RAM; os seis nomes de lumps são formados sem sprintf. A lógica de seleção, colisão/coleta e animação R24 permanece original.

A primeira amostra inclui removed/delay de todos os itens R24; as seguintes incluem apenas entradas alteradas. Assim, a animação estática continua usando o leveltime real do sub e os atrasos originais por item. Itens coletados deixam de ser projetados. Limite explícito: 512 itens R24. Alterações de delay após recarga do mapa também são transportadas.

## Memória e formato

- Stream dos atores: PRG-RAM 0x68000–0x73FFF, 49152 bytes. O build bloqueia `_end >= 0x68000`; heap da S2c: 128 KiB. Mundo S2b permanece na reserva 0x74000–0x7BFFF; câmeras/trace nas áreas superiores anteriores.
- Cabeçalho8×u32: magic53324342, versão1, count27, quantidade R24, bytes usados, checksum de bytes, stride36, reservado. Offsets27×u32 a partir do byte32; registros começam no byte256.
- Frame16: tic32, quantidade de atores16, deltas R24 count16, hash canônico32, playerID16, reservado16. Depois os atores36 e deltas R24 de8 bytes `[index,removed,delay,reservado]` u16.
- Hash canônico: contagens de atores/R24, playerID, os13 valores de cada ator na ordem do pacote e `[removed,delay]` de todos os itens R24 em ordem de índice. FNV numérico32, valores assinados estendidos. Checksum do stream: FNV por byte, campo próprio zerado.
- Após o sub terminar, MD copia a janela banco3 em0x428000 para Word RAM0x608000. Stream limitado antes de copiar.
- Proxies MD em0x614000, no máximo0x3000 bytes. Guard de sizeof(mobj_t)×64. Valores aplicados para auditoria em0x617000. Relatório em0x61B040. Backups privados de itens/listas/jogador em0x61C000/0x61C800/0x61CC00. Não ocupam o BSS de64 KiB do MD e não sobrepõem câmera/mundo/trace.

## Proxies para apresentação

O MD salva as cabeças das listas de atores locais. A cada amostra reconstrói apenas as listas de sprites por setor, apontando para proxies nativos em Word RAM. Cada subsector é recalculado por R_PointInSubsector e comparado ao sectorID do sub; snext/sprev e contagens são verificados. Atores MF_NOSECTOR não entram nas listas. Não cria links de colisão/blockmap, não chama ações de estados e não executa think de ator ou P_Ticker/G_Ticker MD. O jogador original é usado pela câmera, enquanto o ator visual do jogador também existe no conjunto recebido.

Antes de sair por START ou pela flag de depuração, restaura listas locais, flags/delays R24 e posição/câmera/saúde/leveltime do jogador original. Depois usa o retorno ao título já existente. A restauração serve à saída; proxies não são promovidos a uma simulação local jogável.

## Validação

`test_setup.py --actors` prova o G_Ticker natural, 2600 tics e reinício separado. O teste visual independente decodifica todos os atores e deltas R24, verifica estabilidade de tipo por ID, exige criação/remoção, movimento e animação na amostra real, recalcula hashes e compara os registros reconstruídos dos campos MD. Também percorre as listas nativas por setor em Python, verificando membros, ausência de ciclos/duplicatas e ponteiros prev locais. Conserva os checks de câmera, setores/sides, framebuffer/DMA, ausência de lógica MD durante replay e saída ao ciclo original.

Teste local sintético do decodificador com valores assinados, ciclos de vida, item removido e checksum corrompido: PASS. 

## Resultado integrado — 2026-11-08

Commit `0eae23564ccba904a7281f9e75e5ff8c6d2b19bf`, Actions run `42440328871`, job `128607981236`: build e gate completo PASS. Regressões Z4/Z5/Z7/Z8/S2a/S2b também PASS.

- Sub: payload87208 bytes, `_end=0x60590`, abaixo de0x68000. 2600 tics e reinício controlado separado PASS. Hash natural862C5C80; primeira morte no tic510. A fase da visão aproximada pode mudar com layout; esse critério foi aceito pelo usuário. Não usar o hash de outra variante para esta ROM.
- WAD: requests18, bytes72029, errors0/timeouts0, stage5, marcador5A8D. A diferença de6 requests corresponde aos seis lumps R24. A cópia de câmera/mundo/atores é adicional ao contador WAD.
- Atores: stream48432 bytes, de49152 reservados (720 bytes de margem nesta demo). Limite rígido; não extrapolar essa margem para outro mapa ou trajetória. 68 itens R24; máximo55 atores dinâmicos vivos; 122 IDs distintos observados nos checkpoints. 74 entradas e75 saídas entre amostras,142 mudanças de posição,228 de animação,6 mudanças de item para removido e4 restaurações após recarga. São observações entre amostras, não totais de todos os efeitos/ações executados nos2600 tics.
- Mundo nesta variante: stream8796 bytes;85 setores/273 sides;61 mudanças de luz e208 de side, nenhuma alteração de altura/flat na trajetória S2c. A cobertura dinâmica de altura existe no teste S2b anterior, que permanece separado. Não alegar altura dinâmica exercida pela demo S2c.
-27 estados decodificados com hashes válidos;26 conjuntos de atores efetivamente aplicados no MD iguais ao sub, campo a campo; listas nativas por setor percorridas e verificadas independentemente em Python; câmera e mundo exatos, imagens distintas, nenhum G_Ticker/P_Ticker MD durante replay: PASS.
- Saída instrumentada restaurou o estado local e alcançou o G_Ticker original: PASS. START físico da S2c ainda pendente.
- Console: S2b aprovada; S2c pendente do usuário. Não confundir aprovação anterior com esta ROM nova.

ROM privada: `/home/dan/Projetos/Personal/scd-subport-s2c-actors/run-42440328871-1/doom-md-scd-s2c-actors.bin` (4063232 bytes).
Mesmo diretório: `visual_report.json`, snapshots brutos renderizados, `sub_trace.csv`, ELF e relatório de link. Nenhum WAD/ROM/frame foi publicado no repositório.

## Teste físico

Sega CD conectado e ligado. Abrir a ROM e aguardar S2C SUB ACTORS READY / TRANSFER PASS / requests18 errors0 / STATE HASH862C5C80 /2600 TICS AND REBIRTH PASS. Apertar e soltar START ou aguardar início automático. Deve aparecer E1M1 em amostras espaçadas, com rótulos S2C CAMERA WORLD ACTORS FROM CD / OFFLINE REPLAY / START EXIT. Atores e itens acompanham as amostras reais do sub; as mudanças são saltos de100 tics, não animação contínua. Alguns quadros repetidos fazem parte da trajetória da demo e não reprovam isoladamente. START deve retornar ao título/menu original.

Próxima etapa: reduzir o lote para um estado por tic, devolver input do controle ao sub e medir orçamento de transferência/latência. Validar saída/recarga e só então desempenho real. Preservar S2b aprovada e esta S2c até nova aprovação física.
