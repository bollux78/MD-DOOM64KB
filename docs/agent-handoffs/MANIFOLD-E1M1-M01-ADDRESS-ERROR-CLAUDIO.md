# HANDOFF CLAUDIO — Manifold E1M1 M01 / ADDRESS ERROR 68000
**Data:** 2026-11-09/10 (Brasília)  
**Projeto:** `bollux78/MD-DOOM64KB`  
**Branch exclusiva:** `exp-manifold-e1m1-m01`  
**Situação:** ROM binária compila; **NÃO HÁ validação gráfica/jogável**. Falha real reportada pelo usuário nas versões anteriores. Última versão com fallback C ainda **sem teste visual interativo**.

## 0. Objetivo e escopo
Continuar o *port experimental independente* do motor Manifold para o E1M1 de DOOM, produzindo ROM Mega Drive realmente inicializável e caminhável. Não confundir este experimento com DOOM nativo R128 ou subport Sega CD M1.5. **Não modificar as branches R128/SCD.** Manter WAD shareware privado apenas no self-hosted runner; não publicar WAD ou ROM obtida dele sem autorização. O usuário dispõe de BlastEm e console real e realizará testes, mas **não enviar ao hardware enquanto houver crash**.

## 1. Evidência real do problema
O usuário executou diferentes ROMs no BlastEm gráfico e observou corrupção gráfica e travamento que exigia matar o processo. Duas capturas consecutivas (anteriores ao fallback C) mostram a mesma tela:

```text
ADDRESS ERROR
Address: 08001D (unknown)
Offset: 080004 (unknown)
Hint:   008110 (unknown)
SR: 2400
A0: 40000010
A1: 00000000
A2: 00198FC
A3: 0000EA50
A4: 000081E0
A5: 00000000
```

**Cuidado com a interpretação:** os rótulos *Address*, *Offset* e *Hint* são os exibidos pelo depurador do BlastEm; **não assumir automaticamente que `Address` seja o PC da instrução culpada**. Em erro de endereço no 68000, pode representar endereço efetivo acessado. Reconstituir o frame de exceção e o PC real antes de concluir que houve salto inválido. O fato de `0x08001D` coincidir com um local do código é sugestivo, mas não comprova que esse código estava executando. A corrupção pode ter múltiplas causas (render, DMA/VDP, ponteiros, alinhamento, interrupções ou framebuffer).

## 2. Análise objetiva do ELF da ROM anterior
Em [run #42724087131](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42724087131), consultamos `m68k-elf-nm` e `m68k-elf-objdump` sobre `out/release/rom.out`:

```asm
0007fffe <scale_64_450_top_clip>:
7fffe: e588          lsll #2,%d0
80000: 4efb 001c     jmp %pc@(8001e <scale_64_450_jump>,%d0:w)

00080004 <scale_64_450_bot_clip>:
80004: d081          addl %d1,%d0
...
8001a: 4efb 0002     jmp %pc@(8001e <scale_64_450_jump>,%d0:w)

0008001e <scale_64_450_jump>:
8001e: 32e8 0000     movew %a0@(0),%a1@+

00008110 <bmp_do_hblank_process_vertical>:
8110: 518f          subql #8,%sp
```

Assim, **naquela build específica**, `0x08001D` fica um byte antes de `scale_64_450_jump` e `0x080004` na entrada `scale_64_450_bot_clip`. `0x008110` é início da rotina HBlank vertical. O deslocamento varia com layout/linkagem, portanto **nunca mapear esses endereços contra o ELF de outra build**. Os geradores relevantes são `src/python/gen_postinc_tex_tables.py`, `src/tex_table_lookup.c`, `src/tex_draw_tables.s` no Manifold original; consumidores em `src/texture.c`, `src/draw.c`.

## 3. Correções já implementadas e seus limites
Os scripts da experiência estão sob `experiments/DOOM_Manifold_E1M1/m01/`:
- `bootstrap.py`: baixa/copia Manifold no commit travado `b6fe52a52344464de00bde4dc58a40f8b89cfc1a`.
- `convert_wad.py`, `bsp_cells.py`: extraem dados do WAD e recuperam **237 células BSP E1M1**.
- `emit_portal_map.py`: emite `e1m1_map.c` com **1112 paredes atômicas**, contornos e setores. **112 arestas internas sem par** são tratadas como **paredes sólidas**; relatório declara `safe_for_runtime: false`. Isso **não é geometria aprovada**. Há PVS/PHS all-visible provisório, nenhuma THING, portas/triggers incompletos, cores genéricas.
- `stage_rom.py`: adapta compatibilidade SGDK, corrige assinaturas C e registra spawn real; separa a cópia de trabalho do upstream; silencia `KLog` legado (o qual provocava aparente travamento no emulador headless).
- Paredes provisórias marcadas **sólidas, não texturizadas**; adicionados `wall_tex_repetitions` e `collision_vertexes`.
- **Fallback diagnóstico:** `replace_generated_vertical_scalers_with_checked_c(out)` substitui em `src/texture.c` as implementações com jump-tables de `draw_texture_vertical_line` e `draw_bottom_clipped_texture_vertical_line` por loops C com verificações de limites/alinhamento. **Não reivindicar equivalência ou correção visual:** checar unidade/pitch de `col_ptr`, indexação do destino `dst[(y0+i)]`, formato de texel, offsets, e potencial overflow em buffers. O docstring chama `0x08001D` de "PC"; isso **não está demonstrado** pelo print e deve ser corrigido conceitualmente.

## 4. Estado objetivo das Actions
- [Run #42724327838](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42724327838) — mapa com paredes sólidas/tabelas adicionadas, build **SUCCESS** e BlastEm headless 90 quadros, **mas usuário ainda obteve ADDRESS ERROR nessa linha de versões**.
- [Run #42729309940](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42729309940) — **primeiro binário com fallback C**, build **SUCCESS**, 90 quadros headless; tamanho 1.048.576 bytes.
- [Run #42729443144](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42729443144) — última build verificada: **SUCCESS** com **1200 quadros headless**, ROM de 1.048.576 bytes, SHA-256 `849b8dcef8b80a36159f8b5d4975346dd01f015691a47c8daf632c60b9ce733a`. Esses quadros apenas confirmam retorno do comando BlastEm em lote, **não validam conteúdo visual/ausência de ADDRESS ERROR**.

**ROM diagnóstica atual no runner do usuário:**
```text
/home/dan/Projetos/Personal/manifold-e1m1/run-42729443144-1/doom-md-manifold-e1m1-m01.bin
```
**Nenhum teste visual interativo do usuário foi comunicado para essa ROM com fallback C.** O teste gráfico em BlastEm é o próximo gate. Não chamar de ROM funcional.

**Infra:** runner self-hosted CachyOS, SGDK/MARSDEV via GitHub Actions `.github/workflows/manifold-e1m1-rom.yml`. Incompatibilidade prévia SGDK `libmd.a` LTO 13 vs GCC 15 foi contornada na compilação usando `-fno-lto` e objetos fat da biblioteca. O WAD é privado no runner.

## 5. Pedido ao Claudio — prioridades
1. **Confirmar frame de exceção do 68000** e distinguir endereço acessado de PC. Ideal: capturar execução no BlastEm debug de modo reproduzível, com arquivo ELF da *mesma ROM* e `objdump --disassemble`/mapas de símbolos e trace no instante da exceção, incluindo chamadas HBlank/VDP.
2. **Auditar a rotina de HBlank e os buffers:** `src/my_bmp.c`, `bmp_do_hblank_process_vertical`, `do_vint_flip`, `src/my_bmp_a.s`, interrupções, ponteiros de framebuffer em RAM/VRAM, DMA e limites. O Hint `0x008110` coincide com essa rotina na build anterior, sem provar que seja a origem.
3. **Auditar geradores e consumidores das jump-tables de escalonamento:** `src/python/gen_postinc_tex_tables.py`, `src/tex_table_lookup.c`, `src/texture.c`, `src/draw.c`. Testar índices `0..512`, `clip_top`, `clip_bot`, `unclipped_dy`, uso de `d0/d1`, constraints de ASM e offsets PC-relative. Confirmar se `Address: 08001D` era código ou dado.
4. **Auditar o fallback C diagnóstico** de `stage_rom.py`, sobretudo `col_ptr`, endereçamento por linha/coluna e acesso de 16 bits. Preferir uma implementação segura, explicitamente limitada, a saltos ASM rápidos mas não validados.
5. **Isolar a imagem correta primeiro:** criar testes progressivos com marcadores visuais SGDK no início, após init, após 1 quadro e após flip, além de validação automática com screenshot real ou execução visível — não marcar PASS só porque BlastEm `-b` retornou 0. Se necessário, desativar renderer inteiro e habilitar paredes uma a uma.
6. Depois de estabilizar vídeo, **resolver 112 arestas não pareadas** sem fabricar portais; verificar fechamento de células, adjacências e atravessabilidade; somente depois aperfeiçoar texturas/cores, objetos e gameplay.

## 6. Critérios de aceite
- ROM inicia no BlastEm gráfico sem **ADDRESS ERROR** ou corrupção de vídeo.
- Permanece renderizando vários segundos sem congelamento; movimentação e rotação verificadas.
- Vista E1M1 reconhecível ainda que com cores/paredes provisórias.
- Logs/ELF/ROM com SHA e ID de Action rastreáveis.
- Somente depois do aceite gráfico: teste em Mega Drive real pelo usuário.
- Sem alterações nas branches R128/SCD e sem publicação do WAD privado.

## 7. Links para o trabalho
- [Branch da experiência](https://github.com/bollux78/MD-DOOM64KB/tree/exp-manifold-e1m1-m01)
- [`stage_rom.py`](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/experiments/DOOM_Manifold_E1M1/m01/stage_rom.py)
- [`emit_portal_map.py`](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/experiments/DOOM_Manifold_E1M1/m01/emit_portal_map.py)
- [`manifold-e1m1-rom.yml`](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-e1m1-m01/.github/workflows/manifold-e1m1-rom.yml)
- [Última Action #42729443144](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42729443144)
- [Action ELF/disassembly #42724087131](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42724087131)

**Entrega solicitada ao Claudio:** revisão técnica fundamentada, diagnóstico provável com evidências e patch mínimo *na branch experimental*, com ROM nova e critérios de teste reproduzíveis. Se o bug não puder ser demonstrado conclusivamente, reportar hipóteses e evidência faltante, em vez de declarar resolvido.
