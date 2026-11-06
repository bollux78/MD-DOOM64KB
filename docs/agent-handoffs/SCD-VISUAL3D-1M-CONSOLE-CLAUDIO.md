# SCD Visual 3D: "WORD RAM 1M INIT TIMEOUT" no console (Cláudio para o Werk)

**Base:** run 42250299505 (`b2a112c`). No BlastEm passa. No console com Sega CD acoplado, para em `WORD RAM 1M INIT TIMEOUT`.
**Estado:** só diagnóstico, **não executado**.

## O que a mensagem prova
- `boot_sub()` passou: reset, bus request, cópia e verificação da PRG-RAM, e release.
- A falha está no laço seguinte. Ele espera **ao mesmo tempo** a assinatura `0x5343` em `$A12020` **e** `$A12003 & 7 == 4` (MODE=1, DMNA=0, RET=0).
- Isso tem duas causas possíveis, que a tela atual não distingue:
  1. **O sub não chegou lá:** travou, caiu numa exceção (o handler escreve `0xDEAD`, mas o laço só mostra "timeout") ou demorou mais de 60 VBlanks;
  2. **O sub chegou,** mas no hardware real o registrador de modo fica num estado diferente do que o BlastEm mostra, por exemplo DMNA=1 ou RET=1 logo depois da troca 2M→1M.

## Patch de diagnóstico (este commit)
- **Sub:** grava o estágio em `$FF8022` = `$A12022` no principal. Os valores:

  | Valor | Significado |
  |---|---|
  | `5301` | entrou no `entry` |
  | `5302` | texturas prontas |
  | `5303` | 1M pedido |
  | `53FF` | exceção |

  Grava também em `$FF8024` o registrador de modo lido pelo próprio sub logo depois da troca.
- **Principal:** no timeout, imprime:
  - `SIG xxxx STAGE xxxx`
  - `MAIN MEM xxxx SUB MEM xxxx`

  Os registradores de status do sub podem guardar valores de uma execução anterior. Só vale o que o sub escreveu nesta: `53xx`.

## Como ler a tela no console
| Resultado | Diagnóstico | Próxima correção |
|---|---|---|
| STAGE não é `53xx`, ou é `5301` | o sub não roda ou trava cedo | revisar o boot do sub no hardware: vetores, WP da PRG-RAM, reset/release |
| `53FF` / SIG `DEAD` | exceção no sub | ver o handler: fixar uma pista do vetor |
| `5302` parado | travou entre as texturas e a troca de modo | acesso inválido |
| `5303` e `MAIN MEM & 7` ≠ 4 | o sub fez a troca, mas o estado real difere | aceitar MODE=1 e ler RET/DMNA reais; ver abaixo |

## Pontos de hardware real a considerar (fonte: Genesis Plus GX, `core/mem68k.c` e `core/cd_hw/scd.c`, conferido no mcd-verificator do Krikzz)
- Em 1M, escrever **0** em DMNA pelo principal **liga** DMNA, ou seja, pede a troca. O protocolo atual (`CD_MEMCTRL = 0`) depende disso. No GPGX funciona igual ao console, então é provável que esteja certo. O comentário em `boot.s` ("clearing DMNA") é que está enganoso.
- Escrever **1** em DMNA em 1M marca o retorno ao sub no próximo 2M. Evitar.
- O GPGX não marca DMNA=1 ao trocar 2M→1M. Se o console mostrar DMNA=1, a correção é o principal aceitar `MODE=1` e descobrir o banco pelo RET.
- **Teste recomendado:** rodar a mesma ROM no **Genesis Plus GX** (RetroArch), que modela essas peculiaridades melhor que o BlastEm, antes de voltar ao console.

## Relatório
- `build: PASS/FAIL`;
- `blastem: PASS/FAIL` (tem de continuar passando);
- `gpgx: PASS/FAIL` (opcional);
- foto da tela do console com as duas linhas de diagnóstico.
