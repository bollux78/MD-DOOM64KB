# Heretic-Manifold H01 — investigação do IWAD shareware

Objetivo: portar primeiro a **geometria e texturas de E1M1** de Heretic para o renderer Manifold, antes de avaliar monstros, armas e o jogo completo.

## IWAD verificado

- Nome recebido: `HERETIC1.WAD.txt` (o sufixo `.txt` não altera o formato binário)
- Formato: `IWAD`
- Tamanho: `5120300` bytes
- SHA-256: `b33a9d23fccd273485c4769f499e47dd009ce265f9c90d856600a2000bde3fe0`
- Lumps: 1357
- Mapas: E1M1–E1M9, cada um com um THING de player 1.

| Mapa | LINEDEFS | SEGS | SSECTORS | THINGS |
|---|---:|---:|---:|---:|
| E1M1 | 777 | 1118 | 370 | 242 |
| E1M2 | 1128 | 1660 | 506 | 458 |
| E1M3 | 810 | 1255 | 382 | 402 |
| E1M4 | 1875 | 2736 | 928 | 358 |
| E1M5 | 2298 | 3334 | 1044 | 420 |
| E1M6 | 1400 | 2239 | 767 | 503 |
| E1M7 | 1694 | 2633 | 923 | 511 |
| E1M8 | 355 | 555 | 204 | 349 |
| E1M9 | 921 | 1433 | 502 | 531 |

## Método H01

1. Conservar WAD e assets somente no armazenamento privado do runner, fora do Git.
2. Usar uma **cópia isolada** do conversor de DOOM/Manifold; não alterar as branches de DOOM e R128.
3. Tratar Heretic como jogo distinto: adaptar PLAYPAL, TEXTURE1/PNAMES, flats, sky, sprites e tipos de THINGS sem assumir os IDs de DOOM.
4. Primeiro gerar uma ROM de **passeio E1M1**, com paredes/pisos/tetos/texturas/câmera. Se preciso, ignorar THINGS, portas e mecânicas na primeira prova.
5. Medir número real de células/paredes após conversão e documentar qualquer corte; não aprovar se houver geometria faltante.
6. Construir no runner e validar no emulador, depois no console real.

**Fallback:** se a conversão/renderer Manifold se mostrar estruturalmente inviável, experimentar importação dos mesmos mapas e recursos no R128, em branch própria. Não manter duas portas simultâneas sem evidência de necessidade.

## Situação

- [x] Arquivo IWAD validado e diretório de lumps extraído localmente para análise.
- [x] Estrutura dos nove mapas enumerada.
- [ ] Conversão de BSP/células Manifold executada com esse IWAD.
- [ ] Texturização Heretic adaptada.
- [ ] ROM H01 compilada.
- [ ] Testes gráficos/console.

**Não afirmar ainda que H01 roda em Manifold.** A inspeção do formato é somente a primeira etapa.

## Decisão de implementação (13/11/2026)

**Manifold primeiro.** O conversor `m01/convert_wad.py` aceita diretamente WADs little-endian Doom/Heretic, e `emit_portal_map.py` reconstrói BSP para células. Já a R128 usa WAD ROM com setores/sidedefs/seg/texture IDs em formato proprietário big-endian, tornando a simples substituição do IWAD insegura.

Preflight local do arquivo do usuário (Heretic shareware v1.0, SHA fixado acima):
- E1M1: 370 SSECTORS, 1118 SEGS, 777 LINEDEFS, 688 VERTEXES, 154 SECTORS.
- Nenhuma SEG de E1M1 referencia sidedef frontal inválido.
- 251 de 370 subsectors não são anéis fechados independentes: isso requer reconstrução de regiões BSP; não é necessariamente erro.
- TEXTURE1: 58 texturas; PLAYPAL e PNAMES presentes; 12 nomes de flats usados no E1M1.
- Há 242 THINGS e 45 tipos: a versão H01 dispensa objetos e lógica.
- Não aplicar semântica de specials, sprites, HUD ou armas de DOOM ao Heretic.

O workflow `.github/workflows/heretic-h01-manifold.yml` realiza:
1. Obtenção privada do IWAD original via arquivo local ou fonte pública com SHA-256 validado; nunca faz commit do WAD.
2. Auditoria de topologia e geração de candidato portal_map.
3. Preparação da árvore Manifold isolada, **sem texturas/objetos/portas/HUD de DOOM**, para verificar apenas geometria.
4. Compilação de ROM H01 na máquina de runner, se as etapas anteriores forem aprovadas.
5. ROM de diagnóstico, se gerada: `/home/dan/Projetos/manifold-doom/roms/H01/heretic-manifold-h01-geometry.bin`.

**Critério de fallback:** a R128 será considerada se a reconstrução geométrica do Manifold apresentar problema estrutural sem correção simples. Esta rotina não declara que Heretic já executa ou está jogável.
