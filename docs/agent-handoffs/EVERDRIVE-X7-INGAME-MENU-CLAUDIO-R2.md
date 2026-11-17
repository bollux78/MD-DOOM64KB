# Handoff para Werk — menu in-game do Mega EverDrive X7 (Manifold), rodada 2

**Status:** NÃO resolvido. Três tentativas do Claude no Manifold falharam no X7 real. Peço que o Werk aplique/ajuste o patch
com o método de bissecção abaixo (o Claude não tem o X7; só o usuário testa em hardware).

Base: `EVERDRIVE-X7-INGAME-MENU-WERK.md` e `HANDOFF_Mega_EverDrive_X7_Menu_InGame_Generico.md`
(ROMs de diagnóstico do Tile Palette Studio abrem o menu com Baixo+Start e Save/Load State funcionam).

## O que foi tentado (branch `exp-manifold-m14-e1m1`, pasta `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/`)
| Tentativa | Mudança | Resultado no X7 |
|---|---|---|
| r087 | `crt0.s` `stub30` (vetor nível 6): a cada vblank lê TH=0 e TH=1, restaura o latch de TH, depois `rte` (fase menu) ou salta ao `_VINT` do mapa. `menu.c`: VDP reg1 0x44→0x64, flag `0xFF0034`='MVIN', `SR=0x2000`; `launch()` mascara SR, zera flag, desliga VDP. | menu do X7 não abre (nem na tela de abertura) |
| r088 | + `pad_read()` do menu deixa TH **alto** ao final (antes deixava baixo) | não abre |
| r088b | r088 com header `SEGA MEGA DRIVE` em vez de `SEGA SSF` (só diagnóstico) | não abre; gráficos completamente corrompidos (bancos >4 MiB não mapeiam sem SSF) |

Verificado só em emulador: MAME, ROM só com o menu → `stub30` roda 1× por vblank e retorna por `rte`. A ROM completa (SSF 12 MiB)
não roda no MAME (tela preta); BlastEm headless aqui também não renderiza. O emulador não valida o X7.

## Diferenças conhecidas entre a ROM validada (Tile Palette Studio) e o Manifold
1. **Mapper SSF / ROM de 12 MiB** (header `SEGA SSF`), escritas em `$A130F3..FF` (bancos) e `$A130F1` (SRAM). A ROM validada é pequena, sem mapper.
2. **Boot do Manifold** (`crt0.s`): TMSS, Z80, `SR=0x2700`, VDP/CRAM/VRAM clear, música (Z80/PSG/YM) — conferir se algo
   mantém o barramento do Z80 (`$A11100`) ocupado ou escreve em portas que o X7 usa.
3. **Ordem dos eventos:** na validada, V-Int + SR aberto + polling desde o primeiro quadro. No Manifold o menu só liga V-Int depois do setup do VDP.
4. **Pad:** `pad_read()` do menu escreve TH em `$A10003` fora do ISR; o ISR (`stub30`) restaura o latch.
5. **SRAM:** o jogo usa `$A130F1` (janela de SRAM do clone/X7); suspeita: ligar o mapeamento de SRAM pode desligar o hook do menu.
6. `JOY_update()` do SGDK (jogo) só roda 1× por quadro renderizado (2–8 FPS em combate), por isso o polling no vblank foi movido para o vetor.

## Plano de bissecção sugerido (menor para maior)
Partir da ROM validada do Tile Palette Studio e ir acrescentando, testando Baixo+Start no X7 a cada degrau (uma variável por ROM):
1. Mesma ROM validada, com **header `SEGA SSF`** e tamanho 4 MiB, 8 MiB, 12 MiB (preenchido com 0xFF) — isola header/tamanho.
2. + escritas dos registradores de banco `$A130F3..FF` na inicialização (sem usar os bancos).
3. + `$A130F1` (SRAM on/off) como o `menu.c`/jogo fazem.
4. + código de boot do Manifold (`crt0.s`) completo, tela de abertura mínima.
5. + `menu.c` completo.
Quando um degrau fizer o menu parar de abrir, esse é o culpado.

Alternativa rápida: levar o `stub30` do `crt0.s` para a ROM de diagnóstico e ver se ainda abre (descarta o código do vetor).

## Perguntas ao usuário (para o Werk coletar)
- O LED do X7 acende ao apertar Baixo+Start com a ROM do Manifold?
- O menu abre se o Manifold é carregado como ROM <= 4 MiB (por exemplo, só o menu + 1 mapa)?

## Regras de versão
O usuário pediu: **o número rXXX só sobe quando o experimento é aprovado.** Experimentos usam sufixo/tag (ex.: `x7-a`, `x7-b`), sem gastar número.
