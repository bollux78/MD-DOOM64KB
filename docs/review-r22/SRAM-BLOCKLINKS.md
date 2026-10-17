# R22e — blocklinks na SRAM

Objetivo: remover da zona RAM o array de cabeças da tabela de colisão, que consome11648bytes em E1M8. A R22d falhou mesmo entrando direto em E1M8, na etapa GROUP: pedido2028/necessário2048, livre1696/maior bloco1120. A mesma falha existe em8×8 desde as versões antigas.

## ROMs no ZIP

Todas têm prefixo `doom-md-r22e-` e extensão `.bin`.

| Sufixo | Tipo |
|---|---|
| control | Controle8×8 timedemo3, RAM |
| play-control | Controle8×8 jogável/música, RAM |
| sram-perf | Timedemo3 8×8, blocklinks SRAM |
| sram-play | Jogável8×8, blocklinks SRAM |
| sram-direct8 | Diagnóstico8×8: entrada direta em E1M8, blocklinks SRAM |
| sram-transition | Diagnóstico8×8: E1M1→E1M8, blocklinks SRAM |
| sram-p4 | Timedemo3 4×4, solid/LUT, blocklinks SRAM |
| sram-play-p4 | Jogável4×4, solid/LUT, blocklinks SRAM |

Música E1M1 nos mesmos termos da base. Zona RAM/cache de texturas mantidos; o antigo cache de texturas em SRAM continua desativado. As duas diag usam a tela de memória R22d e param intencionalmente com `E1M8 LOADED OK - DIAG STOP` se o mapa inteiro carregar. Não são ROMs para continuar jogando após essa tela.

## Testar

1. `sram-direct8`: fotografar a tela completa, seja sucesso ou falha. É a verificação mais rápida de capacidade e carregamento de E1M8.
2. `sram-play`: abrir menu, jogar, sair de E1M1 e continuar efetivamente andando/jogando em E1M8. Verificar colisões, inimigos, coleta de objetos, disparos e áudio.
3. Se houver problema, repetir na `sram-transition`, dificuldade média, e guardar a tela. Ela registra as últimas16etapas com FREE/MAX.
4. Testar `sram-play-p4` na mesma transição.
5. Comparar `sram-perf` com `control` (~12,37FPS/172,5s de referência); comparar `sram-p4` com o solid-lut anterior (~2,90FPS/735,8s). Diagnósticos não servem para medir ganho puro de FPS.

## Implementação

Reserva até16KiB lógicos de SRAM, em bytes ímpares de0x200001 até0x207FFF. E1M8 usa11648bytes lógicos (2912cabeças de4bytes); E1M1 usa3312 (828cabeças). Não aumenta a zona nem usa os11648bytes correspondentes nela.

Cada valor32bits é lido/escrito explicitamente em quatro bytes ímpares. Os campos `bprev` dos objetos podem indicar uma cabeça em SRAM ou o `bnext` de outro objeto em RAM. Tokens alinhados representam as cabeças; eles nunca são dereferenciados diretamente como ponteiros de32bits. Inserção, remoção e iterador de colisão foram adaptados juntos. O caminho RAM original fica nas ROMs de controle.

Antes de zerar as cabeças de cada mapa, habilita SRAM pelo registrador A130F1, verifica limites (máximo4096células) e testa escrita/leitura em posições que exercitam os bits de endereço e a extremidade da área necessária, em duas fases. Isso detecta ausência e SRAM espelhada pequena demais. Em falha, para com `SRAM ABSENT OR TOO SMALL` ou `SRAM BLOCKMAP TOO LARGE`. Usa SRAM como área temporária; não implementa savegame. Os bytes de teste são restaurados antes da inicialização, depois toda a área das cabeças utilizadas é zerada intencionalmente.

O cabeçalho Genesis da base anuncia SRAM RA em200000..20FFFF; a implementação usa somente a primeira metade desse intervalo físico e a pista ímpar. A ROM deve caber abaixo de2MiB, auditado para evitar sobreposição ROM/SRAM. A quantidade de SRAM realmente disponível/gravação precisa passar no teste do cartucho/emulador.

## Validação

Host: código real de acesso SRAM e funções completas P_SetThingPosition/P_UnsetThingPosition/P_BlockThingsIterator extraídas da produção. Testa leitura/escrita32bits, todas as células nos mapas828/2912/4096, preservação dos bytes pares e da região além do necessário, reinicialização, SRAM8KiB/ausente rejeitada para o mapa que excede a capacidade, remoção de cabeça/meio/último e10000operações de movimento com invariantes dos ponteiros e iterador; UBSan. O teste é um modelo de memória, não emulação elétrica do cartucho.

CI: oito compilações MC68000/GCC15, flags, identidades, ELF/orçamento de boot/font/heap, hashes e cabeçalho SRAM. Isso não prova que E1M8 carrega no hardware: os resultados do usuário completam a validação.
