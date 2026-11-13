# Manifold M14: ROM única com menu de 5 fases (SSF2, 10,5 MB) — handoff para caber em 4 MB

Autor: Claude. Destino: Werk. Data: 12/11. Branch `exp-manifold-m14-e1m1`.

## O que existe (testado)
`claudio-manifold-doom-MENU-5-FASES-ALTURA80.bin`, 11.010.048 bytes: abertura do Doom (imagem do usuário, 2 paletas de 16 cores) → menu → E1M1, E1M2, E1M4, E1M5, E1M9 (walk, objetos ≤126, monstros parados, altura de objetos ×0,80). Verificado pelo usuário: **BlastEm (teste de bancos OK nos 4 slots), Mega Everdrive (clone chinês) joga direito**. Reset volta ao menu; não há retorno ao menu em jogo. No menu, A = teste de bancos da fase selecionada.

## Como funciona
- Mapper SSF2: slot 0 (0x000000, banco 0) fixo; slots 1–7 em 0x080000.. de 512 KB, trocados por escrita de byte em 0xA130F3/F5/F7/F9/FB/FD/FF. Cabeçalho em 0x100 começa com `SEGA SSF` (BlastEm e Everdrive habilitam o mapper por isso).
- Banco 0 = menu bare-metal (sem SGDK, sem interrupções, polling do vblank, sem libgcc), dono da tabela de vetores do 68000. Cada vetor aponta para um stub `move.l (0x80000+4*i),-(%sp); rts`, que repassa a interrupção à tabela de vetores da fase ativa (início da imagem dela em 0x80000).
- Cada fase é uma imagem SGDK completa **linkada em 0x080000** (`md_80000.ld`; `_stext = ADDR(.text)+SIZEOF(.text)` para a cópia de .data), ocupando 4 bancos (2 MB, com preenchimento). Fase i fica nos bancos 1+4i … 4+4i.
- Lançamento (`menu.c: launch`): tela preta, zera a VRAM e a CRAM, escreve os 4 registradores de banco, zera 0xA10009/0B/0D (o startup do SGDK só faz o cold start completo se os registradores de controle estiverem zerados), SR=0x2700, SP=0 e `jmp 0x80200` (`_Entry_Point` da fase).
- Código em `experiments/DOOM_Manifold_E1M1/tools/m14/multimap/`: `build_map_image.sh FASE` (gera `/tmp/m12/mm_FASE/out/release/rom.bin`; altura ×0,80 via `HPCT`, padrão 80), `compose.py` (compila o menu, monta a ROM e a tabela de auto-teste de bancos), `gen_assets.py` (abertura + fonte), `mk-ssf.gen`, `md_80000.ld`, `menu.c`, `crt0.s`.
- Receitas por fase: E1M1 com portas (`MANIFOLD_DOORS=1`); as outras `DOORS=0`; E1M4 `SKY_MERGE=0 MAX_CELL_WALLS=24`; E1M5 `MAX_CELL_WALLS=24`. Comum: `flags_walk.txt` + `VDP_SAFE=2 SWEPT=1 GRATES=0 FALL=1 FALL_FAST=1 WEAPON_FIX=1 INPUT_FIX=1 UNPACK_MAP=1 VG_MICRO=1 SPLIT_LINES=0`.

## Onde está o tamanho (medido: seções .text/.data/.rodata dos .o de cada fase, comparando md5 entre as cinco)
Dados **idênticos nas cinco fases: ~2,59 MB** (repetidos 5× hoje). Específicos de cada fase: E1M1 0,43 MB, E1M2 0,71, E1M4 0,64, E1M5 0,55, E1M9 0,36 (soma 2,69 MB). Código/resto: pequeno.

Maiores itens idênticos entre fases:
| objeto | bytes |
|---|---|
| `src/map_table.o` | 1.048.604 |
| `src/tex_draw_tables.o` | 542.724 |
| `src/obj_sprite.o` | 398.112 |
| `src/div_lut.o` | 286.720 |
| `src/tex_table_lookup.o` | 137.485 |
| `res/music_res.o` | 74.752 |
| `res/sfx_res.o` | 35.840 |
| `src/doom_statusbar.o` | 26.784 |

Específicos por fase: `m12_doom_objects.o` (até 685 KB em arquivo), `textures.o` (até ~520 KB), `e1m1_map.o`.

## Ideias para 4 MB (ordem de ganho esperado)
1. **Deduplicar o conteúdo comum.** Um único exemplar dos ~2,59 MB (linkado uma vez) + só os dados de cada fase (~2,7 MB no total) dá ~5,3 MB; falta tirar ~1,3 MB com os itens 2–4. Estrutura possível: bancos fixos 0..N com o comum (slots 0–2 fixos, 1,5 MB, ou deixar o comum nos slots 1–3 e trocar só os slots 4–7 por fase). Cada fase teria de ser linkada contra os símbolos do bloco comum (ELF/`--just-symbols` ou um arquivo de símbolos gerado a partir do link do comum) — é a parte de trabalho.
2. **Verificar `map_table` (1 MB, idêntico em todas as fases).** Se for tabela gerável ou esparsa (zeros), cabe compactar ou gerar em runtime/na RAM; é o maior alvo isolado.
3. `obj_sprite` (398 KB): conter só os sprites usados pela fase (imp/zombieman/sargeant e pickups nas fases walk), em vez do conjunto todo.
4. `tex_draw_tables` (543 KB) e `div_lut` (287 KB): checar densidade/entradas não usadas, ou compactar a parte fria.
5. Música/efeitos (~110 KB): já pequenos; compactar não muda nenhum banco.
6. Texturas por fase (até ~520 KB): reduzir a bpp ou o número de texturas realmente vistas na rota do passeio.
Restrições: RAM de 64 KB está quase toda no heap (heap_high ≈ 0xFFE1B2; ~1,5 KB livres de pilha além da margem de 3072 do guard do `visit_graph`), então descompressão em runtime precisa de buffer pequeno. Flashcart do usuário (clone Everdrive) aceita SSF2 até 15 MB; BlastEm também. Meta 4 MB = ROM comum a flashcarts sem mapper.

## Pendências relacionadas
- No spawn da E1M2 o fundo do corredor (portais/sala aberta distante) aparece com ruído e faixa azul: é anterior a esta ROM (também nas ROMs de passeio antigas); relacionado aos "buracos residuais em células externas" do M13.2.
- Opção nova `MANIFOLD_STACK_MARGIN` (padrão 3072) no guard de pilha do `visit_graph`; medido no E1M2: uso real de pilha além do guard ≈ 320 bytes, folga de ~1,5 KB com margem 1536 (sem mudança visual).
- Abertos (do Werk): corrupção com botão C no BlastEm/console, ruído no primeiro tiro, animação de tiro invisível.

## Atualização: versão com dados unificados (7 MB), 12/11 noite
`claudio-manifold-doom-MENU-5-FASES-UNIFICADA-7MB.bin`: 7.340.032 bytes (antes 11.010.048). Testada no MAME (menu, teste de bancos, as cinco fases rodando via ROMs planas); troca real de banco ainda não testada no BlastEm/Everdrive nesta versão.

Layout (endereço = offset no arquivo): `0x000000` menu (slot 0 fixo); `0x010000`–`0x2FB000` **bloco comum, um só exemplar** (3,06 MB, idêntico nas cinco fases; slots 0–5, bancos 1–5 identidade); `0x300000`+ **bloco de cada fase** (slots 6–7), alinhado a 512 KB: E1M1 banco 6 (1 banco), E1M2 7–8, E1M4 9–10, E1M5 11–12, E1M9 13. O menu seleciona slots 1–5 = bancos 1–5 e slots 6/7 = banco da fase / banco+1; vetores do menu redirecionam por `0x300000+4*i`; entrada da fase `0x300200`.

Como o bloco comum ficou idêntico (verificado por `compose.py`, que aborta se diferir): `md_split.ld` + `mk-split.gen` (sem `--gc-sections`, para o conteúdo não depender do mapa).
- `.common` (0x10000): os 45 objetos cujo md5 é igual nas cinco fases + `libmd.a` + `libgcc.a`.
- `.mapobjs` (0x301800): os 8 objetos que mudam por fase (`colors level sector_group manifold_sky portal m12_doom_objects e1m1_map textures`) em **endereços fixos** (slots com folga). Os 7 símbolos desses objetos que o bloco comum referencia e cujo endereço variava (`check_trigger_switch clean_portal_map load_portal_map run_sector_group_processes activate_sector_group_enter_trigger portal_rend e1_block_offsets`) ficam fixados no início (seções `-ffunction-sections`).
- `.maphead` (0x300000, 0xE00): vetores/cabeçalho/entrada da fase, ctors, etc. Imagem do `.data` em `0x300E00` (fixa); `_stext=_etext=0x300E00`, `_sdata=0x6A0` fixo (copia até 8 bytes a mais, inofensivo).
- RAM: `.data` começa em 0xE0FF0000 e `.bss` em +0x6C0 (fixo), `_bend` = início do bss + 0x1D00 (fixo; custa ≤ ~0x1C bytes de heap). Dados de RAM dos 8 objetos vão por último. `SUBALIGN(2)` em `.data/.bss` (sem isso `sprite_draw_cache` caiu em endereço ímpar e `init_sprite_draw_cache` dava Address Error: defeito latente que o layout antigo escondia).
- Limites que o link verifica/ou devem ser reavaliados se o conteúdo crescer: bloco comum < 0x2F0000; `.data` ≤ 0x6C0; `.bss` ≤ 0x1D00; textures ≤ ~0x72E00; e1m1_map ≤ 0x17000; m12_doom_objects ≤ 0x23000; bloco da fase ≤ 1 MB (2 bancos).

Próximos ganhos (para os 4 MB): bloco comum 3,06 MB (era 2,59 MB de dados + código/libs sem gc-sections: voltar a podar seções não usadas sem quebrar a igualdade, p.ex. `--gc-sections` com `KEEP` do conjunto de todas as fases); `map_table` 1 MB e `tex_draw_tables` 0,54 MB (idênticos, candidatos a compressão); sprites só dos objetos usados por fase; e reduzir o bloco da fase (textures até 0,47 MB). Com 4 MB faltam ~3 MB: 3,06 (comum) + 5×~0,6 (fases) = ~6 MB de dados reais sem compressão.
