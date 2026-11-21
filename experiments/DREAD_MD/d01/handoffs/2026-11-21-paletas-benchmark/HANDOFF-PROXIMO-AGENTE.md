# Dread MD D01 — handoff para o próximo agente

Data: 21/11/2026. Autor: Werk/Codex. Estado: investigação de paletas e auditoria de benchmark; multipaleta é experimento, não versão aprovada.

## Objetivo do usuário

Melhorar a imagem e o desempenho da engine baseada em Dread, tendo a Alpha 2 do Happy Ferret como referência real. O usuário aceita arma, rosto e HUD compartilhando uma ou duas paletas. Preservar a imagem correta, menus, fases e possibilidade de testes no console. Não voltar às experiências Nexus/NeoDoom/Manifold como base do renderer. Trabalhar com histórico no GitHub; preferir links diretos para ZIP. Não publicar WAD nem ELF. Não mexer na branch de Cláudio sem necessidade.

## Base publicada e como retomar

Repositório: https://github.com/bollux78/MD-DOOM64KB

Base corrigida publicada: commit `42f17f26b1e3187ad7995799891cb50bd090e66c`, branch `exp-werk-dread-exato-input-vblank`. A cópia local equivalente é `61c6e8f192e1fd46365e5f6b59203061bad470b2` (mesma árvore).

Este handoff está numa branch própria, derivada dessa base. O código padrão da base foi preservado. O arquivo `multipal-WIP.patch` ao lado contém TODAS as mudanças do experimento local de paletas, incluindo os dois arquivos novos. Aplicar em checkout limpo com `git apply --check caminho/multipal-WIP.patch` e depois `git apply caminho/multipal-WIP.patch`. Não precisa do ambiente local anterior para recuperar essas alterações.

Diretório do motor: `experiments/DREAD_MD/d01/`. Leia também os handoffs já existentes nessa pasta. Handoff de Cláudio: branch `exp-dread-md-d01-claudio`, commit de documentação `2e11bb8`; renderer posterior dele incluiu `0681cb0`/laço de colunas.

## Descoberta principal: uso REAL das paletas do Ferret

ROM examinada: `E1M1-alpha2.bin`, executada em Genesis Plus GX instrumentado, sem Sega CD e com SRAM bloqueada. Foram lidos atributos dos planos, sprites e CRAM, não apenas a imagem do debugger.

- Dez amostras durante giro: os 720 tiles do viewport (40×18) apontam para PAL0. Os dois planos consultados apontam à mesma tabela, 0xE000; não somar como duas camadas independentes.
- Pistola: 14 peças de sprite, todas PAL2.
- HUD: principalmente PAL1, alguns tiles PAL3.
- PAL1 e PAL3: primeiras 15 entradas idênticas; última 000 versus C00.
- Snapshot de CRAM: 29 cores distintas nos 64 slots.
- Rastreamento de 600 quadros de vídeo: 120 atualizações de cor, somente PAL0 e na linha 243, durante VBlank. H-int desabilitada nas dez amostras.
- Portanto, não há evidência de quatro paletas simultâneas no mundo 3D nessas cenas. Quatro bancos carregados NÃO significam cenário de 64 cores. Não generalizar para todos os efeitos e estados ainda não examinados.

PAL0, palavras CRAM: `000 222 222 444 444 466 688 8AA 244 224 222 00A 48C AEE EC4 C42`.

Dados brutos ao lado: `Ferret-paletas.json`, `Ferret-uso-detalhado.json`, `Ferret-cram-trace.json`; paleta para o conversor: `ferret-palette0.json` (triplas RGB 0..7).

Hipótese a investigar: aparência melhor pode vir da seleção de pares, quantização, iluminação e padrões de mistura. Usar exatamente a paleta dele não reproduz automaticamente sua conversão de texturas.

## Experimentos de paletas — estado exato

Quatro variantes E1M1 apenas, sem SRAM/mapper, mantendo elementos do jogo e quatro modos de vídeo:

| Variante | Mundo | Interface | Bench 312 imagens | Giro 1500 quadros de vídeo |
|---|---|---|---:|---:|
| control | PAL0 atual | 3 bancos | 3,5848 FPS | 6,0040 FPS |
| pal1 | PAL0 exata Ferret | 3 bancos | 3,5848 FPS | 6,0040 FPS |
| pal2 | 2 paletas | arma em uma; rosto/HUD em outra | 2,3438 FPS | 3,8186 FPS |
| pal3 | 3 paletas | arma/rosto/HUD em uma | 2,2299 FPS | 3,4647 FPS |

Valores dos dois últimos: implementação ASM MAIS RECENTE com máscaras de propriedade de tiles por coluna. Não usar `dread-multipal-builds/results.json` do ambiente anterior: esse agregado ficou desatualizado, com números da versão ASM anterior. `resultados-latest.json` deste handoff usa os resultados mais recentes e hashes das ROMs locais.

Isso não demonstra que multipaleta seja intrinsecamente inviável: demonstra que NOSSO gerenciamento/remapeamento atual é caro. Não foi aprovado pelo usuário como solução final. ROMs multipaleta ainda não foram publicadas/entregues como pacote final.

### O que o patch faz

- `palette_span.s`: pós-processamento ASM dos spans; máscara de tiles já atribuídos por coluna e máscara por paleta evitam varrer pixels quando não existe conflito. Se outro material tem paleta diferente dentro do mesmo tile, remapeia os pixels para a paleta proprietária.
- `colasm.s`: hooks depois dos scalers nativos, somente NPAL>1; sky usa PAL0.
- `render.c/h`: estado de propriedade, tabela de paleta dos tiles, metadados de sprites, construtor de name table com stride físico 64. Wrapper compacto preserva API do host.
- `main.c`: duas name tables em RAM; upload adicional junto ao framebuffer, com orçamento de VBlank compartilhado; só apresentar depois de ambos prontos. Aproximadamente 1152 bytes extras de atributos por frame em H40 linhas.
- `conv.py`: PAL0 fixa e famílias adicionais ajustadas offline; escolhe paleta por material e por bucket de sprite.
- `merge_ui_palette.py`, `gen_hud.py`, `game_hud.c`: compartilhamento offline das paletas da interface, preservação de branco e transparência dos sprites.
- `pack_episode.py`: parser de sprites aceita metadados novos; deduplicação não inclui os índices de paleta.
- `build_map.sh`: parâmetros DREAD_NPAL=1/2/3, DREAD_EP_MAPS=1, DREAD_PALETTE_TEST=1 e cache preparado. Default continua NPAL1.

Validação feita: nove amostras de framebuffer do benchmark das versões pal2/pal3 finais têm hashes idênticos às referências C do mesmo algoritmo. Isso valida equivalência com a referência, não fidelidade ao Ferret. Os quatro modos foram testados na versão ASM anterior; REPETIR na versão final com máscaras e examinar HUD, clipping e atributos. Ainda sem teste em console das variantes de paletas. Paletas compartilhadas de episódio inteiro NPAL>1 não estão concluídas; limitar esses testes a E1M1 até corrigir isso.

## Auditoria do alegado declínio de 4,55 FPS

Run fornecido pelo usuário: https://github.com/bollux78/MD-DOOM64KB/actions/runs/44763244095

Commit: `64d62829eca4fad4ebe3624e6165ff5338d2a9e3`. Artefato `14642875942`, nome dread-md-d01. Job `136381006456`. Log e JSON CONFIRMAM 4,55 FPS: 161 imagens / 2123 VBlanks ×60. BlastEm no runner x360-linux. Perfil desse run: render_total 207,5 ms, frame 219,8 ms, média 24,5 segs e 46,3 nodes.

NÃO é comparação direta com o controle recente:

- Antigo: H32, 128×112 lógico, 256×112 na tela; DMA 2048 bytes por VBlank; sem HUD/arma/sprites do mundo/céu texturizado.
- Atual H40 linhas: 160×72 lógico, 320×144 na tela; duplicação vertical com H-int, sprites/interface/céu e regras de DMA diferentes.
- Os botões/durações do script são iguais, mas antes dt dependia do tempo de quadro, limitado a 8. Agora dt=4 por imagem no bench. A mudança foi introduzida no commit `ccfa0b06f93014450423e1b9f8da91db5c8792fc`.
- Por isso o antigo terminou em 161 imagens; atual, 312. Não usar índices de imagem antigos e novos como se fossem a mesma vista. Não tratar a diferença como regressão quantificada de 21%.
- Benchmark comum atual NÃO executa IA ativa: `Actors_Tick` somente em jogo normal ou bench_req=2. Não atribuir a queda à IA sem medir. Bench comum ainda desenha objetos e roda outras tarefas de apresentação.
- Recentes comparáveis: pre-loop 312/5110 =3,6634; laço novo antes da correção de amostragem 312/5015 =3,7328; textura exata rápida 312/5171 =3,6202; exata com input VBlank episódio 312/5244 =3,5698. O controle E1M1 isolado mais recente é 312/5222 =3,5848.

Atenção: a última resposta ao usuário explicou as diferenças mas NÃO houve bisect/ablação completa para atribuir milissegundos a cada recurso. O run antigo foi confirmado pelo log e artefato; não reexecutado por nós nesta auditoria. O próximo agente deve padronizar câmera, viewport, emulador e conteúdo antes de alegar regressões.

Arquivo `bench-antigo-4.55.json` contém o resultado original do artefato. Sem WAD/ELF neste handoff.

## Próximos passos sugeridos

1. Recuperar a base e, se desejar continuar multipaleta, aplicar o patch numa branch experimental.
2. Priorizar amostragem de cores/padrões com UMA paleta, pois é o que a medição mostrou no viewport do Ferret; comparar mesmas vistas com capturas reais.
3. Manter controle NPAL1. Para multipaleta, medir custos separados: propriedade, conflitos/remap, name table e DMA. Procurar decisões offline que retirem trabalho do frame.
4. Para auditoria histórica, portar o passo fixo para o teste antigo e comparar vistas equivalentes; depois testar recursos isoladamente no motor atual. Não prometer recuperação de 4,55 antes de medir.
5. Conferir todos os modos, transparência, HUD, arma, céu e ângulos fechados; preservar clipping de sprites pela janela das paredes. A correção de amostragem exata resolveu distorções visíveis: não removê-la silenciosamente por FPS.
6. Entregar ZIP com controle e variante, SHA256, resultado e commit. Sem WAD/ELF; pedir teste em console para aprovação visual.

## Ambiente anterior (opcional; pode desaparecer)

Raiz `/workspace/scratch/908cd7aa2f56`. Worktrees `dread-reference` (base corrigida) e `dread-multipal` (patch WIP). SGDK local `r128-local-sgdk`; WAD local `pixel4-control/scripts/doom1.wad` (não publicar). Core instrumentado `dread-sram-emu/genesis_plus_gx_libretro.so`.

Resultados/capturas em `dread-multipal-builds`, caches `dread-multipal-cache/{1,2,3}/E1M1`. Harness `validate.py` está copiado neste handoff por auditabilidade; depende de wrapper libretro do repositório, core instrumentado e símbolos locais ELF. Não é executável isoladamente em qualquer máquina sem preparar essas dependências.

Comando usado para recompilar os NPAL2/3 de cache já preparado (não substitui a conversão inicial):

```bash
export GDK="$PWD/r128-local-sgdk" DREAD_COPY_SEGA_S=1 DREAD_EP_MAPS=1 DREAD_COMBAT=1
export DREAD_EXTRA_FLAGS='-DDREAD_VALIDATION_TEST -DDREAD_JOY_VBLANK'
DREAD_NPAL=2 DREAD_PREPARED_MAPS="$PWD/dread-multipal-cache/2" \
 bash dread-multipal/experiments/DREAD_MD/d01/tools/build_map.sh \
 pixel4-control/scripts/doom1.wad EPISODE dread-multipal-builds/pal2 'DREAD 2 PAL CENARIO'
```

O workspace local ainda tem capturas, ROMs e vídeos das experiências; o essencial para recuperar as alterações está publicado neste diretório. Não afirmar que os binários WIP foram publicados: somente o código em patch, evidências e handoff.
