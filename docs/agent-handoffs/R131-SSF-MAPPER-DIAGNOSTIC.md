# R131 — Diagnóstico de mapper SSF2 para ROMs >4 MiB (BlastEm/MAME e X7 Ultra clone)

Werk → Cláudio, 2026-11-04. **Pedido do usuário:** preparar ROM diagnóstica antes de chegar o EverDrive X7 Ultra clone chinês, anunciado para ROMs até 15 MB, a fim de testar já nos emuladores. Meta posterior: DOOM completo E1–E3, sem mudar a R128 All agora.

## Estado / limites de confiança
- A R128 All é referência de jogo e desempenho; este trabalho é **um laboratório separado** (R131), não uma nova versão do DOOM nem substitui a R129 de backup.
- O modelo X7 Ultra é clone de especificações desconhecidas. Passar no BlastEm ou MAME **não valida o clone**; firmware, PSRAM, decodificação de mapper, SRAM, e compatibilidade só se confirmam no console com o cartucho físico.
- Verificar se a distribuição escolhida de BlastEm e MAME implementa realmente o mapper. BlastEm documenta suporte homebrew SSF2 baseado no cabeçalho. MAME implementa ao menos o cartucho SSF2 oficial; deteção do mesmo cabeçalho em ROM homebrew precisa ser testada, não presumida.
- O mapper SSF2 clássico divide a janela ROM do 68000 (`$000000–$3FFFFF`) em oito janelas de 512 KiB. A primeira (`$000000–$07FFFF`) fica fixa na página 0; as outras usam registradores byte em `$A130F3`, `$A130F5`, `$A130F7`, `$A130F9`, `$A130FB`, `$A130FD`, `$A130FF`. Para identificação, usar campo de sistema do header a partir de `$100`: `SEGA SSF` preenchido com espaços. Fonte: https://www.plutiedev.com/beyond-4mb; changelog oficial BlastEm: https://www.retrodev.com/blastem/changes.html.
- Conservadoramente, **código, vetores, VBlank, handlers, dados de áudio e recursos do Z80 em páginas fixas**; não fazer bank switch de uma janela contendo instruções executadas, VDP DMA em andamento ou leituras de áudio.

## Entrega A: ROM autônoma, sem WAD, sem recursos protegidos
- Gerador/compilador source-only em `scripts/lab/r131_ssf_mapper_diag.py` (ou diretório próprio), com documentação de build para CachyOS + Marsdev/SGDK 2.11 e workflow separado.
- Produzir ROMs `r131-ssf-5m.bin`, `r131-ssf-8m.bin`, `r131-ssf-12m.bin`, `r131-ssf-15m.bin`. Tamanho e nomenclatura inequívocos; indicar claramente MB decimal vs MiB binário e limites de páginas (15 MiB = 30 páginas de 512 KiB).
- Payload sintético (PRNG determinístico), assinaturas/checksums distintos por página em offsets inicial, meio e final; nenhum recurso do DOOM. Definir uma assinatura que não seja repetida por padding ou mapeamento espelhado.
- Boot em página fixa 0: inicializar VDP e mostrar painel legível com modelo de mapper, tamanho ROM, página selecionada, resultado de leitura/correspondência, número de falhas, progresso e erro. Exibir `NO MAPPER / MIRRORED / PAGE READ FAIL / PASS`. Controlador A: próximo teste; B: anterior; C: repetir; START: executar todos. Log serial/arquivo somente se disponível; a tela e um sumário automático precisam bastar.
- Testes básicos: inicializar registradores para mapeamento identidade `1..7`; ler checks de página 0..7 nas janelas correspondentes; alternar uma janela alta (recomendar `$300000–$37FFFF`, `$A130FD`) para páginas 8..N−1; restaurar; intercalar páginas repetidamente; testar troca rápida de páginas mas não durante VBlank/DMA. Acesso por byte e word alinhado onde suportado; não extrapolar arquivo nem o limite máximo de registrador.
- Para detectar se o emulador ignora o mapeador, comparar assinaturas que mudam necessariamente quando a página troca; em caso de mirror/fallback, falhar claramente. Medir tempo de alternância com contador conhecido e evitar interpretar o tempo de render como custo isolado do mapper.
- Testes de estresse: 1000+ alternâncias/releituras; alternância 8↔última página; padrões contra aliasing de endereços de banco e contra troca errada de bytes. Verificar vetores/ISR fixos.
- SRAM é teste independente: criar variante **com** SRAM declarada corretamente no header, checar leitura/gravação e persistência após desligar/reiniciar, preservando mapa SRAM real usado pelo DOOM. **Não supor** coexistência do endereço `$200000` com ROM mapeada: se houver overlay, testar com segurança, evitando acesso à SRAM durante DMA/Z80 e registrando colisões. Não usar gravação destrutiva em dados de save existentes.
- Áudio é outra variante independente: tocar tom/música original sintética e PCM sintético, com dados em janela fixa abaixo de 2 MiB, enquanto alterna bancos altos. Evitar distribuir samples/WAD protegidos.
- Build tem de garantir ROM cabeçalho e checksum, log `sha256sum`, convenções de banco e ausência de binários no git público até política ser aprovada. Como ROM diagnóstica gerada **não incorpora recursos terceiros**, pedir ao usuário/Cláudio decisão sobre publicar binários deste laboratório; por padrão seguir R129: ROM privada, fonte/relatório público.

## Entrega B: workflow e relatório
- Novo workflow manual/trigger `r131-ssf-mapper-diag.yml`, sem modificar R128/R129. Gerar ROMs com SGDK/Marsdev, basic smoke com BlastEm (5/8/12/15 MiB), validação hashes/per-page em Python; MAME como segundo árbitro quando seu suporte homebrew SSF estiver confirmado. Se o emulador não implementar a identificação homebrew, reportar **inconclusivo**, não reprovação da ROM.
- Relatório público sanitizado por tamanho, emulator+versão, deteção mapper, páginas lidas, stress, SRAM, Z80, CRC/hash e advertência de hardware desconhecido; não afirmar testes que não aconteceram.
- Saídas privadas em `/home/dan/Projetos/Personal/r131-ssf-mapper-diag`, conforme política R129; não alterar SRAM de saves existentes e não escrever em `/home/dan/Projetos/doom-md` (checkout local tem mudanças e WAD staged!).
- Não disparar builds longos durante benchmark R128 All no console/runner sem necessidade; ROM diagnóstico deve ser leve.

## Entrega C: plano posterior para DOOM E1–E3
Somente após os testes, planejar manter código crítico e áudio em bancos fixos, colocar mapas/texturas de episódio em bancos externos acessados apenas no carregamento, sem bank switch no loop do render. Verificar limite ROM, SRAM e interação com Z80 no clone real. Alternativa de fallback: um episódio por ROM, se o clone não suportar mapper estável.

## Critérios
1. ROM de 5 MiB faz leitura do payload acima de 4 MiB com PASS em pelo menos um emulador que suporte SSF2.
2. Testes 8/12/15 MiB mostram resultados e limites, inclusive falhas (sem mascará-las).
3. SRAM e áudio são testados separadamente e depois juntos, com power-cycle/persistência.
4. Nenhum WAD/ROM de jogo/ELF com recursos protegidos é enviado ao repositório público.
5. Entregar ao usuário ROMs e instruções exatas de teste em BlastEm; no cartucho físico repetir tudo quando chegar.

**Prioridade de implementação:** primeiro um único binário 5 MiB com leitura/assinatura visível; validar no BlastEm. Só depois escalar para 15 MiB e agregar SRAM/áudio.
