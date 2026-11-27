# Dread source drop (Krzysiek-K/Dread-source-drop) — análise do Cláudio, 26/11/2026

Repositório: https://github.com/Krzysiek-K/Dread-source-drop (último commit "gitignore", KK, 30/10/2022).
Conteúdo: `dreadmake` (engine Amiga/Atari ST em C + 68000), `dreadcheat` (gerador de código dos laços de parede,
"codegen2"), `dreadtool` (editor/conversor de mapas e WAD, C++), `dread-main` (dados, mapas, mods), `Dread-public` (SDK).

## 1. Licença — ler antes de tudo
- **Não há licença para o código.** O repositório não tem arquivo LICENSE; código sem licença é "todos os direitos
  reservados" por padrão, mesmo público no GitHub.
- O único texto de licença (`Dread-public/SDK-data/_LICENSE_.txt`) diz: "All rights reserved. Copyright (c) 2021-2022
  KK/Altair" e permite usar o DreadTool e os assets só para uso pessoal, editorial ou no Discord do Dread, **"ONLY as long
  as it's done in the context of the Dread game project (... using the assets, or derivate works for other projects is NOT
  allowed)"**.
- Só os mapas e mods em `maps-contrib`/`mods-contrib` são CC-BY.
- **Conclusão:** não podemos copiar nem adaptar o código da Dread para a FERRET-MD/C7 sem permissão do autor (KK/Altair).
  Podemos estudar as técnicas (ideias e arquitetura não são protegidas) e reimplementar com código nosso, como já fazemos.
  Se o usuário quiser usar o código de fato, o caminho é pedir autorização ao KK.

## 2. Como a Dread desenha (o que explica a velocidade)
1. **Um laço de colunas gerado por tipo de parede** (`dreadmake/gen/render2_linedef_xNNN.s`, gerados pelo `dreadcheat`):
   cada combinação céu/teto/superior/piso/inferior tem sua rotina própria, sem testes de variante dentro do laço.
2. **Tudo em registradores, com "tracers" (DDA) para as bordas:** as alturas de cada coluna andam por soma com passo
   fracionário (sub-pixel em byte, pixel em word); o passo é calculado uma vez por parede (2 MULS + 1 DIVS por borda) e
   gravado no próprio código (código automodificável: `move.w d5,.trace_y0+4`). Nenhuma multiplicação ou divisão por coluna.
3. **Coordenada de textura afim por coluna** (`u1s`, `du`): soma por coluna, sem divisão de perspectiva por coluna.
4. **Desenho por salto para dentro de código desenrolado:** o ponteiro de destino é o `a7` com pós-incremento, coluna
   contígua; texturizado `move.b xxx(a2),(a7)+`, cor `move.b d5,(a7)+`, céu `move.b (a2)+,(a7)+`, e o fim é `jmp (a6)`.
   A entrada é `jmp (a5,dN.w)` calculado pela altura; a "escada" de casos (só céu, céu+superior, superior+piso...) decide
   quais trechos a coluna tem comparando os tracers com o recorte da coluna (ymin/ymax por coluna).
5. **Recorte por coluna** (`_render_columns`, ymin/ymax) e travessia frente-para-trás com BSP + lista de visibilidade por
   subsetor (`VIS`, `e_map_vislist`), a mesma família de estrutura que medimos na Alpha2.
6. A documentação (`dreadmake/doc/68k-timing.txt`, `Cycles.xlsx`, `codegen2.txt`) conta ciclos instrução a instrução.

## 3. Comparação com o que já sabemos (Alpha2 e FERRET-MD R13)
| Ponto | Dread | Alpha2 (medido pelo Werk) | FERRET-MD R13 |
|---|---|---|---|
| Laço de parede | gerado por variante, registradores, tracers | código gerado, ~27 ciclos/byte | C genérico com escada de ifs; texto em asm/gerado |
| Alturas por coluna | soma (DDA) | — | soma corrente de 32 bits (já sem multiplicação) |
| Textura por coluna | afim (soma) | — | perspectiva (DIVU por coluna) ou linear quando aprovado |
| Escrita | coluna contígua, `(a7)+` | destino pós-incrementado, passo 2 | coluna com passo 2 (pares de x intercalados) |
| Visibilidade | BSP + lista por subsetor | lista por célula (213 no zigzag) | FRV2 por célula + pré-testes inline |
| Por coluna, fora do núcleo | ~decenas de ciclos | — | ~milhares de ciclos (medido) |
A diferença de ~3,5x nas paredes vem do item "por coluna, fora do núcleo": a nossa preparação e decisão de cada coluna é em C.

## 4. O que aproveitar (reimplementando, sem copiar)
1. **Gerador próprio de laços de parede por variante** (as nossas 18 variantes de `wall_impl`), em Python, como já fazemos
   com `gen_scale.py`: rotina 68000 por variante, registradores fixos, sem testes de variante por coluna.
2. **Tracers DDA para r0..r3** (já temos as somas; falta mantê-las em registradores no laço gerado) e **u afim** onde a
   aproximação for aceitável (a R04 já tem o critério `linear`; medir o erro visual).
3. **Escrita com destino em registrador pós-incrementado:** exige framebuffer com coluna contígua (72 bytes por coluna) em
   vez do passo 2 atual; o `fr_tiles68k` muda junto (só a ordem de leitura).
4. **Escada de casos por coluna em asm**, com `jmp (aN,dN.w)` para dentro dos trechos desenrolados de cor/céu/textura.
5. **Contagem de ciclos no gerador** (comentários com ciclos por instrução), para prever o custo antes de medir.

## 5. O que muda no plano
- O caminho de micro-otimizar o C da FERRET-MD chegou ao limite (R06 5,17 s -> R13 ~3,5 s nas 12 poses, sempre exato).
- Próximo passo grande: **renderer de paredes no estilo Dread, com código gerado próprio** (itens 4.1 a 4.4), mantendo
  FRV2/visibilidade, pipeline de WAD, paleta, céu, apresentação assíncrona e as ferramentas de medição.
- Critério de aceite: imagem igual à atual onde a matemática for a mesma; onde mudar (u afim), mostrar a diferença e medir.
- O `FR_WALLASM`/protótipo do Werk deve seguir esse desenho (gerado por variante) em vez de uma rotina única.
