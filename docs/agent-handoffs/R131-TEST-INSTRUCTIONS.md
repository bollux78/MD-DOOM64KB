# R131 — Diagnóstico de mapper SSF2

Teste independente para o cartucho atual e para o futuro X7 Ultra clone. **Sem WAD, recursos do DOOM, segredos ou alterações na R128.**

## Arquivos de saída
- `r131-standard-4m.bin` — **cartucho atual**: ROM convencional de exatamente 4 MiB, valida assinaturas diferentes nas páginas 1–7 de 512 KiB; **não escreve nos registradores de mapper**. O PASS não prova compatibilidade com ROMs acima de 4 MiB.
- `r131-ssf-5m.bin` — **BlastEm**: SSF2 de 5 MiB, páginas 8–9 na janela 7.
- `r131-ssf-8m.bin`, `r131-ssf-12m.bin`, `r131-ssf-15m.bin` — 16, 24 e 30 páginas, respectivamente, com 1.024 alternâncias de bancos.

Por segurança, **não carregue as ROMs SSF2 acima de 4 MiB no cartucho antigo** antes de confirmar sua compatibilidade. Elas são para o BlastEm e, posteriormente, para testar o X7 Ultra real.

## Build automático no runner
Workflow: `.github/workflows/r131-ssf-mapper-diag.yml`. Executa build SGDK isolado com Marsdev e preserva ROMs em:

```text
/home/dan/Projetos/Personal/r131-ssf-mapper-diag/run-<run-id>-1/
```

No GitHub público fica somente o artefato `r131-mapper-catalog` (nomes, hashes e tamanhos), **sem ROMs**. O teste no console ainda precisa ser feito pelo usuário.

## Build manual (fish)

```fish
cd /home/dan/Projetos/doom-md-r129
git fetch origin refs/heads/exp-claudio-r121-e1m7-20261103
git pull --ff-only origin exp-claudio-r121-e1m7-20261103
set -lx GDK /home/dan/mars/m68k-elf
python3 scripts/lab/r131_build.py --output /home/dan/Projetos/Personal/r131-mapper
```

Não mexer no checkout original `/home/dan/Projetos/doom-md`, que contém alterações e WAD.

## Tela e interpretação
Cada página verificada exibe PASS/FAIL. O fundo fica verde-escuro quando o total passa e vermelho-escuro em falha. Variantes SSF2 exibem também `STRESS 1024`. Se aparecer `FAIL`, não significa necessariamente defeito de hardware: pode faltar suporte ao mapper no emulador/cartucho.

**Esta primeira R131 testa apenas leitura de ROM e troca de banco.** Não testa SRAM, persistência, coexistência com Z80/PCM ou velocidade real do DOOM. Esses testes exigem próximas variantes.

Referência de mapeamento: https://www.plutiedev.com/beyond-4mb.
