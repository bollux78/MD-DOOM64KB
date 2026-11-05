# R135: correção do "SRAM MAP STATE UNAVAILABLE" na R134 (Cláudio para o Werk)

**Branch:** `exp-claudio-r121-e1m7-20261103`. **Estado:** código pronto, **não executado**.

## Causa
- O cabeçalho `SEGA SSF` (gravado por `r132_doom5m.py`) liga no BlastEm o mapper **SSF estendido da Mega EverDrive** (`MAPPER_SEGA_MED_V2`, `romdb.c`). O mesmo acontece nas EverDrive X3/X5/X7/Pro.
- Nesse mapper, `$A130F1` **não liga SRAM**: toda escrita em `$A130F0/F1` sem o bit 15 (`0x8000`) é ignorada (`sega_mapper.c`, `write_bank_reg_w`). O `$200000` continua sendo a página 4 da ROM, que é só leitura. O teste de escrita e leitura de `R23_MapMemoryInit` falha e chama `I_Error`.
- As ROMs de 4 MiB usavam o mapper clássico, em que `$A130F1=1` sobrepõe a SRAM. Por isso só a ROM de 5 MiB quebra.
- A R133 e a R134 passam no próprio teste porque ele só **lê** as páginas 8 e 9. O erro aparece quando o jogo ou a demo carrega o mapa.

## Correção (`scripts/lab/apply_r135.py`, rodar depois de `apply_r133.py` e `apply_r134.py`)
No SSF estendido, a própria memória do cartucho fica gravável com `$A130F0` bit 13 (`0x2000`) junto com o bit 15. A janela de SRAM passa a ser:

| Momento | Escritas |
|---|---|
| BEGIN | `$A130F9` = 10 (slot 4 → página 10, livre, logo depois dos 5 MiB); depois `$A130F0.w` = `0xA000` |
| END | `$A130F0.w` = `0x8000` (proteção de escrita, slot 0 = página 0); depois `$A130F9` = 4 |

- A ordem garante que a página 4 da ROM nunca fica gravável.
- `R22_SRAM_BASE` e o layout em bytes ímpares não mudam. Nenhuma RAM é adicionada.
- Só vale com `DOOM_R133_SSF_BOOT` (os builds SSF de 5 MiB). Os builds de 4 MiB ficam byte-idênticos.
- O estado do mapa é refeito a cada carga, então não precisa persistir.
- Requisito: o cartucho precisa de pelo menos 5,5 MiB de RAM. O BlastEm dá 16 MiB.

## Como testar
1. No workflow `r134-freedoom-maps.yml`, linha 89: acrescentar `python3 scripts/lab/apply_r135.py` depois de `apply_r134.py`. Não coloquei isso em `paths:` para não disparar sozinho.
2. Testes no BlastEm:
   - a tela da R133/R134 continua toda PASS;
   - a demo 1 (E1M1) e um PLAY entram no mapa sem o erro;
   - lógica idêntica à R128 All em 10/10 demos (`r118_logic_check.py`), porque só o lugar da SRAM mudou.
3. Console: a ROM de 5 MiB no clone. Se der o mesmo erro no clone, ele talvez não implemente o SSF estendido. Nesse caso, testar a alternativa B.

## Alternativa B (sem mudar código)
- Cabeçalho `SEGA MEGA DRIVE` com o fim da ROM em `0x3FFFFF` e o arquivo com 5 MiB.
- O BlastEm então usa o mapper SSF2 clássico (`size > 4 MiB && rom_end <= 4 MiB`), em que `$A130F1` liga a SRAM como antes.
- Nas EverDrive, porém, o mapper costuma ser escolhido pelo `SEGA SSF`. Sem ele, as páginas 8 e 9 podem não existir. Por isso a recomendação é a R135.

## R135b: `R_GetTextureNumForName: texture name: SKY1 not found` (BlastEm)
**Causa:** a R135 trocou só os macros. O codec de save (`src/r81_save_codec.inc`, `R81_SramRead/Write`) abria a janela pelo macro, mas fechava com escrita crua em `$A130F1`. O mapper estendido ignora essa escrita, então:
- o slot 4 ficava **permanentemente** na página 10, e a ROM `$200000-$27FFFF` (lumps do WAD, como TEXTURE1) passava a ser lida como RAM de estado;
- o cartucho ficava **gravável** (bit 13 ligado);
- resultado: `SKY1 not found`.

**Correção (no mesmo `apply_r135.py`):**

| Arquivo | Problema | Mudança |
|---|---|---|
| `r81_save_codec.inc` | fechamento cru da janela (2×) | usa `R22_SRAM_DISABLE()` nos builds SSF: volta o slot 4 para a página 4 e o cartucho para só leitura |
| `r_draw.c` (`R_SramCacheInit`) | abertura crua (ignorada); o teste do cache falhava em silêncio | usa `R22_SRAM_ENABLE()` |
| `r21_prof.c` | escreve `$A130F1` direto | `#error` nos builds SSF: o profiler R21 não vale nesse mapper |
| — | configuração sem janelas | `#error` se o build SSF não tiver `DOOM_R25_MUSIC` ou tiver `DOOM_R27_SRAM_FIXED`, porque a página 10 esconderia a ROM para sempre |

- **Auditoria fail-closed:** o script falha se sobrar qualquer escrita crua em `$A130F1` em `src/` fora da lista conhecida. Todas as que sobram estão em ramos não-SSF.
- **Restauração dos bancos:** depois de qualquer acesso, ficam slot 4 = 4, slot 7 = 7 (a R133/R134 já restaura), `$A130F0` = `0x8000` (só leitura, slot 0 = página 0). Na ordem de fechamento, a proteção de escrita vem antes da troca de página.

## Validação (separar "compilou" de "rodou")
**Fase 1, compilação:**
- `apply_r133.py`, `apply_r134.py`, `apply_r135.py` (o script imprime `audit ok`);
- BSS ≤ 57.920;
- música abaixo de 2 MB (`r122_z80_layout.py --require`).

**Fase 2, execução no BlastEm**, sem liberar para o console antes de passar tudo:
1. Tela da R133/R134: tudo PASS.
2. Demos 1–4 (E1M1–E1M4, cobre a SKY1 e o carregamento de mapa) até o fim, sem `I_Error`. Captura de tela no meio de cada uma, com céu e paredes visíveis.
3. `r118_logic_check.py` contra a R128 All de 4 MiB, nas 10 demos, com checkpoints idênticos. Isso prova que a ROM acima de 2 MB e o estado do mapa leem o mesmo que antes.
4. PLAY: carregar o E1M1, andar alguns segundos, voltar ao menu e carregar outro mapa (exercita o codec de save/estado).
5. Um único relatório marcando separadamente `build: PASS` e `blastem: PASS/FAIL`, com as capturas.
