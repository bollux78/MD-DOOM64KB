# Doom-MD Sega CD: o jogo roda no 68000 do Sega CD (plano, Cláudio)

**Decisão do usuário (2026-11-06):** seguir este caminho e **eliminar a compatibilidade com o Mega Drive sozinho** nesta linha. Exige Sega CD acoplado (Mode 1, boot pelo cartucho, sem disco). A R128 All continua sendo a versão para Mega Drive sem expansão.

## 1. Por que mudar
- Nas tentativas anteriores (colunas, visão, som, raios), o MD preparava dados, esperava e copiava a cada pedaço, e continuava no caminho crítico.
- **Já provado no console:**
  - boot Mode 1;
  - troca 1M em ~0,05 ms;
  - entrega do quadro ao VDP em **1,8 ms dentro do VBlank** (FrameDelivery M1+M2+M6).
- **O novo princípio:** dados residentes no sub, uma conversa por quadro, ninguém espera.

## 2. Papéis
| Mega Drive (terminal) | Sega CD sub 68000 (o jogo) |
|---|---|
| controle → palavra de comunicação | lógica completa (`P_Ticker`), render completo, menus |
| entrega do quadro: plano pronto, 2 DMAs no VBlank | escreve o quadro **já no formato do plano** no banco 1M |
| música e efeitos (Z80/FM/PSG), por comandos do sub | gera os comandos de som |
| **servidor de ROM**: copia para o sub, sob demanda, o que ele pede | pede lumps (mapa, texturas, sprites) e mantém caches |
| HUD/status bar com os tiles e paletas que já tem (R76/R77/hudw) | manda o estado do HUD (vida, munição, rosto, chaves) |

**Passo 2, depois:** a lógica volta para o MD um quadro adiantado e o sub fica só com o render. É aí que mora a chance de multiplicar o FPS.

## 3. Medidas de memória (run 42325460344, R128 All de referência)
| Item | Tamanho |
|---|---|
| Funções (todo o código, inclusive SGDK, som e HUD) | 262 KiB |
| WAD inteiro | 1.633 KiB |
| Música/som | 419 KiB (fica no MD) |
| `r91_joint` (tabela rápida da conversão para o plano, R91) | **512 KiB** |
| `r84_pixels` + `r84_offsets` | 146 KiB |
| `r12_recip_table` (recíproca de escala das paredes) | 127 KiB |
| `r79_map` + `r79_cost` | 112 KiB |
| HUD (`hudw_*`, R76/R77) | ~130 KiB (fica no MD) |

**Por mapa** (`profile_level.py`, run 42294870922):

| Mapa | Geometria | + texturas/tabelas | + todos os sprites |
|---|---|---|---|
| E1M1 | 38 KB | 153 KB | 543 KB |
| E1M2 | 81 KB | 252 KB | 642 KB |
| E1M3 | 80 KB | 235 KB | 625 KB |
| E1M4 | 64 KB | 212 KB | 602 KB |
| E1M5 | 65 KB | 184 KB | 574 KB |
| E1M6 | 105 KB | 229 KB | 619 KB |
| E1M7 | 77 KB | 195 KB | 585 KB |
| E1M8 | 29 KB | 84 KB | 474 KB |
| E1M9 | 53 KB | 110 KB | 500 KB |

## 4. Orçamento do sub
**Memória disponível:**
- **PRG-RAM, 512 KiB:** código do jogo no sub, uns 150–200 KiB sem SGDK, som e HUD (a medir no build do sub); BSS do jogo (hoje 57 KB no MD; no sub, folga para caches); geometria e texturas do mapa.
- **Word RAM 1M, 2 bancos de 128 KiB:** cada banco carrega o quadro (5,4 KB) e o pacote MD↔sub. O resto (~115 KiB) pode guardar **dados só de leitura duplicados nos dois bancos**, porque o sub sempre enxerga um deles. Isso dá ~115 KiB extras efetivos.

**Decisões:**
- **Sprites:** **cache com streaming**. O sub pede `lump id` no pacote, o MD copia da ROM para o banco dele, e na troca seguinte o lump chega. Primeiro uso = 1–2 quadros sem aquele sprite. Os de uso constante (arma, puff, sangue, monstros do mapa) entram já na carga.
- **`r12_recip_table` (127 KiB):** no sub, `divu` (~140 ciclos) ou uma tabela menor com interpolação. Medir o custo por coluna.
- **Conversão pixel→plano (`r91_joint` 512 KiB / `r79` 112 KiB):** não cabe no sub. Opções a medir:
  - (a) o sub escreve o framebuffer pixel4 (3,3 KB) e o **MD** converte com as tabelas da ROM. Custa o mesmo que a R128 já gasta hoje com isso, e só o MD tem a ROM;
  - (b) o sub usa uma versão compacta (`r79`, 112 KiB, mais lenta).

  Começar por (a), medir, e decidir.
- **`r84_pixels` (146 KiB):** identificar o uso (colunas pré-renderizadas). Se for da arma/HUD, fica no MD.

## 5. Marcos
| Marco | O que é | Prova |
|---|---|---|
| **S0** | mapa de símbolos: o que vai para o sub, o que fica no MD, o que some (SGDK, SRAM R23/R25, proxies R24). Build do engine para o sub (sem SGDK) só compilando e linkando, com o relatório de tamanho | `build: PASS`, código ≤ 200 KiB |
| **S1** | o sub roda a **lógica** da demo 1 (E1M1) sem render; o MD é só servidor de ROM | fingerprints de lógica **idênticos** à R128 (`r118_logic_check` adaptado) |
| **S2** | render no sub → framebuffer pixel4 → MD converte (opção a) → entrega | quadros iguais à R128 em 10 checkpoints; FPS da demo contra os 5,49 da R128 |
| **S3** | som e HUD pelo MD a partir do estado enviado; menus; jogável | console: `SEGA CD: ON` jogável do E1M1 ao E1M9 |
| **S4** | pipeline: lógica no MD, render no sub, 1 quadro de atraso | Run All: FPS médio/mínimo contra a R128 |
| **S5** | extras: ASIC (chão texturizado, raios), assembly nos laços críticos do sub | — |

**Testes por marco:** `build: PASS/FAIL`, `blastem: PASS/FAIL`, console depois. Nome do arquivo no header e na tela. BlastEm com a configuração fixa, ≤ 10.000 quadros por execução. ROM/WAD/ELF só em `/home/dan/Projetos/Personal/`. Troca 1M sempre por `$A12018`, nunca DMNA.

## 6. Riscos
- **Memória por mapa** (E1M2/E1M3/E1M6 são os maiores): depende do cache de sprites e da duplicação na Word RAM. Se não couber, cache de texturas também.
- **Conversão para o plano no MD (opção a):** se custar caro, o MD vira gargalo da apresentação. Medir no S2.
- **Divisões e recíprocas no sub** sem a tabela de 127 KiB.
- O sub não tem VDP nem Z80: tudo que a R128 faz direto no hardware (`I_*`) vira comando para o MD.
