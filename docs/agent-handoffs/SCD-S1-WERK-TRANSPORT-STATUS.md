# S1 transport, Werk — estado em 2026-11-07

## Base imutável

Branch de desenvolvimento separada: `exp-werk-scd-subport-s1s2`, criada em cima de `77564c0`. A S1a original aprovada (ROM de diagnóstico com START → R128 All no MD) não foi modificada. O checkout principal em `/home/dan/Projetos/doom-md` não deve ser alterado nem limpo.

## Código entregue

- `experiments/DOOM_SCD_SubPort/scd_proto.h`: enum de comandos, layout dos pacotes e offsets em Word RAM 1M, testados pelo compilador.
- `experiments/DOOM_SCD_SubPort/scd_sub_w_wad.c`: diretório remoto do WAD, busca por nomes, cache de 128 KiB com ponteiros residentes, transferência síncrona via `scd_fetch_*`.
- `experiments/DOOM_SCD_SubPort/scd_md_server.c`: MD responde a `DIR` e `LUMP` da WAD original. É sempre o MD que pede troca de banco escrevendo no $A12018.
- `experiments/DOOM_SCD_SubPort/scd_sub_transport.c`: sub-CPU solicita DIR/LUMP, reconhece troca e copia os dados Word RAM para cache local.
- `.github/workflows/scd-subport-s1-groundwork.yml`: compilação cruzada dos quatro componentes e link relocável cache+transport, com checagem de símbolos.

## Resultados comprovados

- Build de módulos MD/sub 68000: **PASS** (run 42372424285).
- Link relocável cache+transporte do sub, sem símbolos `scd_fetch_*` pendentes: **PASS** (run 42372497224).
- Execução real e integração do engine no sub: **NÃO TESTADAS**.
- Uma ROM S1 nova e jogável: **NÃO GERADA**. Não transformar resultados de compilação em alegação de gameplay.

## Integração pendente — próxima tarefa

1. Inserir `SCD_MdLumpCount` na cópia descartável de `w_wad.c`, devolvendo numlumps do header endian-nativo. Não editar o checkout principal.
2. Adaptar o boot S1a para carregar uma imagem do sub com as funções do engine real, fornecendo `scd_sub_system.c`, `scd_sub_main.c` e callbacks do WAD/cache. Integrar o loop do servidor MD, consumindo pedidos enquanto o engine do sub roda.
3. Testar end-to-end `DIR` e `LUMP`, depois inicialização real do WAD, `Z_Init`, `P_SetupLevel`, `G_Ticker` e demo E1M1 com `norender` no sub.
4. A ROM S1 para console **deve** exibir diagnóstico e, com START, iniciar jogo R128 no MD caso o S1 não assuma o jogo; preservar a rota de resgate.
5. BlastEm: medir tempo de 2600 tics no sub, cache peak, pedidos e primeiro fingerprint divergente da R128. Reportar `build: PASS/FAIL` e `blastem: PASS/FAIL` separadamente.
6. Só depois iniciar S2, mantendo o framebuffer pixel4 de 3344 B na Word RAM e a conversão do VDP no MD.

## Precauções

Os módulos são ainda componentes desacoplados, não uma aplicação completa. O protocolo MD→sub foi compilado mas não validado com o emulador; possíveis diferenças de timing/memctrl devem ser confrontadas com a S1a aprovada. Não publicar WAD, ROM privada, ELF ou outras mídias protegidas no repositório público.
