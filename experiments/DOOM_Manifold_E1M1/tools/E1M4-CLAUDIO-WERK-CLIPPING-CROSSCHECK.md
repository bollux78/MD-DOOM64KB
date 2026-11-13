# E1M4 pátio — cruzamento Cláudio × Werk (2026-11-13)

## Status
- Nenhuma causa definitiva comprovada. Não aplicar mudanças à M14 nem à branch de trabalho do Cláudio.
- Evidência Cláudio: `exp-manifold-e1m4-claude-nearclip-evidence/docs/agent-handoffs/e1m4-patio/README.md`.
- Experimento Werk: `exp-manifold-e1m4-portal-diagnostic`, build [43509107677](https://github.com/bollux78/MD-DOOM64KB/actions/runs/43509107677), cinco ROMs control/trace/revisit12/depth48/both compiladas.
- Na cena fixa do pátio (cel 161), Cláudio mediu profundidade máxima **8** e **zero** cortes por profundidade/pilha. Isso enfraquece substancialmente essas duas hipóteses *nesse local*; ciclo (setor em render) e orçamento de revisitas continuam não medidos.

## Descoberta matemática reproduzível

Em `MANIFOLD_NEAR_SAFE=1`, a função `m11_safe_near_clipping` em `stage_rom.py` **já corrige** `clip_map_vertex_16` para interpolar X em s32 no plano próximo. `NEAR_Z_FIX = 10 << TRANS_Z_FRAC_BITS`, `TRANS_Z_FRAC_BITS = 4`. O indicador `clip=8` do Cláudio significa `RIGHT_Z_CLIPPED`: não significa "sem recorte".

Amostra ruim publicada: `v1=(-192, 326u)`, `v2=(326, -191u)`, projeção `13..431`.

Interseção da reta `v(t) = v1 + t*(v2-v1)` com plano próximo `z=10`:
- `t_near = (326-10)/(326-(-191)) = 316/517 ≈ 0.6112186`
- `x_near = -192 + 518*t_near ≈ 124.6112`
- A projeção horizontal de 64 colunas é `x_screen = 32 + 32*x/z`:
  - primeiro endpoint: `32 + 32*(-192)/326 ≈ 13.153`
  - endpoint recortado: `32 + 32*124.6112/10 ≈ 430.756`

**Os valores reproduzem precisamente 13..431.** Logo, o grande X projetado não prova que a interpolação de near plane falhou: ele é sua consequência geométrica consistente.

A interseção com o **plano lateral direito** `x=z` ocorre em:
- `t_right = (326+192)/(518+517) = 518/1035 ≈ 0.500483`
- `x=z≈67.250`; projeção `x_screen≈64` (borda direita da tela).

Portanto, para esta parede, o segmento dentro do frustum deve projetar aproximadamente **colunas 13..64**, e não 13..431. O código legado do `clip_map_vertex_16` possui dois ramos de clipping lateral prefixados por **`if(0)`**: ambos desativados. Não basta recortar z ao plano próximo.

## Teste controlado solicitado ao Cláudio

O teste prioritário é **habilitar/implementar recorte lateral 3D correto**, isolado da M14, não apenas "adicionar near clipping" que já está presente. Ordem:
1. Manter referência de mesmos câmera, ângulos, mapa, texturas, flags M14 e FPS (0/128/256/384 etc). Controle sem correção.
2. Na função `clip_map_vertex_16`, preservar o recorte próximo existente (x interpolado em s32), e recortar também o segmento aos semiplanos laterais `-z <= x <= z` **com geometria real no espaço da câmera**, usando aritmética larga e coordenadas UV/tmap coerentes. Alternativamente usar clipping paramétrico em um único passo; evitar ligar ramos legados `if(0)` sem auditoria, pois contêm DIVS e lógica ad hoc.
3. Verificar antes do raster que a parede problemática entra aproximadamente por `x1≈13`, sai por `x2≈64`, e que X/Z não excede o intervalo de tela depois do clipping. Confirmar por log, sem depender só da imagem.
4. Comparar visual do pátio e FPS com baseline. Não aumentar limites de recursão nesta variante; para cruzar com Werk, usar `trace.bin` e `revisit12.bin` separadamente.
5. Adicionar contadores por *ciclo de setor ativo*, *limite de 5 revisitas*, *depth*, *stack* para verificar que janelas descartadas coincidem ou não com a região ausente; a máscara `trace.bin` marca janelas rejeitadas e áreas yclip ainda abertas, mas não é por si prova de causa.

## Interpretação
- Se o clipping lateral eliminar a diagonal mantendo os mesmos limites e FPS, teremos forte evidência a favor de span fora do frustum/rasterização.
- Se não eliminar, auditar clipping yclip/oclusão, backface e a correção da interpolação vertical do raster. A parede ser "enviada" para uma função não comprova que todas as colunas foram de fato preenchidas.
- Profundidade máxima 8 e zero corte de stack/depth em E1M4 não eliminam bugs de profundidade em outros mapas.

**Nada aqui é uma aprovação da correção para integrar na M14.**
