# R70-A — diagnóstico da falha do teste diferencial (run 40356754608)

## Conclusão verificada
A divergência "A2 / A1+A2 ≠ controle" vista no runner era **instabilidade do harness**, não diferença funcional do renderizador.

## Evidência (reproduzida localmente, gcc 13.3)
1. `test_r70a_segloop.py --legacy` (harness do primeiro run: hasheia também os campos de `dcvars` que a rotina NÃO lê, sem zero-init) reproduz o erro em todos os -O0/1/2/3/s e -std=gnu99/default: a primeira diferença concreta é sempre
   `FIRST DIFFERENT EVENT #8: control 'flat.UNREAD.colormap 94206181552504' vs a1 'flat.UNREAD.colormap 94448156746104'`
   (valores = ponteiros de pilha/ASLR; `R_DrawColumnFlat` só lê x, yl, yh).
2. Prova decisiva: em modo legado o **mesmo binário de controle, executado duas vezes, diverge de si mesmo**; em modo estrito é idêntico.
3. Modo estrito (hasheia só o que a rotina lê/escreve + `-ftrivial-auto-var-init=zero`): controle = A1 = A2 = A1+A2 em 20.000 cenários (8.955.451 eventos cada), todos os eventos: chamadas de desenho (rotina e argumentos), clip arrays por índice, solidcol, maskedtexturecol, didsolidcol, globais finais.
4. Sensibilidade preservada (nada relaxado): 5 mutantes do texto real de `R_RenderSegLoop` (yl+1, floorclip errado, passos de scale/top/bottom omitidos) são todos detectados.

## Diagnóstico agora impresso em qualquer divergência
Primeiro cenário divergente, entradas do cenário, nº do primeiro evento diferente, nome (`draw/flat/sky/wall/segtex/end.<campo>[índice]`), valores de ambos, 6 eventos anteriores; campos `UNREAD` são classificados como lixo de harness.

## Limite da conclusão
Verificado no gcc local; no runner (gcc mais novo, gnu23) só será confirmado numa nova execução, que NÃO foi disparada. O workflow ativo teve o gatilho `push` removido (apenas `workflow_dispatch`).

## Correções de workflow
- Disassembly: só roda se os 4 ELF existirem; senão "SKIPPED - build/capture unavailable". `objdump` falhando mantém stderr completo (rc, comando, stderr) em `dist/r70/disasm/stderr.log` e na anotação.
- Capturas: pulam com "SKIPPED" se ROM/ELF ausente; comparação de pixels idem, sem erros em cascata.
- Nenhuma alteração na R66.
