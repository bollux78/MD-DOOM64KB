# M11 — próximo plano de bugs: paredes próximas, HUD e distância

Data 2026-11-10. Branch experimental `exp-manifold-m11-nearclip-hud`, derivada da M11 musical `db00dcd6`. **A música XGM já toca corretamente no teste gráfico do usuário e não perturba o gameplay.** Sem mudanças na release nem na branch principal.

## Relatos do teste gráfico
1. Paredes próximas piscam intensamente, possivelmente câmera atravessando geometria.
2. Paredes distantes piscam intermitentemente em vistas longas e/ou cenas complexas.
3. Retângulos/tiles pretos aparecem por cima do HUD do DOOM, em posições diferentes entre ROMs.
4. Controle original Manifold `doom-md-manifold-control-m02.bin` **não pisca**, controle `doom-md-manifold-controlnh-m02.bin` **pisca**. São mapas upstream e não E1M1; a comparação visual sugere que retirar `VDP_setEnable(0)` do HBlank é pior, mas não isola o mesmo cenário.
5. H32, na experiência gráfica do usuário, não trouxe ganho significativo de desempenho.

## Diagnóstico de código confirmado
No `src/portal.c` original, `clip_map_vertex_16` é chamado e imediatamente a seguir se consulta `z_recip_table_16[trans_v.y >> TRANS_Z_FRAC_BITS]` **antes de testar `NEAR_Z_CULLED` ou `FRUSTUM_CULLED`**. Isso pode indexar a tabela com profundidade negativa ao se aproximar ou atravessar planos de parede. Existe outro acesso semelhante numa rotina secundária.

No `src/math3d.c`, quando um segmento cruza o plano próximo (`NEAR_Z_FIX=10*16`) a diferença entre abscissas era feita em `s16`, podendo transbordar para paredes compridas da E1M1. O código original ainda escreve `rz1_12_4=NEAR_Z_FIX` no ramo que deveria modificar `rz2_12_4`.

**Correção candidata `MANIFOLD_NEAR_SAFE=1`:** proteger os índices da LUT antes da leitura, interpolar o cruzamento usando `s32`, saturar o x final, ajustar o z do lado direito. Isso pode reduzir os piscares próximos sem alterar colisão ou mapa. Build deve rejeitar caso os dois lados não tenham sido efetivamente substituídos.

## Variantes de mesma base H32+HUD DOOM+E1M1 XGM
- `m11music-h32.bin`: controle musical sem correções visuais.
- `m11nearsafe-h32.bin`: música + proteção LUT + recorte próximo corrigido; **variante candidata**.
- `m11hudrepair-h32.bin`: música + redesenho do tilemap HUD BG_B a cada atualização, **somente diagnóstico de corrupção de tilemap**, pode diminuir FPS.
- `m11noweapon-h32.bin`: música + sprites de arma deslocados para fora da tela; **somente diagnóstico de sobreposição dos sprites**.
- `m11nh-h32.bin`: música + E1M1 com desligamento de vídeo durante HBlank removido; **controle A/B HBlank na mesma fase**, não promover sem validação.
- `m11nearaw-h32.bin`: música + near safe + autowalk; não é jogável manualmente, vetores de exceção fatais.

## Critérios de validação
- Compilar todas as variantes sem mudar o HUD H32, a R128 e a linha Sega CD.
- BlastEm: 3600 quadros autowalk **com near safe efetivamente ativado**; rejeitar `ADDRESS ERROR`, `ZERO DIVIDE`, bloqueios e corrupção de memória.
- MAME: executar variantes, conferir HUD e visibilidade; FPS em cenas idênticas antes de alegar melhoria.
- Teste gráfico pelo usuário em proximidade da mesma parede, vistas de grande distância e HUD antes/depois de ação da arma.
- Interpretar diagnóstico:
  * Se `m11hudrepair` eliminar pretos, revisar tilemap BG_B e quem o sobrescreve, sem manter redesenho caro.
  * Se `m11noweapon` eliminar pretos, revisar atributos e link chain dos sprites de arma e sobreposição SAT.
  * Se nenhum eliminar, inspecionar fundo/plano A, tiles/paletas, DMA e VRAM.
  * Se `m11nearsafe` eliminar flicker próximo, promover apenas após comparação de FPS e geometria com controle.
  * Se `m11nh` piorar flicker na E1M1, manter estratégia original de HBlank.

## Pendências
O grande bloco/triângulo cinza do exterior já persiste com neblina desativada nas câmeras fixas M11 anteriores. A nova correção de near plane não prova resolver esse problema ou piscadas à distância: recursão de portais, overflow de profundidade, recorte vertical e sobreposição de janelas seguem sujeitos a investigação e eventual LOD.

## Resultado da compilação e testes (2026-11-10)

**Action [#42907326397](https://github.com/bollux78/MD-DOOM64KB/actions/runs/42907326397): SUCCESS**. Commit efetivamente compilado: `90d531681065ad02194112a2cb93c46502d3b66d`. A documentação foi atualizada em commit posterior, sem alterar a ROM. Diretório local: `/home/dan/Projetos/Personal/manifold-e1m1/run-42907326397-1/`.

- `m11music-h32.bin` SHA256 `bd0fcdd8a61abfc45130e0ae6d84ab91f26b17661156421c356fe8df2762098c` (controle musical, mesmo hash da versão aprovada antes pelo usuário).
- `m11nearsafe-h32.bin` SHA256 `bc57668595f12ff01a66b75cce3058fe6e3e40fd623bb9c5ebde4b934ff8c352`.
- `m11hudrepair-h32.bin` SHA256 `9f23b77fc95703f5219462760d59399878281e90a15796275ecc9da5ee3b1633`.
- `m11noweapon-h32.bin` SHA256 `09fc5c0aa7e863c36e91cb8f60aede3103f36ef9336a4f92a385d862bfd14080`.
- `m11nh-h32.bin` SHA256 `cc10b5c255547a7945f093feab7633c844cf7fad6792eebea7e48d588fcd11d9`.

As cinco têm 1.966.080 bytes, header SEGA, música XGM. `M11_MUSIC_AUTOWALK=PASS_3600_FRAMES` e **`M11_NEARCLIP_AUTOWALK=PASS_3600`** foram emitidos pelo workflow. MAME capturou f60–f890 das variantes e não houve falha no job. 

**Exame visual das capturas MAME:** a geometria inicial das cinco variantes permaneceu reconhecível e semelhante. Isso **não é prova de que o flicker próximo foi eliminado**, pois o MAME headless nessas cenas não reproduz necessariamente o ângulo/dinâmica da parede do usuário. As variantes de HUD sem sprites e com recomposição ainda carecem de teste gráfico perto dos retângulos pretos observados pelo usuário. As paredes distantes e o plano cinza exterior **não foram corrigidos comprovadamente nesta rodada**.

**Importante:** a variante `m11nearsafe` utiliza aproximação de `x` na interseção da near-plane com `s32` + saturação; portanto, testar se altera espessura e continuidade das paredes, especialmente ao girar encostado na geometria. A 3600 frames do BlastEm testa estabilidade, não fidelidade. Não promover à release principal sem testes gráficos específicos. Os diagnósticos `hudrepair`, `noweapon` e `nh` não devem ser integrados ao renderer principal.

