# Cláudio — avaliação do subport Sega CD após S2e

Data: 2026-11-08. Pedido do Daniel: **“faça um handoff para claudio avaliar”**.

## 1. Pedido de avaliação

Avalie a arquitetura atual, a validade da medição e a ordem do próximo trabalho. O port já aceita controle real com lógica no Sega CD, mas continua muito lento. A primeira otimização retirou boa parte do custo de transferência/diagnóstico; agora renderizar/apresentar no MD domina o orçamento.

**Decisão principal solicitada:** priorizar a cadência de lógica35Hz, otimizar mais o renderer MD, migrar o renderer para o sub como previa o plano original, ou combinar essas frentes em marcos separados? Recomende uma primeira mudança concreta, mensurável e reversível, com critérios de aprovação.

Este documento é um handoff técnico para revisão; não é uma exportação integral da conversa. Os relatórios detalhados estão referenciados abaixo.

## 2. Base exata para ler e reproduzir

- Repositório: <https://github.com/bollux78/MD-DOOM64KB>.
- Branch atual: `exp-werk-scd-subport-s1s2`.
- Código funcional/performance validado: `9d466431941339cd78c8746fc27baba1f9675d0b`.
- Documentação consolidada antes deste handoff: `63b6cf5f1eb9810afd77afcf92365dccfa1ccb38`.
- Gate completo: [Actions42483932970](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42483932970), job128741595681, PASS.
- Workflow: `.github/workflows/scd-subport-s1b.yml`.
- Ler primeiro: [SCD-S2E-PERFORMANCE.md](SCD-S2E-PERFORMANCE.md), depois [SCD-S2D-LIVE-TICS.md](SCD-S2D-LIVE-TICS.md), [SCD-S2C-ACTORS-BRIDGE.md](SCD-S2C-ACTORS-BRIDGE.md).
- Plano/arquitetura original: [SCD-SUBPORT-S1S2-CLAUDIO.md](SCD-SUBPORT-S1S2-CLAUDIO.md). As seções antigas têm estados históricos; as entradas mais recentes no topo prevalecem.

**Importante sobre nomes:** S2a–S2e são os nomes dos marcos incrementais desta implementação. Isso **não significa que o S2 completo do plano original esteja concluído**: o renderer continua no MD. O sub executa a lógica e produz estado, não pixels.

## 3. O que foi aprovado, e por quem

| Marco | Prova atual |
|---|---|
| Simulação CD original,2600 tics e reinício controlado separado | Testes automatizados e aprovações anteriores no console |
| S2a câmera, S2b setores/sides, S2c atores/R24 | Aprovados pelo usuário no console |
| S2d interativa | Usuário confirmou funcionamento correto no console e relatou aproximadamente1FPS |
| S2e otimizada | Gate completo e comparação emulada PASS; **sem nova medição física até este pedido** |

Trechos humanos exatos que delimitam o estado recente, na ordem:

> funcionou corretamente no console. agora é melhorar o desempenho que nesta esta a 1 fps

Após a entrega da S2e, a próxima mensagem foi:

> faça um handoff para claudio avaliar

Portanto, não registrar3,15FPS como resultado de console nem presumir uma aprovação física da S2e.

## 4. Arquitetura realmente em execução

### Sega CD

Usa o G_Ticker original, P_Ticker e a lógica de mapa/atores da árvore R128 gerada, com adaptação de plataforma e WAD residente. O build verifica que o corpo G_Ticker permanece igual à fonte original. Um wrapper acessa G_InitNew, que é privado no módulo original, e um setter externo preenche o netcmd; não substitui a lógica do ticker.

O sub tem geometria em RAM, cache WAD128KiB, heap128KiB e representação R24 dos itens estáticos. Registra spawn/remove/reset de atores para produzir IDs monotônicos, sem transmitir ponteiros. Cada troca entrega um estado e recebe o input para o próximo tic. Som e vídeo do sub continuam nas fronteiras de plataforma; áudio de eventos não é transportado.

### Mega Drive

Mantém o engine R128 para inicialização local, renderer nativo, conversão/apresentação e retorno ao título. Durante o modo CD, não executa G_Ticker/P_Ticker MD. Aplica campos visuais de setores/sides com R23_GET/R23_SET onde necessário, reconstrói proxies de atores por setor em Word RAM e chama o renderer original.

Câmera, saúde/armadura/munição, armas, powers e psprites de arma/flash acompanham o estado CD. Targets, thinkers e links de colisão do CD não são copiados. Os proxies MD servem à apresentação, não a uma segunda simulação. START envia stop, restaura as listas/jogador/itens locais previstos pelo protótipo e retorna ao ciclo original do MD.

### Restrição funcional mais importante

**Uma troca ainda corresponde a um G_Ticker e um quadro. A lógica não está desacoplada do FPS.**3,15 quadros/tics por segundo não equivalem a uma simulação Doom normal de35Hz: são aproximadamente9% dessa cadência. O protótipo aceita controle, mas não deve ser descrito como jogo em velocidade temporal normal.

Esta é uma frente distinta de aumentar FPS. Favor avaliar acumulador, lote de tics, limite de recuperação e amostragem de input antes de mudar o protocolo. Não simplesmente incrementar gametic por vários tics sem executar a lógica correspondente.

## 5. Protocolo e memória que não podem quebrar

Transporte1M com sequências nãozero, ACK/DONE e ownership real. MD é o único iniciador da troca pelo mailboxA12018; **não introduzir DMNA**. DIR/LUMP continuam no mesmo servidor. O sub publica o frame no banco que possui; depois da troca o MD possui esse estado, e o sub possui o próximo comando.

S2e usa magic53324546, versão2, marcador de boot5AAD. Input16bytes mantém FNV e inclui tic esperado, avanço/strafe/giro/buttons/stop. Frame inclui cabeçalho/câmera/player/psprites/input ecoado e blobs de mundo/atores. Limite total16384bytes, limites individuais8192bytes, alinhamento e ordem conferidos antes de aplicar.

| Área | Uso |
|---|---|
| PRG-RAM sub,512KiB | Código/BSS/heap/cache e buffers reservados |
| `_end=0x60680` | Fim linkado da S2e; guard exige `<0x68000` |
| Sub0x68000–0x73FFF | Reserva de stream de atores,49152bytes; no modo live contém somente o frame corrente |
| Sub0x74000–0x7BFFF | Reserva de stream de mundo,32768bytes |
| Word RAM MD0x600000 | Mundo aplicado/copied blob |
| MD0x608000 | Blob de atores |
| MD0x614000–0x616FFF | Proxies nativos, bound de `64*sizeof(mobj_t)` |
| MD0x617000 | Registros reextraídos dos campos nativos para auditoria |
| MD0x61A000 | Cabeçalho/câmera/player recebido |
| MD0x61B000 e seguintes | Relatórios; perfil em61B140 |
| MD0x61C000/61C800/61CC00 | Backups para a saída |

Payload sub87424bytes **não é RAM total**: há BSS/cache/heap além do payload. Loader atual admite imagem de até128KiB em uma janela. ROM linear4063232bytes, dentro de4MiB. Atores dinâmicos: máximo64 vivos; IDs16 monotônicos, com falha explícita ao esgotar65535 criações. R24: máximo512 entradas.

**Os bancos Word RAM alternam.** Dados persistentes neles não sobrevivem por identidade de endereço entre trocas. O runner guarda os backups de saída num temporário MD de256palavras32 (1024bytes de stack) e reinstala os backups no banco recebido; proxies são reconstruídos. Qualquer novo paralelismo, buffering ou mudança de ownership precisa revisar a vida útil desses ponteiros/dados e o orçamento de stack.

As reservas de stream são grandes em relação ao frame live atual; podem ser candidatas a reaproveitamento numa migração de renderer/cache, mas não mover áreas sem revisar guards, loader e stack.

## 6. O que a S2e mudou

1. Setores/sides completos na primeira amostra; depois somente campos alterados. O estado persistente fica em RAM/SRAM MD nativa. R24 removed/delay também usa deltas. Atores dinâmicos ainda são snapshots completos por frame.
2. Cópias alinhadas32bits, em vez de loops por byte.
3. Removeu dois checksums de byte internos redundantes. O pacote completo usa checksum de palavras32: rotacionar5bits, XOR com palavra e somar9E3779B9, módulo32, zerando o próprio campo. Input mantém seu FNV. Não é proteção criptográfica.
4. Auditoria FNV completa do estado nativo MD no frame0 e a cada32tics no modo de uso. Nos demais, hash aplicado0 e checked0 explícitos. O CD ainda produz o hash canônico de todo o estado em cada tic.

**Não foram desligados os checks de cada pacote:** versão/tic/ownership/checksum/alinhamento/limites, tipos/IDs/estados e validação espacial dos atores continuam ativos. `s2e_test_deep=1` força auditoria completa em todos os quadros para testes. Padrão físico0.

Rever especialmente se essa separação de auditoria/uso é apropriada, se o checksum cobre todos os dados necessários e se a estratégia de deltas se mantém correta após recarga/reinício. Não há validação de campanha ou mapas com contagens diferentes.

## 7. Medição e provas

Contador NTSC `_g_vblankCount` interno à ROM, não tempo de parede do debugger. CPU divider MD7 no BlastEm. Mesmo roteiro de controle;94 amostras, estados2–95, excluindo inicialização/saída. A medição não separa execução da lógica CD de serialização CD: tempo de trabalho no sub pode estar oculto pelo trabalho simultâneo no MD. Espera MD0 não significa que a lógica CD custe zero ou já possa sustentar35Hz.

| Média por quadro, VBlanks | S2d | S2e de uso |
|---|---:|---:|
| Espera/sub+swap | 0 | 0 |
| Checagem/cópia/backups | 27 | 1 |
| Aplicação/auditoria de mundo | 12 | 0,149 |
| Atores/player | 6 | 3,638 |
| Render/DMA | 14,160 | 14,255 |
| **Total** | **59,160** | **19,043** |
| **FPS equivalentes60Hz** | **1,014** | **3,151** |
| Pacote médio, bytes | 7730,21 | 2678,55 |

Ganho emulado3,1067×, pacote65,35% menor. Render/DMA agora é74,9% do total. Mantendo esse custo intacto e zerando todo o resto, o teto **desta amostra** seria aproximadamente4,2FPS; não é teto universal do hardware.

Testes que passaram:

- Regressões de setup/geometria, lógica2600tics, decoder original e reinício controlado, câmera, mundo e atores.
- S2d controle e S2e em dois processos do **mesmo binário**: auditoria profunda em todos os98 estados; depois padrão de uso com checkpoints0/32/64/96.
- Input ecoado na ordem, movimento/giro efetivos, consumo de munição50→45, arma/flash, listas espaciais nativas, tipos/índices e alternância dos dois bancos.
- Trajetória/dados iguais entre os dois modos S2e e SHA256 iguais dos97 framebuffers renderizados. Isso é cobertura do roteiro, não prova de todas as cenas ou do scanout físico completo.
- Zero G_Ticker/P_Ticker MD antes da saída; stop instrumentado restaurou a saída ao G_Ticker original. START físico da S2e ainda depende do console.
- Checksum C/Python e352 corrupções de um bit: PASS.

A visão aproximada R128 pode produzir trajetórias diferentes quando o layout de memória muda. O usuário aceita divergência em relação à demo MD se o jogo funcionar; reportar a divergência. Não confundir isso com tolerar pacote/estado aplicado incorreto. O teste profundo/periódico usa o mesmo binário e exige equivalência do roteiro e das imagens.

Uma tentativa anterior teve EOF de inicialização do BlastEm no teste Z7 e, em consequência, falta de CSV no comparador. Não foi contada como gate aprovado. O gate final passou completo. Não foram adicionados retries de runtime nem relaxados critérios para esconder essa falha.

## 8. Arquivos e reprodução

| Arquivo | Papel na revisão |
|---|---|
| `experiments/DOOM_SCD_SubPort/s2d/sub_live.c` | Loop G_Ticker CD, produção do pacote e input |
| `s2d/md_live.c` | Loop MD, controle, aplicação, render, backups e perfil |
| `s2d/live_wire.h` | Wire v1/v2 e checksum por palavras |
| `s2d/live_build.py` | Instalação em árvore descartável |
| `s2b/sub_world.c`, `s2b/md_world.c` | Produção/aplicação de mundo e auditoria |
| `s2c/sub_actors.c`, `s2c/md_actors.c` | IDs, atores/R24, listas nativas e auditoria |
| `s1e/engine_build.py` | Adaptações de plataforma e assert do G_Ticker original |
| `scd_sub_transport.c`, `scd_md_server.c` | Sequências, DIR/LUMP/TIC, input e swaps |
| `s2d/test_live.py`, `s2c/test_actors.py` | Decodificação independente e provas de aplicação |
| `s2e/compare_perf.py` | Comparação dos contadores e equivalência profunda/uso |

Todos os caminhos abreviados nessa tabela são relativos a `experiments/DOOM_SCD_SubPort/`. O workflow contém as variáveis e a sequência completa de preparação.

```bash
python3 experiments/DOOM_SCD_SubPort/s1d/build_setup.py "$tree" "$S1A_OUT" "$ram" "$out" --fast
```

No ambiente do runner, com `BLASTEM` e `PYTHONPATH` preparados pelo workflow:

```bash
python3 experiments/DOOM_SCD_SubPort/s2d/test_live.py --fast "$S2E_OUT/doom-md-scd-s2e-fast.bin" "$S2E_OUT/doom-md-scd-s2e-fast.elf"
python3 experiments/DOOM_SCD_SubPort/s2d/test_live.py --fast --production "$S2E_OUT/doom-md-scd-s2e-fast.bin" "$S2E_OUT/doom-md-scd-s2e-fast.elf"
python3 experiments/DOOM_SCD_SubPort/s2e/compare_perf.py "$S2D_OUT/live_report.json" "$S2E_OUT/live_report.json"
```

ROM S2e privada:

```text
/home/dan/Projetos/Personal/scd-subport-s2e-fast/run-42483932970-1/doom-md-scd-s2e-fast.bin
```

Nesse diretório estão `live_deep_report.json`, `live_report.json`, `performance_comparison.json`, frames, ELF e relatórios de link. Controle S2d perfilado: diretório equivalente `scd-subport-s2d-live/run-42483932970-1/`. A referência física aprovada original é a S2d do run42480397654.

O trabalho é compilado/testado no runner self-hosted do Daniel, com SGDK/m68k-elf e BlastEm. Não há cross-compiler local neste workspace de revisão. Não publicar WAD/ROM/ELF/frames. Não limpar/resetar o checkout original `/home/dan/Projetos/doom-md`; builds modificam cópias descartáveis.

## 9. Perguntas que o Cláudio deve responder

1. **Cadência:** como manter35Hz de lógica sem uma serialização completa por tic e sem ampliar desnecessariamente a latência de input? Qual política de lotes/recuperação/cap deve ser testada primeiro?
2. **Render:** o custo14,25VBlanks inclui rasterização, conversão, upload e espera DMA. Qual instrumentação separa esses custos antes de escolher CPU CD, ASIC ou otimização MD?
3. **Migração:** qual é o menor subconjunto `r_*` que permite um primeiro framebuffer real no sub, aproveitando o plano S2 original? Medir fonte/link/heap/cache/texturas antes de presumir que cabe. Revisar loader128KiB, tabelas grandes e reservas de stream reaproveitáveis.
4. **Aplicação de atores:** vale transportar subsectorID/cache espacial ou compactar snapshots para reduzir os3,64VBlanks restantes? Como manter validação e vida útil dos proxies entre bancos?
5. **Validação:** o roteiro atual e a auditoria periódica bastam para a próxima ROM? Que casos acrescentar para porta, coleta, morte/reinício, travessia de setor, limite de atores e saída por START?
6. **Ordem:** proponha um marco jogável com comparação A/B na mesma cena e métricas explícitas, sem reduzir resolução/qualidade ou alterar IA silenciosamente.

A recomendação deve distinguir **resultado demonstrado**, **hipótese** e **trabalho proposto**. Não implementar uma grande migração antes de concluir essa avaliação e definir o primeiro experimento.

## 10. Integridade e limite deste handoff

Brief técnico reconstruído do contexto desta tarefa, dos arquivos atuais e dos relatórios no repositório. Contém2 mensagens humanas recentes reproduzidas literalmente e0 respostas de IA transcritas; a abertura reproduz também o pedido atual como metadado. Não é uma transcrição integral, e não afirma completude da conversa. Não inclui dados pessoais de outras tarefas, instruções internas, raciocínio privado, credenciais ou assets do jogo.

Os dados de CI e os números acima foram conferidos com o relatório atual de performance e com o estado consolidado da branch. S2e permanece sem resultado físico informado. Não há nova execução de código de jogo neste pedido: é uma entrega de documentação para avaliação.
