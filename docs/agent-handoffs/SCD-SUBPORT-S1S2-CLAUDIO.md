# Sega CD sub-port, S1 e S2: lógica e render no 68000 do Sega CD (Cláudio para o Werk)

## Estado atual — S2c, 2026-11-08

Branch `exp-werk-scd-subport-s1s2`. S2b confirmada no console pelo usuário. S2c implementada e validada em BlastEm: câmera, setores/sides, atores dinâmicos com IDs estáveis e itens R24 reais do sub no renderer MD. 27 estados/26 frames, hashes e valores aplicados exatos, listas nativas por setor verificadas, zero ticks MD durante replay, saída instrumentada restaurada. Run `42440328871`, commit `0eae23564ccba904a7281f9e75e5ff8c6d2b19bf`. Máximo55 atores vivos,68 itens R24,122 IDs observados. Console S2c pendente.

Ver [SCD-S2C-ACTORS-BRIDGE.md](SCD-S2C-ACTORS-BRIDGE.md) para limites, wire, memória, resultados e ROM privada. Continua sendo replay em lote, sem input ao vivo e sem alegação de FPS. Próximo marco: comunicação por tic e entrada real. O estado S2b abaixo é histórico.


## Estado atual — S2b, 2026-11-08

Branch de desenvolvimento: `exp-werk-scd-subport-s1s2`. S2a aprovada em hardware pelo usuário. S2b implementada e validada em BlastEm: câmera e setores/sides reais do sub aplicados ao renderer MD, 27 estados/26 frames, sem G_Ticker/P_Ticker MD durante o replay, saída para ciclo original PASS. Run `42438888747`, commit `22cd6de114551bb4faf4ca8b2f832ce37ae88c22`. Stream de 8924 bytes; 85 setores/273 sides; alterações reais de altura, luz e sides verificadas. Console S2b ainda pendente.

Ver [SCD-S2B-WORLD-BRIDGE.md](SCD-S2B-WORLD-BRIDGE.md) para contrato, memória, resultados e ROM privada. Continua sendo replay em lote; atores congelados locais, sem input ao vivo e sem alegação de FPS. Próximo marco: atores com IDs estáveis e vínculo espacial local; depois comunicação por tic.

O plano/base histórica abaixo permanece como referência; a branch citada no primeiro parágrafo abaixo não é a branch atual de desenvolvimento.


**Branch:** `exp-chatgpt-scd-bench03b`. **Base pronta:**
- **S0:** `experiments/DOOM_SCD_SubPort/s0_report.py`. As 85 fontes da R128 All compilam para o sub sem SGDK; 191 KiB de funções.
- **S1a:** `experiments/DOOM_SCD_SubPort/s1a/`, workflow `scd-subport-s1a.yml`.
  - Engine no sub com resultado idêntico ao do MD.
  - MD servindo lumps do E1M1 pela Word RAM.
  - Tela de diagnóstico + START → jogo. Aprovado no console.
- **Plano geral:** `SCD-SUBPORT-PLAN-CLAUDIO.md`.

**Critério do usuário (2026-11-07):**
- se a demo não ficar idêntica à R128, mas o jogo funcionar normalmente para o jogador, **é aceitável**. Medir a divergência e reportar, mas ela não reprova;
- **toda ROM de teste para o console precisa ser jogável:** tela de diagnóstico e depois START → jogo.

**Relatório de cada passo:** `build: PASS/FAIL`, `blastem: PASS/FAIL`, console pelo usuário.

---

## Regras de arquitetura (valem para S1 e S2)
1. **Mesmo código-fonte, dois alvos:** a árvore R128 All gerada pelo build (como no S0 e no S1a). O sub compila com os defines da R128 **menos** os de SRAM e hardware de vídeo do MD:
   - `-UDOOM_R22_SRAM_BLOCKLINKS -UDOOM_R23_MAPMEM -UDOOM_R25_MUSIC`;
   - com isso os macros `R23_GET/R23_SET` e `R25_SRAM_*` caem nas versões de RAM direta (`r23_mapmem.h`, `r22_blocklinks.h`);
   - o mapa vive na PRG-RAM, sem janelas.
   - Manter `DOOM_R24_EPISODE` (proxies de things da ROM). Eles leem lumps, que no sub vêm do cache.
   - Conferir com o `s0_report.py` (passando os defines do sub) que nenhum símbolo de SRAM ou VDP sobra no lado do sub.
2. **Arquivos do sub:**
   - entram: `p_*`, `g_game`, `d_main` (sem `D_Display` de vídeo do MD), `r_*` (no S2), `m_*`, `tables`, `info`, `z_*`, `r24_*`;
   - ficam no MD: `i_genesis*`, `hud*`, `r76/r77/r79/r91` (conversão para o plano), som/XGM, menus de vídeo;
   - novos no sub: `scd_sub_w_wad.c`, `scd_sub_system.c`, `scd_sub_main.c`, mais o `boot.s`/libc do S1a.
3. **Protocolo**, um só arquivo compartilhado `scd_proto.h`:
   - troca 1M sempre pelo `$A12018`, **nunca DMNA**;
   - o pedido leva um ID único, o sub faz ACK em `$FF8026`, e o fim do pedido sai em `$FF8028` + dados em `$FF802A/2C`, como no S1a.
   - Comandos do sub ao MD:

     | Comando | Para quê |
     |---|---|
     | `LUMP n` | MD copia o lump n para o banco |
     | `DIR` | diretório do WAD: nome, tamanho, por lump |
     | `TIC` | entrega o quadro/estado; o MD devolve o input do tic |
     | `SFX/MUSIC id` | — |
     | `HUD estado` | — |
     | `ERROR texto` | — |

   - Como o sub não pode iniciar uma troca (quem pede é o MD), **o MD fica num laço de servidor**: a cada VBlank lê `$A12020..2E`. Se o sub publicou um pedido (`$FF802E` = seq), o MD atende e responde pela troca normal.
4. **Memória do sub:** PRG-RAM de 512 KiB.

   | Item | Tamanho |
   |---|---|
   | código | ~150–190 KiB |
   | BSS do engine | ~55 KiB, sem as restrições do MD |
   | heap/zone | 128 KiB+ |
   | **cache de lumps** | o resto, ~150 KiB |

   No primeiro passo, sem despejo dentro da fase (o engine guarda ponteiros), limpo a cada mapa. Se encher: `ERROR "LUMP CACHE FULL n"`, para medir.

## S1: lógica no sub (sem render)
**Objetivo:** a demo 1 (E1M1) roda no sub com `norender`, e o MD só serve lumps e input da demo.

**`scd_sub_w_wad.c`** substitui o `w_wad.c` no sub:
```c
/* no boot: CMD_DIR -> o MD manda numlumps e, em blocos, {filepos,size,name[8]} (~16 B/lump). */
int16_t W_GetNumForName(const char *name);           /* busca no diretório local, igual ao w_wad.c */
uint16_t W_LumpLength(int16_t n);                    /* do diretório */
const char __far *W_GetNameForNum(int16_t n);
const void __far *W_GetLumpByNum(int16_t n)          /* cache: se faltar, CMD_LUMP n (síncrono) */
{
    if (!slot[n]) slot[n] = scd_fetch_lump(n);       /* copia do banco para o cache, devolve o ponteiro */
    return slot[n];
}
void W_FlushCache(void);                             /* na troca de mapa */
```
- `slot[]`: um ponteiro de 4 B por lump, ~8 KB, na BSS do sub.
- Lumps maiores que um banco não existem: `uint16` de tamanho.

**`scd_sub_system.c`:**
- `I_Error` → `CMD_ERROR`, com o texto no banco, e para;
- `MEM_alloc`/`MEM_getFree` → heap simples;
- relógio/`I_GetTime` → contagem de tics enviada pelo MD em cada `CMD_TIC`;
- `JOY_*` → input do pacote;
- som/vídeo → vazios no S1.

**`scd_sub_main.c`:**
- boot da biblioteca, `W_Init` (via `CMD_DIR`), `Z_Init`, a sequência de init do `D_DoomMain` sem vídeo;
- `G_DeferedPlayDemo("DEMO1")` com o caminho `norender` dos builds PERF/demotest (o mesmo que o `r117_profile.py --norender 1` usa);
- a cada 100 gametics, publica a impressão digital de lógica do `r118_logic_check.py`: jogador x, y, z, ângulo, vida, número de mobjs, `prndindex`. Vai num bloco de resultado no banco.

**MD (S1):**
- a R128 inteira, com o servidor instalado antes do `D_DoomMain`, como o `S1A_Test`;
- serve `DIR`, `LUMP` e `TIC` até a demo acabar;
- mostra na tela de diagnóstico: tics executados, VBlanks, lumps servidos, bytes, tamanho máximo do cache, a primeira divergência (se houver) e o FPS de lógica pura do sub;
- **START → jogo R128 normal no MD**, para ser jogável.

**Testes S1** (BlastEm):

| Teste | Critério |
|---|---|
| a demo chega ao fim sem `ERROR` | obrigatório |
| fingerprints a cada 100 tics × R128 nativo (`r118_logic_check` na mesma demo) | **reportar** o primeiro tic diferente. Diferença não reprova (critério do usuário), mas tem de ser explicada |
| tempo de lógica no sub: VBlanks para 2.600 tics | comparar com o `norender` da R128 no MD (tempo de lógica pura) |
| cache | pico de uso, lumps pedidos |
| a ROM continua jogável depois do START | G_Ticker alcançado, como no teste do S1a |

## S2: render no sub, entrega pelo MD
**Objetivo:** o jogo inteiro roda no sub, e o MD só apresenta. **Ainda serial nesta etapa:** o sub faz lógica + render, o MD apresenta. O paralelismo é o S4.

**Sub:**
- compila os `r_*` com os defines de render da R128 (pixel4, R60 asm etc.);
- o framebuffer pixel4 (`r115_draw`, 3.344 B) fica **no banco 1M** do sub, que já é dele;
- **no fim do quadro, `CMD_TIC`:** a troca entrega o banco com o framebuffer ao MD e devolve o input do próximo tic.

**MD:**
- recebe o framebuffer no banco;
- roda **a mesma conversão para o plano da R128**: R79/R91, `I_FinishUpdate`/R115, apontando para o framebuffer na Word RAM `0x600000+off` em vez da RAM;
- mantém o HUD a partir do bloco de estado: vida, munição, rosto, chaves, mensagens;
- toca som e música pelos comandos;
- lê o controle e manda no pacote.
- **RAM do MD:** sem o engine de jogo, sobra muita BSS. O BSS do MD despenca, e a restrição de 57.920 deixa de apertar.

**Primeira ROM S2 jogável** (exige o Sega CD; sem ele, mostra "SEGA CD REQUIRED"):
- tela de diagnóstico: boot, diretório, cache;
- START → jogo rodando no sub.
- **Medir no BlastEm:**
  - bench do E1M1, o mesmo do console: FPS médio/mínimo e tempo contra os 6,27 / 2,6 / 414,47 s da R128;
  - quadros iguais à R128 em checkpoints;
  - 0 timeouts;
  - pico do cache.

**Expectativa honesta:**
- só pelo clock (1,65×) e sem as janelas de SRAM, o S2 deve ficar perto de ou acima do nativo;
- os ganhos grandes vêm no S4 (lógica no MD, em paralelo) e nas otimizações do sub (texturas residentes, asm, ASIC).
- Se o S2 for muito pior que 1,65× × nativo, medir com PC sampling no sub: cache, recíprocas sem a tabela de 127 KiB (`DOOM_R12_RECIP_LUT` fora do sub, usar divu) ou a conversão no MD.

## Tabelas grandes no S2
| Tabela | O que fazer |
|---|---|
| `r12_recip_table` (127 KiB) | `-UDOOM_R12_RECIP_LUT` no sub (volta ao `divu` da R10/R9, já existente) |
| `r91_joint`/`r79_*` | ficam no MD (conversão para o plano) |
| `r84_pixels` (136 KiB) | identificar o uso no S2. Se for render no sub, ver se cabe ou se tem modo sem a tabela |

## Ordem
1. S1 com o servidor, lógica e fingerprints. Primeiro o BlastEm, depois a ROM jogável para o console.
2. S2 com a ROM "SEGA CD REQUIRED" + bench do E1M1.
3. Depois disso, o Cláudio revisa os números e passa o S4 (paralelismo).
