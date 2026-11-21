# Handoff para o Werk — pulos no modo linhas e tela preta no modo colunas

Branch `exp-dread-md-d01-claudio`. A ROM com os dois problemas é a do run 44922171487 (commit `d4f9f4b`). Os dois vêm de mudanças do Cláudio de hoje. O diagnóstico e as correções estão abaixo.

## 1. Modo colunas: tela preta

**Causa (commit `a042caf`, "display off above the view").** No modo linhas, o VBlank desliga a tela nas linhas 0–15, e o `hint_a` religa antes da visão. No modo colunas não há interrupção de linha (`hint_on = 0`), e o VBlank não desliga a tela. Só que, ao trocar de linhas para colunas pelo menu, a tela pode ter ficado **desligada** pelo último VBlank do modo linhas. Ninguém religa depois disso. A tela preta aparece também ao entrar direto se o modo inicial passar por esse caminho.

**Correção, em `set_mode()` (`src/main.c`, perto da linha 142):** depois de calcular `hint_r1on`, religue a tela sempre:

```c
    hint_r1on = 0x8100 | VDP_getReg(1) | 0x40;
    *(volatile uint16_t *)0xC00004 = hint_r1on;      /* display on (colunas never runs hint_a) */
    hint_on = colb == 1;
```

Confira também a pausa e o título. Se algum caminho desliga a interrupção de linha (`hint_on = 0`) fora de `set_mode()`, ele precisa religar a tela do mesmo jeito.

## 2. Modo linhas: pulos na imagem

**Causa (commit `62a1f67`, "minimal H-int").** O `hint_b` novo não lê mais o contador de linha. Cada chamada desce **uma** linha da imagem, supondo que as chamadas estão sempre exatamente 2 linhas de vídeo uma da outra. Se alguma interrupção atrasa mais de uma linha ou se perde, todo o resto da visão fica deslocado naquele quadro. É o "pulo". Atrasos podem vir de interrupções mascaradas, de uma instrução longa do 68000 ou de algum acesso ao VDP fora do VBlank. A versão anterior se corrigia sozinha a cada chamada.

**Opção A — voltar ao `hint_b` robusto (a mais segura).** Restaure o `hint_b` de `src/hint.s` do commit `d851704`/`a042caf`, que recalcula a linha pelo contador do VDP a cada chamada. Mantenha o `hint_a` atual, que liga a tela (`hint_r1on`) e grava `hint_v`. O custo de volta é de ~3% de FPS: o benchmark cai de 3,64 para ~3,53.

**Opção B — robusta e barata, com tabela (recomendada se quiser manter o ganho).** O contador vira índice de uma tabela de valores de rolagem pré-calculados:

```asm
hint_b:
        move.l  %d0,-(%sp)
        moveq   #0,%d0
        move.b  0xC00008,%d0                /* V counter (current line) */
        add.w   %d0,%d0
        move.l  #0x40000010,0xC00004
        move.w  hint_tab(%pc,%d0.w),0xC00000   /* (see note on the table placement) */
        move.l  (%sp)+,%d0
        rte
```

- A tabela `hint_tab` tem 256 palavras, indexadas pela linha L. Para cada L, ela guarda o valor de rolagem da linha L+1: `-(min((L + 1 - 15) >> 1, 72))`. Antes da visão o valor é 0. Abaixo da visão, `-72`.
- Para desligar a interrupção depois da visão, use uma de duas formas:
  - teste um valor sentinela na tabela;
  - deixe a interrupção ligada e aceite as chamadas restantes, até a linha 224, gravando `-72`. Custa ~32 chamadas por quadro, mas é bem mais simples.
- `d8(PC,Xn)` só alcança ±127 bytes. Coloque a tabela numa seção `.data` ou `.text` logo depois da rotina e use `lea hint_tab,%a0` com um registrador a mais salvo. Outra saída: tabela em RAM com endereço absoluto mais índice. O que importa é ter **nenhum desvio** e uma única leitura do contador.
- Custo estimado: ~110 ciclos por chamada, contra ~150 da versão robusta antiga e ~95 da mínima atual.

**Como testar.**
1. Rode o modo linhas com o limitador em **LIVRE**, andando e girando por ~2000 frames no começo de E1M2 e no benchmark.
2. Procure frames com faixas fora de lugar. O Cláudio detecta isso comparando linhas vizinhas: na visão (linhas 17–160), as linhas devem vir em pares iguais. A exceção é a região da arma, que é sprite em resolução cheia.
3. Confira que o benchmark continua saindo **idêntico pixel a pixel** à build `d4f9f4b`, e anote o FPS.
4. Teste no console. Os pulos podem aparecer só no hardware.

## 3. Depois das duas correções

- Teste também a troca de modo pelo menu nas quatro combinações: H40 e H32, linhas e colunas. Em todas, entre e saia da pausa.
- Entregue a ROM em zip em `/home/dan/Projetos/Personal/dread-md/`, com o link do artefato.

Referências de FPS no Genesis Plus GX, build `d4f9f4b`, modo linhas:

| Cena | FPS |
|---|---|
| Benchmark de E1M1 | 3,64 |
| Começo de E1M2, girando 300 frames | ~5,1–5,2 |
