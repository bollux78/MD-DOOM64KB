# R84 — auditoria de gargalos sobre R83 sprites

Esta rodada é análise, não uma nova ROM nem um benchmark. Base escolhida pelo resultado do usuário: **R83 sprites P1/F1**, 7,48 FPS / 285,13 s / 2.134 frames. O candidato de clipping de paredes fica fora. Checkout inspecionado: `81d1268`; os fontes efetivos foram preparados numa worktree separada com `apply_r81.py`, `R80_EXPERIMENTS=P1+F1 apply_r80_performance.py` e `R83_CANDIDATE=sprites apply_r83.py`.

## Conclusão

Priorizar **eliminar resolução/composição/transporte de colunas**, e não outra simplificação pequena do clipping. A alternativa de menor esforço é combinar o MOVEP já aprovado com a reutilização da última coluna. A alternativa estrutural é preparar dados de textura em ROM. A medição que falta é um perfil atual da R83, com frequência de hits, misses e repetições; os percentuais da R71 não podem ser apresentados como atuais.

| Prioridade | Experimento independente | Evidência no código atual | Limite/risco |
|---|---|---|---|
| 1, pequeno | MOVEP + reutilização da última coluna | `mall` ativa MOVEP em mapa/cache, mas **não** `DOOM_R39C_REUSE_CACHE`; hits ainda copiam a coluna da SRAM para `tmpCache` | Frequência de repetição ainda não medida; estado adicional de 3 bytes antes de alinhamento |
| 2, estrutural | Colunas compostas preparadas em ROM | 1.574 das 1.682 colunas amostradas têm todos os 128 bytes definidos; dados deduplicados = 139.008 B | Preservar histórico do cache e bytes não escritos das outras colunas; ver abaixo |
| 3 | Diretório ROM de origens das paredes não compostas | `R_DrawSegTextureColumn` resolve patch, diretório WAD e `columnofs` a cada chamada | Não repetir simplesmente WALL_HOIST, que já perdeu; usar diretório gerado e fallback exato |
| 4 | Evitar leituras SRAM desnecessárias na classificação de linhas | `R_RecalcLineFlags` lê o sidedef antes de saber se a linha é unilateral; `R_AddLine` relê flags após recalcular | LTO, pressão de registradores e chamadas podem anular a economia |
| 5 | Kernel de pixels e geometria, guiados por perfil novo | O kernel serve agora a paredes **e sprites**; o perfil anterior não representa essa distribuição | Mudanças isoladas e equivalência de overflow/rounding; sem estimativa de FPS confiável |

Não há porcentagem de ganho demonstrada para esses candidatos. Uma rotina ocupar 6% do perfil antigo não significa que removê-la dará 6% na R83.

## 1. Cache: uma oportunidade concreta e pequena

`build_r71a12mul_hud.py` seleciona `DOOM_R39C_VARIANT=mall`. Em `build_r35_linear.fish`, `mall` habilita `MOVEP_CACHE` e `MOVEP_MAP`; `reuse` é outro caso mutuamente exclusivo. Portanto selecionar simplesmente `reuse` **desliga as otimizações MOVEP aprovadas**, produzindo uma comparação inadequada.

O candidato deve manter `mall` e acrescentar apenas `DOOM_R39C_REUSE_CACHE`. O código existente de `R_ComposeColumn` já registra qual coluna está em `tmpCache` e evita `SramCacheCopyFrom` quando ela é a desejada. Inicialização invalida esse estado. Conferir também load, mudança de mapa e todos os escritores de `tmpCache` antes de publicar uma ROM.

O primeiro experimento deve usar essa versão existente, sem mudar hash, substituição ou composição. Uma variante posterior pode testar retorno antecipado antes da busca no cache, mas precisa validar separadamente os efeitos na ordem de substituição. Não aumentar o cache RAM: a margem de BSS da PLAY é apenas 68 B em relação ao gate 57.920.

## 2. Auditoria de pré-composição: tamanho e uma armadilha real

Ferramenta: [`r84_texture_audit.py`](../../scripts/lab/r84_texture_audit.py). Resultado: [`texture-audit.json`](texture-audit.json).

Foi reconstruído o WAD do episódio com o conversor do workflow. A auditoria do WAD original e do convertido deu as mesmas colunas. O resultado registrado usa o convertido, SHA-256 `249c2f185f0d53c65b1efc0fed017defa729fed8bfa62a627d23eded7cab226f`.

O caminho atual de `R_ComposeColumn` usa `(texcolumn & 0xfffc) & widthmask`: a biblioteca de colunas precisa respeitar esse arredondamento, não introduzir mais detalhe horizontal.

| Quantidade estática | Resultado |
|---|---:|
| Texturas totais | 125 |
| Marcadas `overlapped` | 79 |
| Colunas distintas selecionáveis nesse caminho | 1.682 |
| Colunas com janela completa de 128 bytes definida | 1.574 |
| Colunas com bytes não atribuídos | 108 |
| Payload das janelas completas, deduplicado globalmente | 139.008 B = 135,75 KiB |
| Tabela compacta de ponteiros para as 1.682 posições | 6.728 B, além do diretório por textura |
| Folga nominal até 4 MiB da ROM R83 registrada no handoff | 1.310.720 B |

O payload cabe folgadamente no limite nominal, mas **o linker e o mapeamento SRAM/ROM ainda precisam ser auditados**. Não colocar tabelas numa janela ocultada pelo SRAM quando forem lidas. Os índices fonte continuam sendo os originais: luz, dano e quatro perfis de cores permanecem nas LUTs atuais. Não gerar uma cópia por paleta.

### Por que não basta apontar todas as paredes para ROM

`R_DrawColumnInCache` não limpa `tmpCache`. As texturas AASTINKY, BIGDOOR1, STEP4/5/6, SW1COMM/EXIT e SW2COMM/EXIT não atribuem toda a janela de 128 bytes. Isso não prova defeito visual: falta verificar se esses bytes são amostrados em alguma cena. Porém, impede assumir que uma coluna é sempre função só da textura e de x.

Mesmo desviando apenas colunas completamente definidas para ROM, o conteúdo anterior de `tmpCache` e o histórico de slots mudam. Uma composição parcial posterior pode herdar bytes diferentes. Portanto o campo `safe_columns` do JSON significa **independência do buffer de entrada naquela composição**, não prova de segurança de um bypass global do cache.

Primeiro candidato estritamente conservador: em um **miss**, substituir a composição de uma coluna completa por cópia de seus 128 bytes pré-calculados para `tmpCache`; manter o hash, a cópia para SRAM, as tags, a substituição e os hits exatamente como antes. Isso elimina a busca de patches e a composição, mas não elimina o transporte. Medir para saber se a cópia única compensa.

O candidato mais ambicioso, com fonte direta em ROM e sem cópias, exige prova adicional sobre as janelas efetivamente lidas das texturas parciais ou um modelo que preserve o histórico observável. Deixar um fallback sem tratar isso não é suficiente. Não remover cache/save nem prometer liberação de RAM nesta etapa.

### Verificação realizada

O auditor extraiu e compilou a função C **real** `R_DrawColumnInCache`, sem reescrevê-la. Comparou o resultado C com o modelo Python para todas as 1.682 colunas, com dois conteúdos iniciais diferentes (0x55 e 0xAA): **3.364 composições de 128 bytes concordaram**. O teste preserva inclusive o comportamento do fonte ao recortar `originy` negativo. Isso valida composição/cobertura no host; não valida desempenho 68000 ou renderização da ROM.

## 3. Diretório ROM para paredes não compostas

Hoje o caminho resolve `R_GetColumn` → `W_GetLumpByNum` → `patch->columnofs[x]` → `column+3`. Esses dados são imutáveis. Gerar um diretório por textura/coluna, mantendo a ordem exata dos patches e o tratamento atual de texturas simples, pode substituir a cadeia por uma consulta.

É diferente de reativar `DOOM_R20_WALL_HOIST`: o antigo experimento guardava preparação por segmento e mudou chamadas/registradores, com regressão medida. O diretório deve usar o índice da textura **depois** da tradução de animação/switch, preservar `widthmask`, e não aplicar a lógica de parede opaca aos posts transparentes de sprites ou paredes mascaradas. Ainda não foi calculado o tamanho desse diretório nem demonstrado ganho.

## 4. SRAM: atacar acessos específicos, não culpar toda a R81

O snapshot normal do sidedef no renderer lê offsets 4..8, exatamente a faixa contígua que a R81 mantém no caminho rápido de `R27_ReadBlock`. O fallback byte a byte para reconstruir ponteiro/padding existe, mas **não é o caminho desses dois snapshots**. Não atribuir a ele um gargalo geral sem perfil.

Há, contudo, trabalho evitável: `R_RecalcLineFlags` faz esse snapshot antes do teste de `ML_TWOSIDED`. Para linhas unilaterais, a decisão de fechamento não depende do sidedef. Pode-se testar um caminho que faça a leitura somente quando necessária. Outro candidato é devolver as flags calculadas ao chamador, evitando o `R23_GET` logo após o write. Cada um precisa manter `ML_MAPPED`, validcount, portas, switches e automap.

Não simplesmente manter SRAM habilitada: o builder normal não usa `DOOM_R27_SRAM_FIXED`, e há assets na região de ROM compartilhada. MOVEP reduz cópias, mas não elimina as obrigações do mapper e do áudio.

## 5. Hipóteses rebaixadas por esta revisão

- **Sobrepor lógica à espera do vídeo:** `D_DoomLoop` já executa ticker e áudio antes de `D_Display`; o `R20_StopVideo` que protege o framebuffer ocorre em `R22_BeginFrame`. A sugestão antiga de adiantar a lógica já está essencialmente atendida. Remover a espera criaria concorrência entre renderização e DMA sobre o mesmo buffer.
- **Cache minúsculo de ângulos de vértices:** uma simulação estática de duas entradas LRU, reiniciadas por subsetor, acerta somente 9,6–11,7% dos endpoints ao percorrer integralmente os mapas E1M1–M9 na ordem dos segs. Não é frequência em execução, mas enfraquece a expectativa de aproveitar quase metade das chamadas. Os testes de chave e spills podem consumir a economia.
- **Simplificar novamente clipping como alvo principal:** R83 wallclip já teve resultado negativo no DEMO3 completo. Não extrapolar redução de código para redução de tempo.
- **Novas flags globais do compilador:** os experimentos R82 não demonstraram ganho útil. Priorizar remoção de trabalho e olhar o assembly do caminho realmente executado.
- **Tratar o kernel R60 como intocável:** não há prova de ótimo. Mas desenrolar laços ou acrescentar LUTs grandes sem contabilizar acessos, prólogos e chamadas tende a produzir mais mudanças marginais. Reavaliar após perfil atual, incluindo sprites.

## Próxima rodada recomendada

1. Perfil da R83 sprites separando tempo de composição, transporte, resolução de origem, desenho, lógica e espera. Contar misses, hits e repetição imediata sem usar FPS instrumentado como benchmark. O sampler antigo injeta código abaixo da pilha: não executá-lo cegamente com a ocupação de RAM da R83.
2. A/B independente: controle R83 versus **mall + reuse**; outro candidato com **pré-composição conservadora em misses**. Só montar fonte direta em ROM após resolver a dependência dos bytes residuais.
3. Mesmo job e faixa de tics para a comparação parcial; framebuffer idêntico, BSS/ROM/pilha dentro dos limites; testar portas, switches, save/load e perfis. O usuário continua fazendo o DEMO3 completo.

Nenhum workflow, benchmark ou build de ROM foi disparado nesta auditoria. Foram feitos preparação dos fontes, leitura do caminho ativo, reconstrução de assets e comparação host da composição. O branch mantém o código de jogo sem alteração.
