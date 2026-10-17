# Perguntas para a próxima revisão

Queremos uma análise nova, ancorada no código e no assembly GCC15.2, que evite repetir literalmente a revisão anterior.

1. Onde estão agora os maiores custos de68k? Rever cálculo/iterações por segmento, clipping, preparação de colunas, composição de textura/cache e escrita de células apósR5/R6. Solicitar contadores novos ou perfil de ciclos quando faltarem dados.
2. Há trabalho invariável ainda dentro de loops, conversões/sinais/larguras redundantes, spill de registradores ou chamadas caras nas opções vencedoras? Mostrar trechos reais e como validar equivalência para inputs limites.
3. É possível fundir caminhos/reestruturar dados sem mudar rasterização, cache/tag/replacement ou comportamento de fullbright? Não prometer ganho sem incluir custo do wrapper/setup e frequência real de uso.
4. Há melhorias de cache por tag, máscara, layout e colisões que não reproduzam oR4b perdedor? Medir com colunas reais e colisões, não apenas cachehit ideal.
5. Que economia segura de RAM permitiria melhorar cache ou folga de stack? Modelar heap SGDK, zona Doom, estáticos, stack e picos de init separadamente. Reduções de drawsegs/openings precisam instrumentar máximos em vários mapas, não inferir segurança deDEMO3.
6. V3 pode melhorar com menor trabalho porframe/linha sem perder preservação de SR/Z80 e workaround DMA? Considerar o custo68k e timing do VDP real; separar ganho esperado de risco de áudio.
7. Vale retomar V2 isoladamente e S5 com diagnóstico na transição? Apresente causa plausível e experimento que a discrimine, sem tratar tentativa anterior como falha comprovada deVBlank em si.
8. Quais flags/LTO/inlining/alinhamento geram assembly melhor nesta versão do compilador? Comparar assembly total e tempo real; não extrapolar resultados deGCC13 para15.2.

## Escopo

Prioridade:mesma viewport,mesma imagem,música,clock e demo;performance e estabilidade. 36colunas/viewport menor, pixels2x2/4x4 ou renderpixel a pixel podem ser discutidos em seção separada como mudança de produto/arquitetura, não como ganho equivalente. Sem32X. SRAM pode ser estudo separado, mas não é a base atual.

## Entrega solicitada

- README e resumo com5–10propostas realmente novas ou revisões justificadas de tentativas anteriores.
- Para cada proposta:ID,arquivo/função,problema concreto,patch/pseudocódigo,ganho estimado e fundamento,custoRAM/ROM,risco,pré-condições,testes,prioridade.
- Separar otimização exata de aproximação matemática/alteração visual;estas últimas exigem flag e comparação visual própria.
- Trazer tabelas de ciclos ou microbench com setup,caso curto/longo e preservação ABI;deixar explícito o que é medido em CPU,emulador ou hardware.
- Matriz sugerida com controle e opções isoladas antes de combinações, nomes≤30caracteres, pares diag/perf, sem alterar dezenas de fatores ao mesmo tempo.
- Identificar comportamentos indefinidos ou bugs com evidência,sem misturá-los com ganho comprovado.
- Se a melhor próxima ação for medir, especificar instrumentação de baixo overhead e como retirar seu custo da comparação.
