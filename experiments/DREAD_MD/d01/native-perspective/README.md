# Dread native perspective — primeiro núcleo reconstruído

22/11/2026. Branch `exp-werk-dread-native-perspective-20261122`.
Base D01 completa: árvore de `42f17f26b1e3187ad7995799891cb50bd090e66c`.
**Experimento, não substituto aprovado do motor. Não é uma reconstrução completa da Ferret.**

## Problema e mudança concreta

O sampler anterior calculava a origem no topo recortado com `zq` e executava um scaler com passo quantizado diferente. Além disso, interpolava U e profundidade por blocos de 16 colunas. Isso pode criar diferenças de fase nas texturas entre colunas e entre recortes. Não prova que toda distorção percebida pelo usuário tenha essa única causa.

Novo caminho de paredes em H40/H32 com colunas lógicas de dois pixels:

- Escala escolhida diretamente pela profundidade inversa, por tabela ROM. Evita converter inverso em profundidade, multiplicar e quantizar de volta.
- Scalers independentes, gerados matematicamente, ancorados no horizonte. O deslocamento de um texel depende da linha absoluta, não do início do recorte. 160 níveis logarítmicos; não são os 2.048 seletores da Ferret.
- Núcleos 68000 MOVE.B/DBRA/RTS residentes em ROM. Nenhuma escrita em código ROM, SRAM ou uso inseguro de SP como framebuffer.
- U racional por coluna, usando quociente/resto: `r=N-uD`, `A=dN-u*dD`. Avança `D+=dD; r+=A`, ajustando quociente e resto por ADD/SUB/CMP. O laço não usa DIV/MUL por coluna. Há uma estimativa com DIVU e quatro MUL no setup por segmento.
- Guardas usam os deslocamentos realmente emitidos para não ler além de H+pad. Spans com wrap usam o caminho genérico mascarado, com o passo selecionado. O caminho genérico continua calculando origem e tem arredondamento ligeiramente diferente; não foi eliminada toda aproximação.

Referências estudadas: `Krzysiek-K/Dread-source-drop`, em especial os núcleos `render2_linedef_x001[p].s`, e a engenharia reversa preservada em `research-ferret-alpha2-reconstruction/research/ferret-alpha2`. Código aqui é uma implementação independente dessas técnicas; não inclui código máquina extraído da ROM Ferret ou suas imagens estáticas.

## Resolução completa no menu

START → DETALHE alterna LINHAS → COLUNAS → ALTURA COMPLETA; esquerda percorre no sentido inverso. TELA continua alternando H40/H32.

| Modo | Amostras lógicas | Apresentação |
|---|---:|---|
| H40 linhas |160×72|320×144, linhas duplicadas por H-int|
| H40 colunas |80×144|320×144, quatro pixels por coluna|
| H40 altura completa |160×144|320×144, dois pixels por coluna, sem duplicação de linhas|
| H32 linhas |128×72|256×144|
| H32 colunas |64×144|256×144|
| H32 altura completa |128×144|256×144, sem duplicação de linhas|

**ALTURA COMPLETA não significa 320 amostras horizontais independentes.** O formato de cor atual é um byte por par de pixels. Em altura completa há um buffer RAM de 23.040 bytes e um banco VRAM; não há H-int de duplicação. O custo maior é esperado e não foi usado para alegar ganho de FPS.

Arma, HUD, música e E1M1–E1M9 permanecem no episódio. São 4.194.304 bytes na ROM experimental, 3.538.944 no controle; sem mapper, SRAM ou Sega CD.

## Resultado medido

Genesis Plus GX instrumentado, NTSC, sem SRAM e sem Sega CD. Mesmo WAD/cache, toolchain m68k-elf GCC 13.1, música ligada, benchmark de menu E1M1 de 312 imagens, dt=4, H40 linhas, IA pausada pelo benchmark. Três repetições idênticas de cada variante. A tela usa truncamento para duas casas.

| Variante |VBlanks|FPS normalizado a 60 Hz|
|---|---:|---:|
| Controle |5.244|3,569794|
| Novo sampler |5.279|3,546126|

Perda de FPS **0,663%**. Não é um ganho de velocidade. Primeiro protótipo marcou 6.511 VBlanks; a seleção direta e a recorrência reduziram esse custo para 5.279. A comparação com Ferret ainda exige mesma pose/conteúdo/método; seus 7–8 FPS históricos não são um resultado deste benchmark.

`evidence/results.json` contém repetições, hashes, versão e condições. Capturas dos mesmos quadros estão em `comparison-001/070/150.png`; diferenças são intencionais na amostragem. **Não há validação de igualdade visual com a ROM Ferret.**

Testados seis modos H40/H32, ida/volta dos detalhes, E1M2/E1M8 com controles e final fullscreen do benchmark. Isso não prova todos os mapas/portas/ângulos nem ausência de glitches no console.

## Por que a diferença de arquitetura continua

A D01 ainda faz BSP, bbox, projeção de segs e geração dos registros de bordas antes de desenhar. A Ferret estudada tem streams de visibilidade já preparados e kernels de parede com avanço encadeado em registradores. Ela também usa outro layout de framebuffer e outra publicação ao VDP. Apenas trocar o sampler não remove esses custos.

Perfil no spawn parado, 300 quadros de vídeo, IA pausada, intervalos por símbolos no core instrumentado (exclusivos por endereço; não são tempos inclusivos de função):

| Faixa de código |Controle|Novo sampler|
|---|---:|---:|
| `seg_columns` clipping/despacho |16,21%|16,19%|
| `render_node` percurso |12,76%|13,12%|
| `draw_seg_body` preparação |10,78%|10,83%|
| `proj` |5,47%|5,61%|
| `bbox_visible` |3,89%|4,02%|
| `hint_b` |8,47%|8,48%|

Os percentuais são da execução instrumentada nessa condição, incluindo esperas em outras faixas. **Não somar rótulos como se fossem etapas completas**, e não comparar diretamente com perfis Ferret de cenas diferentes. Arrays foram zerados antes de cada perfil. JSON brutos preservados.

## Próximas partes ainda não reconstruídas

1. Substituir as fases separadas de bordas e desenho por kernels especializados Dread com avanço de bordas em registradores, conservando recorte de atores e portas. O sampler novo pode ser a referência visual dessa etapa.
2. Gerar streams de visibilidade offline com ordem válida por célula e condições; não repetir B1 que reconstrói listas a cada posição.
3. Ensaiar buffer intercalado e publicação separadamente. Medir se a conversão e o tráfego extras compensam remover H-int; não presumir SRAM16.
4. Geometria/projeção ainda usa reciprocais e near-clipping D01. Comparar poses idênticas com Ferret antes de afirmar perspectiva equivalente.

Portanto esta entrega inicia a reconstrução solicitada e recupera o modo de detalhe; **não encerra a tarefa de igualar o renderer inteiro da Ferret**.

## Compilar e repetir

WAD shareware local; não versionar WAD/ELF/ROM original Ferret.

```bash
export GDK=/caminho/SGDK
# DREAD_COPY_SEGA_S=1 se necessário para seu SGDK local
bash experiments/DREAD_MD/d01/native-perspective/build.sh /caminho/doom1.wad /tmp/native-out
python3 experiments/DREAD_MD/d01/native-perspective/check_recurrence.py
```

Cache opcional: `DREAD_PREPARED_MAPS` aponta para diretório contendo E1M1..E1M9 gerados pelo mesmo conversor/flags. Sem cache, o script prepara tudo.

Para medir com o core instrumentado publicado na pesquisa (exporta `retro_sram_block`):

```bash
export DREAD_TEST_ROOT=/tmp/native-out
export DREAD_TEST_CORE=/caminho/genesis_plus_gx_libretro.so
export DREAD_TEST_NM=/caminho/m68k-elf-nm
python3 experiments/DREAD_MD/d01/native-perspective/measure_route.py control native
python3 experiments/DREAD_MD/d01/native-perspective/check_modes_maps.py control native
```

`check_recurrence.py`: 811.353 verificações contra divisão inteira exata, incluindo U/profundidade crescentes e decrescentes. Valida a recorrência, não a imagem inteira nem todas as condições de overflow possíveis em mapas arbitrários. O probe de modos verifica estado/resposta e gera screenshots; não é prova pixel a pixel de correção desses modos.
