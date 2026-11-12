# Manifold E1M1 — reprodução dos objetos 3D billboards (barril M12) para o Cláudio
Data: 12/11/2026 | Branch de entrega: `exp-manifold-m12-claudio`
**Tipo:** handoff técnico; sem implementação, merge, workflow ou release.

## 1. Origem FUNCIONAL: não reinventar o barril

A implementação antiga está **preservada na branch** `exp-manifold-m12-objects-pickups-approved`, NÃO presumir que foi integrada à branch compartilhada atual. O barril mostrado antes foi gerado do sprite do DOOM `BAR1A0` (THING tipo **2035**); há ainda lâmpada `COLUA0` (2028), stimpack `STIMA0` (2011), medikit `MEDIA0` (2012), munição `CLIPA0` (2007), shotgun `SHOTA0` (2001), bônus `BON1A0` (2014), `BON2A0` (2015). Os tipos e arquivos reais podem ser lidos em:

- [m12_objects.py — fonte primária](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-m12-objects-pickups-approved/experiments/DOOM_Manifold_E1M1/m01/m12_objects.py)
- [stage_rom.py — integração opt-in](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-m12-objects-pickups-approved/experiments/DOOM_Manifold_E1M1/m01/stage_rom.py)
- [emit_portal_map.py — serialização de THINGS](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-m12-objects-pickups-approved/experiments/DOOM_Manifold_E1M1/m01/emit_portal_map.py)
- [m12_pickups.py — etapa POSTERIOR opcional](https://github.com/bollux78/MD-DOOM64KB/blob/exp-manifold-m12-objects-pickups-approved/experiments/DOOM_Manifold_E1M1/m01/m12_pickups.py).

**Ponto crucial:** não é um sprite VDP posicionado na tela em coordenadas fixas. É um objeto do mundo, associado a uma célula/setor, projetado em perspectiva, desenhado como *billboard* pelo rasterizador de sprites RLE do renderer (obj_sprite).

## 2. Pipeline comprovado no código histórico

1. **Fonte local legalmente disponível:** `wad_textures.Wad(wad)` lê os lumps do WAD do usuário durante o build. `WT.patch_image(w.lump("BAR1A0"))` decodifica pixels/transparência e `WT.playpal(w)` lê a paleta. **Não publicar WAD, lumps extraídos ou sprites protegidos no GitHub/artefatos.**
2. **Remapeamento de cores:** o script transforma a cor do WAD na entrada mais próxima da paleta VDP `vdp_palette`, por `WT.nearest(palette,rgb[p])`. Cada pixel de desenho passa a byte `(c << 4) | c` porque o kernel de coluna espera **dois pixels horizontais 4bpp por byte**; transparência permanece ausente (`None`).
3. **Reamostragem:** cada patch é convertido em uma grade fixa de **64 colunas × 64 linhas**, usando `min(pw-1,x*pw//64)` / `min(ph-1,y*ph//64)`. Cada coluna é comprimida como spans RLE: pares `(skip,count)` mais bytes `texels`; coluna vazia tem `num_spans=0`. Emitir `const rle_sprite m12_sprite_barrel` no C gerado (não gravar assets binários no repo).
4. **Posicionamento no mapa:** ler as entradas de `lumps["THINGS"]` como `(x,y,angle,kind,flags)`. Filtrar tipos não implementados, flags incompatíveis e dificult. Para cada THING, determinar exatamente **uma** célula convexa do mapa por `point_inside([w["a"] for w in c["walls"]], (x*16,y*16))`; se zero ou várias, registrar `skipped ambiguous` em vez de escolher setor errado. Há guarda de máximo **126** placements históricos.
5. **Emitir THINGS:** `emit_portal_map.emit(...,things=m12_things)` cria `static map_object e1_m12_things[] = { {.sector_num=cell,.x=x,.y=y,.z=0,.type=template_index}, ... }` e configura `.num_things` / `.things` na estrutura `portal_map e1m1_map`. As coordenadas em THINGS permanecem em unidades Doom; a checagem da célula usa escala ×16 da geometria intermediária.
6. **Vincular templates:** `install_templates()` substituía na cópia staged o array `object_types[32+1]` de `src/object.c`, mantendo player na posição inicial e criando entradas `DECORATION` com `.sprite=&m12_sprite_barrel`, `.flags=FLAGS_ANCHOR_BOT_MASK`, `.init_state=IDLE_STATE` e dimensões físicas/projetadas. O primeiro barril apareceu **grande demais**; o script histórico contém comentário explícito de ajuste de **−25%** em largura e altura. Expressões usadas após a correção: `.width=width*3//2`, `.height=height*24` (verificar unidades com o código atual antes de transportar).
7. **Raster de sprite:** quando `MANIFOLD_OBJECTS=1`, o `stage_rom.py` histórico gerava `src/m12_doom_objects.c`, instalava templates, e chamava `m12_safe_sprite_raster(out)`, que substitui a função `draw_rle_sprite` em `src/obj_sprite.c`. O comentário do patch descreve raster C com stepping fixed-point, busca vertical pré-calculada uma vez por sprite e **clipping vertical pelo portal**; evitar divisões por pixel. Ler a função histórica completa antes de aplicar.
8. **Integração opt-in histórica:** `MANIFOLD_OBJECTS=1` exige a paleta de mapa DOOM; `MANIFOLD_PICKUPS=1` era etapa separada e dependia também de HUD Doom. O primeiro objetivo aqui é **visual**, sem coleta, colisão, combate, explosão ou IA.

## 3. Como trazer para a linha compartilhada sem destruir M13

- **Não cherry-pick da branch de objetos inteira.** São bases divergentes, com mudanças antigas de stage, renderer, HUD e geometria. Usar arquivos antigos como fonte e **portar os trechos mínimos para o head atual**.
- Conferir diferenças de `stage_rom.py`, `emit_portal_map.py`, `src/object.c`, `src/obj_sprite.c`, layouts `portal_map/map_object`, `FLAGS_ANCHOR_BOT_MASK` e registradores ASM/SGDK2 antes de aplicar.
- Manter tudo sob flag nova ou a mesma `MANIFOLD_OBJECTS=1`, com controle `=0` compilando bit a bit / funcionalmente como antes. Não presumir offsets, índices de templates nem slots de sprites.
- **Primeiro milestone:** um único barril no seu THING real em E1M1, transparente, no chão, com tamanho correto, variando com distância/ângulo; preservar textura, cor e oclusão. Depois ativar várias decorações da tabela. Se o projeto atual não resolver o THING real do barril no enquadramento testado, criar câmera de teste reprodutível para um THING 2035, sem falsificar coordenadas.
- **Ordenação/oclusão:** paredes e portais devem cobrir o barril atrás deles; o barril não deve atravessar paredes; avaliar relação com `yclip` e modo BSP. Não declarar correção apenas porque o sprite apareceu sobre tudo.
- **Segurança dos buffers:** confirmar limites, dados RLE, spans e índices de paleta; não reintroduzir sobrescrita de VRAM/HUD. Verificar resultado visual no hardware (BlastEm/MAME servem para triagem).
- **Performance:** contar objetos candidatos/projetados/visíveis/desenhados, pixels e tempo de raster; nas áreas abertas o M13.2 all-leaves já regrediu de ~4 para ~1 FPS, portanto **não misturar o diagnóstico dos buracos com o custo de sprites**. A/B mesmo ponto com flag OFF/ON.
- **Entrega:** variante A controle sem objetos, B com barril estático, no mesmo renderer H40/mesmo commit salvo flag; logs de skips por THING e métricas. Não ativar pickups até validar visual e desempenho. Não alterar releases.

## 4. Trechos de código para orientar o porto (ilustrativos, não patch pronto)

No `m12_objects.py` histórico:

```python
TYPES = ((2035, "BAR1A0", "barrel", 32, 56), ...)
# Decodifica patch do WAD / reamostra 64x64 / compacta colunas RLE.
# Extrai THINGS e resolve uma única célula convexa por object.
# Cada placement: (sector_cell, x_doom, y_doom, template_index).
```

No `emit_portal_map.py` histórico:

```c
static map_object e1_m12_things[] = {
    { .sector_num = CELL_INDEX, .x = DOOM_X,
      .y = DOOM_Y, .z = 0, .type = BARREL_TEMPLATE_SLOT },
};
/* e1m1_map: .num_things=..., .things=e1_m12_things */
```

No `stage_rom.py` histórico:

```python
if os.environ.get("MANIFOLD_OBJECTS","0") == "1":
    from m12_objects import generate, install_templates
    sprite_c, templates, m12_things = generate(
        wad, map_lumps, cells, tex["vdp_palette"], point_inside)
    (out/"src/m12_doom_objects.c").write_text(sprite_c)
    install_templates(out, templates)
    m12_safe_sprite_raster(out)
(out/"src/e1m1_map.c").write_text(
    emit(map_lumps, cells, tex, things=m12_things))
```

O código acima mostra **onde** se conectam os estágios; constantes e estruturas devem ser verificadas contra o head de M13 antes do porte.

## 5. Relação com os problemas atuais e critério de aceite

A correção das alturas pelo all-leaves **não** corrigiu blocos azul-escuros na área externa; o FPS foi relatado ~4→~1. O trabalho de objetos **não** deve ser apresentado como solução para esses dois problemas. Idealmente executar em branch/flag de teste baseada no código compartilhado e pedir ao usuário teste no console antes de qualquer promoção.

**Aceite mínimo para o barril:** (1) aparece no THING 2035 correto, (2) está no chão e com escala aceitável, (3) transparência preservada, (4) não atravessa paredes, (5) desaparece corretamente fora do campo de visão e atrás de paredes, (6) sem corrupção de HUD/framebuffer, (7) FPS A/B reportado, (8) controle sem objetos inalterado.

**Próxima responsabilidade do Cláudio:** revisar código antigo e devolver proposta/patch opt-in mínimo, com evidências verificáveis. Nenhum build disparado por este handoff.
