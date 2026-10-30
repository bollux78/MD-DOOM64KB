# R104: crash no console (ADDRESS ERROR) e correção das janelas de SRAM (Cláudio para o Werk)

**Status:** correção validada no hardware pelo usuário (2026-10-30). **A R104 mask substitui a R100 F1 como base.**

## 1. Sintoma
- No console (clone antigo de Everdrive, que salva a SRAM no SD e a restaura a cada boot), o benchmark trava com **ADDRESS ERROR** em `PIT_AddThingIntercepts`: thing = `0xBCFCFFFF`, acesso ímpar em `FD003F`.
- Acontece sempre no mesmo ponto da demo, em E1M1 e E1M7, da **R92 toggle em diante**. **R91 sh1/sh2 passam.** Jogando não trava.
- BlastEm nunca reproduz: a demo inteira roda limpa em todas as combinações, inclusive com a checagem de ponteiros.

## 2. Diagnóstico
1. O disassembly mostra que o ponteiro inválido vem da cabeça da lista de things do blockmap, lida da **SRAM do cartucho** com `movep` (`R22_BlockHead`, inline em `P_PathTraverse`).
2. A **R103 diag** valida cada ponteiro do iterador e troca o crash por uma tela de informação. No console:
   - com Shadow Off, passou (o layout e o timing mudaram);
   - com **Shadow On**, mostrou `TIC 2904 MAP 1 CELL 729 (36×23) HEAD 00400000`. Ou seja, a SRAM daquele slot continha lixo, e esses bytes não existem na ROM no endereço sob a janela.
3. Conclusão: corrupção dependente de **timing exato do hardware**. É determinística no console, aparece ou some com o layout e com Shadow On, e não acontece no emulador. Hipótese: o **VBlank entra no meio de uma janela `$A130F1=1`**. O ISR faz DMA de WRAM para a VDP, pede o barramento do Z80 e escreve na CRAM, enquanto a SRAM está mapeada sobre `$200000-$20FFFF`. Nessa faixa ficam também o fim do `bgm_episode` (XGM2) e o início do WAD.

## 3. Correção (`scripts/lab/apply_r104.py`, aplicada depois do `apply_r100.py`)
- `R25_SRAM_BEGIN` salva o SR, faz `ori.w #$0700,sr` e mapeia a SRAM. `R25_SRAM_END` desmapeia e restaura o SR. O SR salvo fica em `r104_sr` (2 B, sem aumento líquido de BSS no build).
- As duas sondas de carga de nível que abriam a janela com `R22_SRAM_ENABLE()` puro (`R22_BlockInit`, `R23_MapMemoryInit`) passam a usar `R25_SRAM_BEGIN`.
- Janelas não aninham. Um aninhamento deixaria as interrupções mascaradas e dispararia o timeout do VBlank; a demo completa no BlastEm (Off, A2, L3) não teve nenhum.
- `r81_save_codec.inc` continua com o enable/disable direto, porque só roda em save/load fora do jogo.

## 4. Validação
| Teste | Resultado |
|---|---|
| Console, `r104-maskdiag`, E1M1 Shadow On | passou: 7,66 FPS / 278,73 s |
| Console, `r104-maskdiag`, E1M7 Shadow On | passou: 5,06 FPS / 421,92 s |
| BlastEm, pixels Off e On A2/L3 pós-passe | idênticos à R100 F1 |
| BlastEm, tempo | +0,88% (Off), +0,93% (On), no trecho medido |
| Pilha / BSS | pico 1.632 B, BSS 57.876 (folga 44): igual à R100 |

Artefato: https://github.com/bollux78/MD-DOOM64KB/actions/runs/41120586563 (branch `exp-claudio-r104-srammask-20261030`).

## 5. Regras daqui para frente
- **Todo acesso à SRAM do cartucho passa por `R25_SRAM_BEGIN`/`END`**, com as interrupções mascaradas. Nada de `$A130F1` direto em código de jogo.
- Prova no emulador não basta para nada que toque SRAM, mapper ou timing de ISR: precisa de benchmark no console.
- Os números de FPS anteriores eram do BlastEm. As medidas do console são as da tabela acima.
- Candidatos futuros (R102 bits/twoface etc.) devem ser refeitos sobre a R104 mask.
- Possível ganho futuro: recuperar o ~0,9% juntando leituras da SRAM numa janela única (por exemplo, a cabeça e toda a cadeia de um bloco) ou movendo a lista de things para a WRAM. Isso só depois de medir no console.
