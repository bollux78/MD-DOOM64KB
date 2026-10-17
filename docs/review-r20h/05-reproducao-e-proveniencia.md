# Reprodução, proveniência e limites

## Fonte congelada

Commit8d875327922a7f6bedd3142dbafda02d628c4fbd;cada blob de source foi comparado ao SHA Git retornado pela árvore remota, usando SHA1 de `blob <tamanho>\0<conteúdo>`. Nenhuma divergência. SHA256SUMS do handoff cobre todos os arquivos entregues, exceto ele próprio. Não confundir esses hashes de integridade com checksum do cabeçalho Sega.

A revisão anterior acompanha o pacote em previous-review, sem seus binários/benchmarks executáveis;serve para identificar o que já foi sugerido. As conclusões atuais constam nos documentos01–04.

## Build

Ver `source/scripts/lab/build_r20h.fish`, `r20h_matrix.json`, `r20h_flags.py` e `.github/workflows/r20h.yml`. Requer WAD e SDK externos conforme script. No runner do usuário:SGDK em~/Projetos/marsdev/sgdk/SGDK;GCC15.2.0. Os caminhos efetivos são resolvidos pelos scripts/variáveis; não presumir disponibilidade desses caminhos nesta máquina.

Para uma reconstrução limpa da matriz em checkout com dependências disponíveis (fish):

```fish
set -e DOOM_R20H_REUSE
set -gx DOOM_R20_BGM_VGM /caminho/absoluto/e1m1.vgm
fish scripts/lab/build_r20h.fish
```

Preparar E1M1 a partir do assetxz e verificar hash conforme workflow,ou fornecer o VGM correto. O build da vencedora exige todas as flags exatas em `evidence/flags-doom-md-r20h-vc-all.txt`; um make padrão não é necessariamente essa ROM. TIMEDEMO é definida; versão jogável futura precisa seleção própria.

A CI h final reutilizou36ROMs já compiladas do run39045298927,verificadas em144arquivos selados(BIN/ELF/flags/log),e compilou as4restantes após encurtar nomevc-all. Código do motor não mudou. Ver `r20h_reuse.json` e `verify_r20h_reuse.py`. Não reutilizar binários após mudar engine/flags/toolchain. Primeiro run falhou por nome>30caracteres, não por erro do jogo.

ZIP original40ROMs:SHA256af8fa760f0f67d94ba68d6566db45b63ebfd9e360cd4668fe12b453c206df7c3. Os logs/flags/ELF da vencedora e controles estão neste pacote. O ZIP original inclui todas as demais evidências.

## Testes existentes

`test_r20a.py`,`test_r20b_math.py`,`test_r20d_sources.py`,`test_r20g.py`,`gen_r20g_probe.py`,`build_r20g_evidence.py`. Ler cada teste para distinguir cobertura real de checagem de texto. A CI conferiu matriz40,pareamento e cobertura2^4,IDs/bounds e hashes.

Testes de equivalência:507904estados de colisão/cache;6712colunas WAD;probe MC68000 de768spans com guardas e1054vetores de matemática. Probe inclui caminhos reais deP2/P3,R5/R6/M2;testar opção perdedora no probe não a habilita na vencedora. Mock deV2 exercita1000frames,mas não valida timing do VDP.

O harness Musashi é emulador deCPU puro, NÃO emulador deMegaDrive. `.raw` da evidência é probe,nãoROM de jogo. Exigir marcador `tag0`,não apenas exit0. O ELF pode conter `.data` inicializada fora de`.text`;o teste rigoroso carrega todas as seçõesSHF_ALLOC nãoNOBITS. Execuções anteriores:raw231528550ciclos;imagemcompletaELF234062986ciclos;ambastag0. Esses ciclos NÃO são o tempo deDEMO3.

## Validação experimental futura

MesmaDEMO3,2134frames,NTSC60Hz,7,67MHz,controle na mesma sessão. Repetir finalistas para avaliar variação;diagnóstico antes do desempenho. No hardware observar paredes/fullbright,chão/teto,sprites/arma,HUD,música/transições. Novos mapas para limites de memória. Registrar falha com ROM,frame/tic,erro,SP e heaps;nomes ausentes só podem ser inferidos por conjunto completo e devem continuar marcados como inferência.
