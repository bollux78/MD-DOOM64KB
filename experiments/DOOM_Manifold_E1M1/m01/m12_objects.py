"""M12 opt-in: convert static THINGS and 64-column sprites from private shareware WAD.
No WAD assets are committed. Decoration is visual only; no pickup/combat yet.
"""
from collections import Counter
from pathlib import Path
import wad_textures as WT

TYPES = (
 (2035,"BAR1A0","barrel",32,56),
 (2028,"COLUA0","lamp",16,64),
 (2011,"STIMA0","stimpack",20,24),
 (2012,"MEDIA0","medikit",32,24),
 (2007,"CLIPA0","ammo",16,16),
 (2001,"SHOTA0","shotgun",32,16),
 (2014,"BON1A0","health",16,16),
 (2015,"BON2A0","armor",16,16),
)
def generate(wad, lumps, cells, vdp_palette, point_inside):
    w=WT.Wad(wad)
    rgb=WT.playpal(w)
    palette=[(((v>>1)&7)*255//7,((v>>5)&7)*255//7,((v>>9)&7)*255//7) for v in vdp_palette]
    lines=['#include <genesis.h>','#include "obj_sprite.h"']
    templates=[]; mapping={}
    for kind,lump,name,width,height in TYPES:
        try: pw,ph,img=WT.patch_image(w.lump(lump))
        except KeyError:
            print("M12 skipped missing patch:",lump)
            continue
        if not 0<pw<=512 or not 0<ph<=512: raise ValueError("Invalid patch dimensions")
        idx=len(templates)+1
        ident="m12_sprite_"+name
        cols=[]
        for x in range(64):
            seq=[img[min(ph-1,y*ph//64)][min(pw-1,x*pw//64)] for y in range(64)]
            # Manifold draw_col writes a byte encoding TWO horizontal 4bpp pixels.
            seq=[None if p is None else (lambda c: (c << 4) | c)(WT.nearest(palette,rgb[p])) for p in seq]
            spans=[];texels=[];y=0
            while y<64:
                skip=0
                while y<64 and seq[y] is None: skip+=1;y+=1
                if y==64: break
                first=y
                while y<64 and seq[y] is not None: texels.append(seq[y]);y+=1
                spans.extend((skip,y-first))
            if spans:
                a=f"m12_{idx}_{x}_sp";b=f"m12_{idx}_{x}_px"
                lines.append(f"static const u16 {a}[] = {{{','.join(map(str,spans))}}};")
                lines.append(f"static const u8 {b}[] = {{{','.join(map(str,texels))}}};")
                cols.append(f"{{.num_spans={len(spans)//2},.spans={a},.texels={b}}}")
            else: cols.append("{.num_spans=0,.spans=0,.texels=0}")
        lines.append(f"const rle_sprite {ident} = {{.num_columns=64,.columns={{")
        lines.append(",\n".join(cols))
        lines.append("}};")
        templates.append((ident,name,width,height))
        mapping[kind]=idx
    if not templates: raise ValueError("M12 needs at least one sprite from local WAD")
    placements=[];skipped=Counter()
    for x,y,angle,kind,flags in lumps["THINGS"]:
        if kind not in mapping or flags&16 or not (flags&7): continue
        matches=[i for i,c in enumerate(cells) if point_inside([w["a"] for w in c["walls"]],(x*16,y*16))]
        if len(matches)!=1: skipped[kind]+=1;continue
        placements.append((matches[0],x,y,mapping[kind]))
    if len(placements)>126: raise ValueError(f"Too many decorations: {len(placements)}")
    print("M12 THINGS inserted",len(placements),"skipped ambiguous:",dict(skipped))
    return "\n".join(lines)+"\n",templates,placements

def install_templates(out,templates):
    p=Path(out)/"src/object.c";s=p.read_text()
    a=s.index("const object_template object_types[32+1] = {")
    b=s.index("\n\nint look_for_player(",a)
    externs="".join(f"extern const rle_sprite {ident};\n" for ident,*_ in templates)
    entries=['{.name="player",.type=OBJECT}']
    for ident,name,width,height in templates:
        entries.append(f'{{.sprite=&{ident},.name="{name}",.width={width},.height={height*32},.flags=FLAGS_ANCHOR_BOT_MASK,.init_state=IDLE_STATE,.type=DECORATION}}')
    p.write_text(s[:a]+externs+"const object_template object_types[32+1] = {\n"+",\n".join(entries)+"\n};"+s[b:])
