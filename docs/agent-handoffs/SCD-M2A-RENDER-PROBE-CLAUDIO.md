# M2a: o renderer R128 no 68000 do Sega CD, medido (Cláudio)

**Branch:** `exp-werk-scd-subport-s1s2`. **Ferramenta:** `experiments/DOOM_SCD_SubPort/m2/render_probe.py`, workflow `scd-subport-m2.yml`. Só reporta nomes e tamanhos.
**Runs:** 42487894055, 42488193032, 42488481842 (`build: PASS` da sonda; nenhuma ROM).
Feito em paralelo ao M0/M1 do Werk, sem tocar no código S2e.

## 1. Descoberta principal: o renderer R128 depende do mapa em "SRAM"
- Com os defines do sub de hoje (sem R22/R23/R25/R81), **`r_draw.c` não compila**: `r89_rom_pending` não declarado. `p_map.c` e `r24_romthings.c` também falham.
- **Solução testada (variante `sram-in-ram`):** manter **todos** os defines da R128 e mover a "SRAM" do cartucho para a PRG-RAM do sub:
  - `R22_SRAM_BASE`/`DOOM_SRAM_FIRST`/`DOOM_SRAM_CONTROL` → `SCD_SRAM_BASE` (RAM), mantendo o layout em byte ímpar;
  - `R22_SRAM_ENABLE/DISABLE` → no-op.

  O patch é só de texto, em `r22_blocklinks.h` e `r_draw.c`, numa cópia da árvore.
- Resultado: **83 de 85 fontes compilam.** Só falham `i_genesis.c` e `r25_music.c`, por `music.h` do MD, e esses não vão para o sub. **O código de render é o mesmo da R128.**
- **Custo:** o mapa em layout de SRAM ocupa 64 KiB de RAM do sub (2× a capacidade de 16.384, por causa das posições ímpares). Os acessos com MOVEP/byte ímpar continuam funcionando em RAM.
- **Ganho de brinde:** sem janelas reais nem IRQ mascarado, cada acesso fica mais barato que no MD.

## 2. Tamanho do fechamento de `R_RenderPlayerView` (gc-sections, variante `sram-in-ram`)
| Item | Tamanho |
|---|---|
| **Funções** | **80,7 KiB** (`R_Subsector` 17 KiB) |
| BSS | 8,8 KiB (`r22_fb` 3.352 B) |
| Const | 924 KiB, detalhado abaixo |
| Não resolvidos | **só 7:** `I_Error`, `memcpy`, `memset`, `DMX_Play`, profiler R21 (×3) |

Todos já existem ou são triviais no sub (S1e tem libc/`I_Error`).

| Tabela const | KiB | Quem usa | Destino no sub |
|---|---|---|---|
| `r91_joint` | 512 | não há relocação de nenhuma função. Fica pela seção do `.s` gerado | **não carregar.** Separar o `.s` ou linkar sem ele; confirmar com `nm` |
| `r84_pixels` + `r84_offsets` | 146 | `R_DrawSegTextureColumn` (colunas pré-calculadas R84) | build do sub **sem o define R84** (volta ao caminho normal de coluna) ou medir |
| `r12_recip_table` | 127 | idem, via `.s` | **sem `DOOM_R12_RECIP*`** no sub (variante `norecip`), usando `divu` |
| `r76_*`/`r77_*` (6 × 17 KiB) | 104 | `r59_color_tables` (cores/colormix do render) | **necessárias** para manter a imagem. Ver §3 |
| tabelas de ângulo/seno, `states`/`mobjinfo` | ~30 | engine | já fazem parte da lógica no sub |

**O WAD (1.633 KiB)** é lido pelo render via `W_*`. No sub vem do cache de lumps (DIR/LUMP já existem).

**`I_FinishUpdate`** (conversão + entrega, fica no **MD**): 7 KiB de funções. Usa `r79_map`/`r79_cost` (112 KiB) e o `r91_joint` da ROM do MD. Confirma o desenho: **o sub entrega `r22_fb`, o MD converte.**

## 3. Orçamento de memória do sub para o M2
**Hoje** (S2e): `_end` = 0x60680, com cache WAD de 128 KiB, heap de 128 KiB e streams reservados de 0x68000 a 0x7BFFF.

**M2 acrescenta:**
- ~81 KiB de funções de render;
- 64 KiB de mapa em layout SRAM;
- 104 KiB de tabelas de cor;
- ~9 KiB de BSS;
- e retira os streams (−80 KiB).

**Não cabe sem reorganizar.** Proposta, em ordem:
1. **Tabelas de cor (104 KiB) duplicadas nos dois bancos da Word RAM 1M.** Cada banco tem 128 KiB e o sub sempre enxerga um deles. Sobram ~24 KiB por banco para `r22_fb` (3,3 KiB) + pacote/HUD.
   - Carregar uma vez por banco no boot: o MD escreve as duas cópias antes do primeiro quadro.
   - O render usa ponteiros fixos `0x0C0000+off`.
2. **Streams de mundo/atores (80 KiB):** deixam de existir, porque o render no sub lê o estado real. Só ficam HUD/som.
3. **Cache WAD de 128 KiB:** medir o pico de E1M1–E1M9 com texturas. Se faltar, LRU só para patches/sprites.
4. **Loader:** a imagem passa de 128 KiB. Copiar em várias janelas trocando o banco BK da PRG-RAM (`$A12003` bits 6–7) com o sub em bus request.

## 4. M2b: próximos passos concretos
1. `build_setup.py --render`: copiar a árvore com o patch `sram-in-ram` (o mesmo de `render_probe.py`), defines da R128 **menos** `DOOM_R12_RECIP*` e R84, compilar `r_*`/`i_genesisv` (só as funções de coluna) no sub, e linkar com a lógica S2e.
2. **Sonda:** `nm`/`size` do link; confirmar 0 não resolvidos e `r91_joint` fora.
3. **Sub:** depois de cada tic (ou só antes da troca), `R_RenderPlayerView(&_g_player)` → `r22_fb`. O framebuffer vai para o banco que o sub entrega.
4. **MD:**
   - copia o framebuffer para o próprio `r22_fb`, ou aponta a conversão para a Word RAM;
   - roda só `I_FinishUpdate` + HUD;
   - pula `S2B/S2C_Apply` e o próprio render.
5. **Teste A/B na mesma cena** (spawn do E1M1, 24 quadros):
   - VBlanks/quadro MD;
   - tempo de render no sub (stopwatch);
   - framebuffer do sub × framebuffer do render MD do mesmo estado (diferenças pequenas aceitáveis);
   - FPS contra os 4,6 do nativo.

**Riscos:**
- caminho de coluna sem R84 mais lento;
- `divu` no lugar da recíproca;
- cache WAD sem despejo;
- ponteiros fixos na Word RAM para as tabelas de cor.

Os quatro são medidos no passo 5.
