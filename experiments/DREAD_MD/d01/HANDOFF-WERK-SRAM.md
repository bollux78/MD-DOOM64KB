# Handoff para o Werk — testes de SRAM na D01

O objetivo é medir quanto a SRAM de 16 bits acelera a **nossa** D01, nas mesmas condições das suas medições da Bermuda e da Alpha 2. A previsão do Cláudio é **até ~3,5%**: a D01 já desenha direto no formato de tile, na RAM, e manda por DMA no VBlank. A SRAM só ajuda o Ferret porque, sem ela, ele grava a imagem direto na porta do VDP durante a tela ativa. A medição serve para confirmar isso ou desmentir.

Base: branch `exp-dread-md-d01-claudio`, a partir do commit `f1f7b3d` ou mais novo. Inclui combate, céu, a correção da faixa, o limitador de FPS e os setores na ROM.

## Regras do projeto (não mudar)

- **O jogo tem que rodar igual sem SRAM.** A SRAM só pode ser usada quando o teste de presença confirmar que ela é de 16 bits. Com SRAM de 8 bits, ou sem SRAM, o caminho é o atual, na RAM.
- **Sem mapper ou SSF** na versão principal. O chaveamento pelo A130F1 só entra no teste B, e esse teste é só para medir.
- Não publicar WAD nem ELF. A ROM shareware pode ser pública.
- Toda ROM de teste:
  - abre numa tela preta com a fonte do SGDK mostrando o nome da ROM, o que ela testa e "aperte START ou aguarde 15 segundos";
  - leva o nome no cabeçalho;
  - é jogável.

## O conflito de endereço (por que existem dois testes)

A SRAM aparece em `0x200000`. A ROM do episódio tem 3,4 MB, então essa faixa também é ROM. As ROMs do Ferret têm 1,3–1,5 MB, por isso lá não há disputa.

- **Teste A, ROM com menos de 2 MB:** a SRAM fica em `0x200000` sem conflito. Para caber, use **poucas fases**, sem abertura e sem música. Por exemplo, E1M1 + E1M2, que inclui o começo pesado de E1M2. As texturas compartilhadas das 9 fases já ocupam 1,59 MB, então todas as fases não cabem.
- **Teste B, episódio inteiro com A130F1:** a SRAM só é ligada durante o desenho e o DMA. Isso exige que tudo o que pode ser lido nesse intervalo esteja **abaixo de 2 MB**:
  - texturas, sprites, mapa, PVS, escalonadores e código;
  - a música, porque o Z80 lê a XGM2 continuamente;
  - os frames da arma e do HUD, enviados por DMA no VBlank.

  Provavelmente não cabe. Comece pelo teste A e só faça o B se o A mostrar ganho.

## O que colocar na SRAM

1. **O framebuffer:** `fbuf` em `src/main.c`, linha ~51 (`static uint8_t fbuf[FB_MAX]`). Troque por um ponteiro: `fb_base = sram16 ? (uint8_t *)0x200000 : fbuf_ram`. O renderer escreve por esse ponteiro (`R_RenderView(&view, fb)`, linha ~717), e o VBlank faz o DMA a partir de `dma_src`. O DMA pode ler da faixa do cartucho.
2. **Um segundo framebuffer no modo colunas quando houver SRAM:** é o único lugar onde a SRAM pode dar ganho real. Hoje `nbuf = colb == 2 ? 1 : 2` em `set_mode()`, e no modo colunas o desenho espera o DMA terminar (`if (NBUF == 1) while (dma_src) {}`). Com a SRAM, use `nbuf = 2` também no modo colunas.
3. Opcional: uma build de controle **com a imagem do framebuffer não enviada** (sem o `DMA_doDma` da visão, só marcando como concluído). Ela mostra o teto de ganho de qualquer mudança no envio da imagem.

## Detecção (16 bits, 8 bits ou ausente)

- **Cabeçalho:** em `0x1B0`, `"RA"` + `0xF8 0x20` (SRAM em palavras), início `0x00200000`, fim `0x0020FFFF`. Só no teste A.
- **Em tempo de execução**, no `main()` antes de `set_mode()`:
  1. grave `0x55AA` e depois `0xA55A` como palavra em `0x200000`;
  2. leia de volta;
  3. se as duas palavras voltarem iguais, é 16 bits; se só o byte ímpar bater, é 8 bits (não usar); se nada bater, não tem SRAM.
- Não use o primeiro bloco se alguém já salvou algo nele. Hoje não salvamos nada.

## Como medir

1. **Benchmark do título:** a opção BENCHMARK percorre E1M1 com passos fixos. O limitador fica desligado no benchmark. Anote "BENCH 312 quadros X FPS".
2. **Começo de E1M2:**
   1. no título, use SELECT LEVEL → E1M2;
   2. na pausa, coloque **LIMITE: LIVRE**;
   3. gire para a esquerda durante 300 frames;
   4. conte as trocas do mapa de tiles da visão, do mesmo jeito que você contou na Bermuda.

   Referência do Cláudio no Genesis Plus GX sem SRAM: **4,8 FPS de média**. Olhando para a sala grande, 15 a 27 VBlanks por frame; nas outras direções, 4 a 9.
3. Para cada ROM, rode três configurações:
   - SRAM de 16 bits;
   - sem SRAM;
   - SRAM de 8 bits simulada.

   E nos dois modos: linhas e colunas.
4. Se puder, trave a cena: o mesmo quadro, sem atores (`bench_req`). Assim a cadência não muda as poses.

## Resultado esperado

| Modo | Ganho esperado com SRAM de 16 bits |
|---|---|
| Linhas | ~0 a 3,5% (já temos dois framebuffers na RAM) |
| Colunas | maior, porque deixa de esperar o DMA com o segundo framebuffer |

Se o modo linhas ganhar bem mais que isso, o Cláudio quer ver o profile.

## Onde gerar

- Use o workflow `.github/workflows/dread-md-ep.yml` ou `tools/build_map.sh EPISODE` com `DREAD_EXTRA_FLAGS`.
- Para o teste A, é preciso um modo de build com menos fases. Hoje o laço `for n in {1..9}` em `tools/build_map.sh` monta as 9. Sugestão: uma variável `DREAD_EP_MAPS="1 2"`, e o menu SELECT LEVEL listando só essas fases.
- As ROMs vão para `/home/dan/Projetos/Personal/dread-md/`, entregues num zip.
