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
