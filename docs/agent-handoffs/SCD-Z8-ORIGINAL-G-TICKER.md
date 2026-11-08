# Z8 — G_Ticker original de nível no sub-68000

## Escopo autorizado

Após Z6 aprovada no console e Z7 comparar 27 checkpoints independentes, o usuário autorizou P_Init + G_Ticker no Sega CD, com morte/reinício. Z6 e seus artefatos privados permanecem preservados.

## Implementação

- `s1e/engine_build.py` compila `src/g_game.c` original do repositório para o sub, sem os hooks de benchmark/menu R116 exclusivos do MD. Mantém o corpo inteiro de G_Ticker e verifica por comparação literal que não foi modificado. Decoder original G_ReadDemoHeader/G_ReadDemoTiccmd e G_InitNew/G_DoLoadLevel/G_DoReborn permanecem reais. G_DoLoadGame/G_DoSaveGame falham explicitamente: não há SRAM no sub.
- Demais módulos de lógica são os R128 gerados já usados nas Z5–Z7, recompilados para PRG-RAM direta. Não há substituição de IA, física, spawns ou respawn.
- `SCD_MetadataInit` lê TEXTURE1 real e obtém numtextures. O lookup original de `r_data.c`, a lista original de switches e P_InitPicAnims são executados. P_Init omite apenas R_InitSprites, cache gráfico que continua sendo responsabilidade do MD. Não carrega TEXTUREP com imagens de paredes.
- ST_Start/ST_Ticker/HU_Start/HU_Ticker são fronteiras de apresentação sem saída no teste. Áudio permanece silencioso. AM_Ticker/AM_Stop são originais. Intermissão, final, título, save/load e fim da demo antes do orçamento falham explicitamente; esta etapa cobre o ciclo de E1M1, não todos os estados do jogo final.
- `engine_libc.c` fornece strings SGDK/ASCII e memcmp requeridos pelo decoder e lookup; memcpy/memset vêm do objeto sub já validado.
- `s1e/sub_engine.ld` garante KEEP(.text.vectors) no endereço 0 antes de .text.unlikely.*; alinhamento de dados/BSS e orçamento de PRG-RAM/trace verificados. Aplica-se apenas à Z8, sem alterar layout/hash das versões aprovadas.
- A instrumentação MD da Z7 é desfeita na cópia gerada ao empacotar Z8, restaurando o R128 normal após START. Backup/restauração só na árvore descartável.

## Teste

1. Z_Init, W_Init, TEXTURE1/P_Init e AI Normal.
2. DTE1M1 privado (10414 bytes, Doom 1.9 UV E1M1) via servidor MD; G_DeferedPlayDemo inicia o decoder original.
3. 2600 chamadas naturais de G_Ticker; 27 checkpoints de estado, t=0 observado dentro do primeiro P_Ticker real. Checkpoints referem-se ao ordinal de comandos, não a leveltime (que pode reiniciar).
4. Depois de encerrar/gravar o trace natural, uma prova SEPARADA pede uma demo nova, executa um tic e injeta PST_REBORN como estímulo controlado. G_Ticker original precisa recarregar o mapa, retornar jogador vivo/saúde 100/leveltime=1; Z_CheckHeap precisa passar. Não descrever o estímulo como morte/respawn natural da demo.
5. Metadados PRG-RAM 0x7C360: 2600, controlled_rebirth_pass=1, first_dead_natural_tic, final_probe_leveltime=1. Trace ocupa 864 bytes antes desses 16 bytes. MD copia tudo para 0x61E000; teste independente confere hash, movimento, metadados e fallback MD.
6. Sucesso exclusivo 0x5A8D, 12 requests (DIR, TEXTURE1, demo, nove lumps), zero erros/timeouts. UI: S1E Z8 REAL G_TICKER / 2600 TICS AND REBIRTH PASS. Estado/trace retornado ainda não alimenta o renderer.
7. Heap 224 KiB, cache WAD 128 KiB, payload limitado à janela de boot 128 KiB e _end inferior a 0x7C000; stack no topo de PRG-RAM.

## Histórico de correções

- dcaa07b / run 42429001612: link estrito falhou só em memcmp, strlen e R_InitSprites; nenhuma execução Z8.
- b1b009d / run 42429332111: link estrito de 43 objetos PASS; validação bloqueou layout de reset (bad boot vector). A seção cold do GCC veio antes dos vetores no script padrão.
- f11a4ec: restaura fallback R128 normal após instrumentação Z7.
- b1cd0d2 / run 42429675015: linker explícito passou; sub payload 82450 bytes, RAM end 0x73950. Build MD parou por objeto de observador Z7 ainda presente depois da restauração. Nenhuma execução Z8 nessa rodada.
- 34639e9: remove o fonte/objeto/dependência do observador MD na árvore descartável após restaurar o fallback normal.

## Resultado final

**Build/link estrito PASS / BlastEm PASS / hardware NOT TESTED.** Run [42430167033](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42430167033), commit `34639e904afdd5f2f315fbfcf6b9ffd8b5c9ebec`. Workflow SUCCESS, regressões Z4/Z5/Z7 PASS.

- Link estrito 43 objetos; payload sub **82450 bytes**, `_end=0x73950`, vetores no zero. Heap 224 KiB/cache 128 KiB e 0x7C000 reservado ao trace respeitados.
- Sub: stage=5, marcador=0x5A8D, served=12, bytes=69151, errors=0, timeouts=0, último tic natural=2600.
- Trace natural: **27 checkpoints**, movimento e hash **0A1B0220** recalculado a partir da cópia PRG-RAM → Word RAM, PASS.
- G_Ticker natural: jogador morreu no tic **2334**; final natural health=0, mobjs=34, prndindex=118, x=69126796, y=-240122343, z=0, angle=927805423. Não afirmar sobrevivência nem respawn natural dessa amostra.
- Prova controlada, separada e posterior ao trace: `controlled_rebirth_pass=1`, `final_probe_leveltime=1`, jogador PST_LIVE/health=100 e Z_CheckHeap PASS. Inclui duas chamadas extras de G_Ticker além das 2600 do trace, executando uma demo nova e o estímulo PST_REBORN. Não incluir esse estímulo nos dados de comparação natural.
- Comparação MD original: tic 0 coincide; primeiro checkpoint divergente 100, agora **somente prndindex** (MD 47/sub31). Posição, ângulo, saúde e mobjs=37 coincidem nesse checkpoint. A trajetória/saúde divergem no checkpoint200. Não é paridade bit a bit, nem causa exata isolada. Fonte conhecida de divergência potencial continua R128 sight por endereço do mobj.
- Fallback G_Ticker MD PASS; instrumentação automática Z7 retirada dos fontes e objeto ao empacotar esta ROM. Verificação automatizada alcança o ticker MD, não um benchmark completo do fallback após START.
- **ROM para console:** `/home/dan/Projetos/Personal/scd-subport-s1e-z8/run-42430167033-1/doom-md-scd-s1e-z8.bin`.
- Tela esperada: `S1E Z8 REAL G_TICKER`, `TRANSFER PASS / STAGE 5`, requests12/errors0/bytes69151, `STATE HASH 0A1B0220`, `2600 TICS AND REBIRTH PASS`.
- Procedimento físico: Sega CD ligado/conectado, abrir ROM e aguardar sem START; fotografar diagnóstico antes do timeout de15segundos, depois START e confirmar R128 normal no MD. Ainda não há imagem 3D gerada a partir do estado sub.
- CSV/ELF/comparison.json privados na mesma pasta da ROM. Nunca publicar WAD ou ROM em GitHub.


## Próximo marco

Homologação física da Z8 após PASS no BlastEm. Depois: snapshots do estado do sub para o MD, entrada contínua e renderização alimentada pela lógica sub; medir custos de transferência e FPS real. Não prometer ganho FPS a partir de um teste sem renderização.
