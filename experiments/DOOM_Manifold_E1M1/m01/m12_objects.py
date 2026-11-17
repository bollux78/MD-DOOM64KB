"""M12 opt-in: convert static THINGS and 64-column sprites from private shareware WAD.
No WAD assets are committed. Decoration is visual only; no pickup/combat yet.
"""
from collections import Counter
from pathlib import Path
import os
import wad_textures as WT
_MIXC={}

TYPES = (
 (2035,"BAR1A0","barrel",32,56),
 (2028,"COLUA0","lamp",16,64),
 (2011,"STIMA0","stimpack",20,24),
 (2012,"MEDIA0","medikit",32,24),
 (2007,"CLIPA0","ammo",16,16),
 (2001,"SHOTA0","shotgun",32,16),
 (2014,"BON1A0","health",16,16),
 (2015,"BON2A0","armor",16,16),
 # M14: remaining non-monster THINGS of E1M1. Box = patch size x the barrel's
 # approved ratios (width x1.39, height x1.75); monsters are NOT converted.
 (35,"CBRAA0","candelabra",40,107),
 (48,"ELECA0","techcolumn",53,224),
 (24,"POL5A0","bloodpool",76,18),
 (10,"PLAYW0","gibs",79,39),
 (12,"PLAYW0","gibs",79,39),
 (15,"PLAYN0","deadplayer",71,25),
 (2002,"MGUNA0","chaingun",75,28),
 (2003,"LAUNA0","rocketlauncher",86,28),
 (2008,"SHELA0","shells",21,12),
 (2018,"ARM1A0","greenarmor",43,30),
 (2019,"ARM2A0","bluearmor",43,30),
 (2046,"BROKA0","rocketbox",75,37),
 (2048,"AMMOA0","bulletbox",39,28),
 (2049,"SBOXA0","shellbox",44,21),
 # M14: BRNBIG lattice (two-sided mid-textured fences, sector 72) as 32-unit
 # billboard slices; box = slice x 1.39 wide, 128 x 1.75 high.
 # M14: monsters, static (no AI yet) at their E1M1 start positions, front frame
 # A1; width/height 0 = derive from the patch with the barrel's approved ratios.
 (3004,"POSSA1","zombieman",0,0),
 (9,"SPOSA1","sergeant",0,0),
 (3001,"TROOA1","imp",0,0),
 (9101,"POSSF1","zombieman_atk",0,0),
 (9102,"SPOSF1","sergeant_atk",0,0),
 (9103,"TROOF1","imp_atk",0,0),
 (9111,"POSSL0","zombieman_dead",0,0),
 (9112,"SPOSL0","sergeant_dead",0,0),
 (9113,"TROOM0","imp_dead",0,0),
 (9001,"GRATE_L","grate_l",44,224),
 (9002,"GRATE_R","grate_r",44,224),
 (9003,"GRATE_C0","grate_c0",44,224),
 (9004,"GRATE_C1","grate_c1",44,224),
 (9005,"GRATE_C2","grate_c2",44,224),
 (9006,"GRATE_C3","grate_c3",44,224),
 # M14 shareware: the remaining E1 monsters, static front frame A1.
 # Spectre = demon sprite with a checkerboard of transparent texels (fuzz look).
 (3002,"SARGA1","demon",0,0),
 (58,"SARGA1","spectre",0,0),
 (3003,"BOSSA1","baron",0,0),
 # M14: remaining E1 pickups (patch size x the barrel ratios)
 (9301,"BEXPA0","bexp0",0,0),
 (9302,"BEXPB0","bexp1",0,0),
 (9303,"BEXPC0","bexp2",0,0),
 (9304,"BEXPD0","bexp3",0,0),
 (9305,"BEXPE0","bexp4",0,0),
 (2025,"SUITA0","radsuit",0,0),
 (2013,"SOULA0","soulsphere",0,0),
 (2024,"PINSA0","invis",0,0),
 (2045,"PVISA0","lightamp",0,0),
 (2026,"PMAPA0","compmap",0,0),
 (2010,"ROCKA0","rocket",0,0),
 (2005,"CSAWA0","chainsaw",0,0),
 (8,"BPAKA0","backpack",0,0),
 (5,"BKEYA0","bluekey",0,0),
 (6,"YKEYA0","yellowkey",0,0),
 (13,"RKEYA0","redkey",0,0),
 # M14 r057: monster animation frames (2nd walk frame, pain, one death frame), front rotation
 (9400,"POSSC1","zombieman_w1",0,0),
 (9402,"POSSJ0","zombieman_d0",0,0),
 (9403,"SPOSC1","sergeant_w1",0,0),
 (9405,"SPOSJ0","sergeant_d0",0,0),
 (9406,"TROOC1","imp_w1",0,0),
 (9408,"TROOK0","imp_d0",0,0),
 # M14 r066: the rest of the monster animation sets (walk B,D; aim; pain; death frames)
 (9420,"POSSB1","zombieman_wb",0,0),
 (9421,"POSSD1","zombieman_wd",0,0),
 (9422,"POSSE1","zombieman_aim",0,0),
 (9423,"POSSG1","zombieman_pain",0,0),
 (9424,"POSSH0","zombieman_dh",0,0),
 (9427,"SPOSB1","sergeant_wb",0,0),
 (9428,"SPOSD1","sergeant_wd",0,0),
 (9429,"SPOSE1","sergeant_aim",0,0),
 (9430,"SPOSG1","sergeant_pain",0,0),
 (9431,"SPOSH0","sergeant_dh",0,0),
 (9434,"TROOB1","imp_wb",0,0),
 (9435,"TROOD1","imp_wd",0,0),
 (9436,"TROOE1","imp_aim",0,0),
 (9437,"TROOH1","imp_pain",0,0),
 (9438,"TROOI0","imp_dh",0,0),

 # r068: back (A5,C5) and side (A3, A7 = A3 mirrored) frames for every monster; demon/spectre/baron get their animation sets
 (9457,"POSSA5","zombieman_bk0",0,0),
 (9458,"POSSC5","zombieman_bk1",0,0),
 (9459,"POSSA3A7","zombieman_sl",0,0),
 (9460,"POSSA3A7~","zombieman_sr",0,0),
 (9468,"SPOSA5","sergeant_bk0",0,0),
 (9469,"SPOSC5","sergeant_bk1",0,0),
 (9470,"SPOSA3A7","sergeant_sl",0,0),
 (9471,"SPOSA3A7~","sergeant_sr",0,0),
 (9479,"TROOA5","imp_bk0",0,0),
 (9480,"TROOC5","imp_bk1",0,0),
 (9481,"TROOA3A7","imp_sl",0,0),
 (9482,"TROOA3A7~","imp_sr",0,0),
 (9483,"SARGC1","demon_w1",0,0),
 (9484,"SARGE1","demon_aim",0,0),
 (9485,"SARGF1","demon_atk",0,0),
 (9486,"SARGH1","demon_pain",0,0),
 (9487,"SARGI0","demon_dh",0,0),
 (9488,"SARGK0","demon_d0",0,0),
 (9489,"SARGN0","demon_dead",0,0),
 (9490,"SARGA5","demon_bk0",0,0),
 (9491,"SARGC5","demon_bk1",0,0),
 (9492,"SARGA3A7","demon_sl",0,0),
 (9493,"SARGA3A7~","demon_sr",0,0),
 (9494,"SARGC1","spectre_w1",0,0),
 (9495,"SARGE1","spectre_aim",0,0),
 (9496,"SARGF1","spectre_atk",0,0),
 (9497,"SARGH1","spectre_pain",0,0),
 (9498,"SARGI0","spectre_dh",0,0),
 (9499,"SARGK0","spectre_d0",0,0),
 (9500,"SARGN0","spectre_dead",0,0),
 (9501,"SARGA5","spectre_bk0",0,0),
 (9502,"SARGC5","spectre_bk1",0,0),
 (9503,"SARGA3A7","spectre_sl",0,0),
 (9504,"SARGA3A7~","spectre_sr",0,0),
 (9505,"BOSSC1","baron_w1",0,0),
 (9506,"BOSSE1","baron_aim",0,0),
 (9507,"BOSSF1","baron_atk",0,0),
 (9508,"BOSSH1","baron_pain",0,0),
 (9509,"BOSSI0","baron_dh",0,0),
 (9510,"BOSSK0","baron_d0",0,0),
 (9511,"BOSSO0","baron_dead",0,0),
 (9512,"BOSSA5","baron_bk0",0,0),
 (9513,"BOSSC5","baron_bk1",0,0),
 (9514,"BOSSA3A7","baron_sl",0,0),
 (9515,"BOSSA3A7~","baron_sr",0,0),
 # projectiles (appended at the end: IDs follow order)
 (9520,"BAL1A0","fball0",0,0),
 (9522,"BAL1C0","fbx0",0,0),
 (9525,"MISLA1","rocketp",0,0),
)

def _masked_texture(w,texdefs,name):
    """Composite a texture keeping unpainted texels transparent (None)."""
    wdt,hgt,patches=texdefs[name]
    img=[[None]*wdt for _ in range(hgt)]
    for ox,oy,pname in patches:
        try: pw,ph,pim=WT.patch_image(w.lump(pname))
        except KeyError: continue
        for y in range(ph):
            for x in range(pw):
                v=pim[y][x]
                if v is not None and 0<=x+ox<wdt and 0<=y+oy<hgt: img[y+oy][x+ox]=v
    return wdt,hgt,img

def grate_extra(w):
    """name -> (pw,ph,img) 32-wide slices of BRNBIGL / BRNBIGR / BRNBIGC."""
    td=WT.textures(w);out={}
    if "BRNBIGL" not in td: return {}
    for key,tex,x0 in (("GRATE_L","BRNBIGL",0),("GRATE_R","BRNBIGR",0),("GRATE_C0","BRNBIGC",0),
                       ("GRATE_C1","BRNBIGC",32),("GRATE_C2","BRNBIGC",64),("GRATE_C3","BRNBIGC",96)):
        wdt,hgt,img=_masked_texture(w,td,tex)
        out[key]=(32,hgt,[row[x0:x0+32] for row in img])
    return out

ZCODE={}
def grate_placements():
    """(x,y,kind) of the slices: west fence x=2888 and east fence x=3128 of
    E1M1 (linedefs 298-303); y runs -4352..-4160, 32 units per slice."""
    ys=[-4336,-4304,-4272,-4240,-4208,-4176]
    west=[9001,9003,9004,9005,9006,9002]
    east=[9002,9003,9004,9005,9006,9001]
    return [(2888,y,k) for y,k in zip(ys,west)]+[(3128,y,k) for y,k in zip(ys,east)]
def kinds_has_grates(w):
    return True

class _SafeWad:
    """MANIFOLD_SAFE_WAD=1 (other IWADs, e.g. Heretic): sprites missing from the WAD become empty 1x1 placeholders, so the
    Doom type table and its M14_ID_* names still exist and the build goes on."""
    @staticmethod
    def _mk():
        import struct
        n=16; col=bytes([0,n,0])+bytes([200])*n+bytes([0,255])
        return struct.pack("<hhhh",n,n,-140,-110)+b"".join(struct.pack("<I",8+4*n+len(col)*c) for c in range(n))+col*n
    _DUMMY=None
    def __init__(self,w):
        self._w=w
        if _SafeWad._DUMMY is None: _SafeWad._DUMMY=_SafeWad._mk()
    def lump(self,n):
        try: return self._w.lump(n)
        except KeyError:
            if n.startswith(("TEXTURE","PNAMES","PLAYPAL","COLORMAP")): raise
            if n.startswith("DS"): return b"\x03\x00\x11\x2b\x20\x00\x00\x00"+b"\x80"*32
            return self._DUMMY
    def __getattr__(self,a): return getattr(self._w,a)

def generate(wad, lumps, cells, vdp_palette, point_inside):
    w=WT.Wad(wad)
    if os.environ.get("MANIFOLD_SAFE_WAD")=="1": w=_SafeWad(w)
    rgb=WT.playpal(w)
    palette=[(((v>>1)&7)*255//7,((v>>5)&7)*255//7,((v>>9)&7)*255//7) for v in vdp_palette]
    lines=['#include <genesis.h>','#include "obj_sprite.h"']
    templates=[]; mapping={}
    seen={}
    extra=grate_extra(w) if kinds_has_grates(w) else {}
    _present={k for _x,_y,_a,k,f in lumps["THINGS"] if f&2 and not f&16}
    _diet={}; colinfo={}
    _lk={}
    for _k,_l2,_n,_w,_h in TYPES: _lk.setdefault(_l2,set()).add(_k)
    _map=os.environ.get("MANIFOLD_MAP","E1M1")
    def _unused(kind,lump,name):        # r068: sprites of things this map never places keep header + size but carry no columns
        if name.startswith("grate_"): return not (_map=="E1M1" and os.environ.get("MANIFOLD_GRATE_SPRITES","1")=="1")
        if name.startswith("bexp"): return 2035 not in _present
        if kind<9000: return not any(k in _present for k in _lk[lump])
        return False
    if os.environ.get("MANIFOLD_MAP","E1M1") in ("E1M2","E1M3","E1M4"):      # r067: these map blocks are the fullest -> fewer animation frames
        for _f in ("zombieman","sergeant","imp","demon","spectre","baron"):
            _diet.update({f"{_f}_wd":_f,f"{_f}_bk1":f"{_f}_bk0"})
            if os.environ.get("MANIFOLD_MAP")=="E1M3": _diet.update({f"{_f}_aim":_f,f"{_f}_wb":f"{_f}_w1"})
    for kind,lump,name,width,height in TYPES:
        _flip = name.endswith("_sr") and lump.endswith("~")
        if _flip:                   # r068: right-side view = left-side view mirrored -> same column data, reversed order, own header
            _ai=[i for i,t in enumerate(templates) if t[1]==name[:-3]+"_sl"][0]+1
            import struct as _st3
            _pw,_ph=_st3.unpack('<hh',w.lump(lump[:-1])[:4])
            _wd=width or round(_pw*1.39); _ht=height or round(_ph*1.75)
            idx=len(templates)+1; ident="m12_sprite_"+name
            lines.append(f"const rle_sprite __attribute__((section(\".rodata.m12hdr\"))) {ident} = {{.num_columns=64,.columns={{")
            lines.append(",\n".join(f"{{.num_spans={colinfo[_ai][63-x]},.spans=m12_{_ai}_{63-x}_sp,.texels=m12_{_ai}_{63-x}_px}}" if colinfo[_ai][63-x] else "{.num_spans=0,.spans=0,.texels=0}" for x in range(64)))
            lines.append("}};")
            templates.append((ident,name,_wd,_ht)); mapping[kind]=idx; colinfo[idx]=[colinfo[_ai][63-x] for x in range(64)]; seen[lump]=idx; continue
        if name in _diet:           # own header (same layout/size in every map) pointing at a neighbouring frame's column data
            _ai=[i for i,t in enumerate(templates) if t[1]==_diet[name]]
            if _ai:
                import struct as _st2
                _ai=_ai[0]+1; _pw,_ph=_st2.unpack('<hh',w.lump(lump)[:4])
                _wd=width or round(_pw*1.39); _ht=height or round(_ph*1.75)
                idx=len(templates)+1; ident="m12_sprite_"+name
                lines.append(f"const rle_sprite __attribute__((section(\".rodata.m12hdr\"))) {ident} = {{.num_columns=64,.columns={{")
                lines.append(",\n".join(f"{{.num_spans={n},.spans=m12_{_ai}_{x}_sp,.texels=m12_{_ai}_{x}_px}}" if n else "{.num_spans=0,.spans=0,.texels=0}" for x,n in enumerate(colinfo[_ai])))
                lines.append("}};")
                templates.append((ident,name,_wd,_ht)); mapping[kind]=idx; seen[lump]=idx; continue
        _spec=name.startswith("spectre"); _sk=lump+("#S" if _spec else "")
        if _sk in seen:            # several THING kinds, one sprite
            mapping[kind]=seen[_sk]; continue
        _grp={"zombieman":3004,"sergeant":9,"imp":3001,"demon":3002,"spectre":58,"baron":3003}.get(name.split("_")[0])
        if (_grp is not None and _grp not in _present) or _unused(kind,lump,name):      # r057: monster not in this map -> empty sprite (saves map ROM)
            if lump in extra: pw,ph=extra[lump][0],extra[lump][1]
            else:
                _l=w.lump(lump); import struct as _st; pw,ph=_st.unpack('<hh',_l[:4])
            img=[[None]*pw for _ in range(ph)]   # keep the true size: object_types lives in common code
        else:
          try:
              if _spec:
                  pw,ph,img=WT.patch_image(w.lump(lump))
                  img=[[(None if (x+y)&1 else v) for x,v in enumerate(row)] for y,row in enumerate(img)]
              else:
                  pw,ph,img=extra[lump] if lump in extra else WT.patch_image(w.lump(lump))
          except KeyError:
            print("M12 skipped missing patch:",lump)
            continue
        if not 0<pw<=512 or not 0<ph<=512: raise ValueError("Invalid patch dimensions")
        if not width: width=round(pw*1.39)
        if not height: height=round(ph*1.75)
        idx=len(templates)+1
        ident="m12_sprite_"+name
        cols=[]; _ci=[]; colinfo[idx]=_ci
        for x in range(64):
            seq=[img[min(ph-1,y*ph//64)][min(pw-1,x*pw//64)] for y in range(64)]
            # Manifold draw_col writes a byte encoding TWO horizontal 4bpp pixels.
            # r060: like the wall textures, mix two palette colours per byte (alternating screen columns)
            def _px(p, _m=os.environ.get("MANIFOLD_SPRITE_MIX","1")=="1"):
                if p is None: return None
                k=(rgb[p],_m)
                if k not in _MIXC:
                    if _m:
                        a_,b_=WT.nearest_pair(palette,rgb[p]); _MIXC[k]=(a_<<4)|b_
                    else:
                        c=WT.nearest(palette,rgb[p]); _MIXC[k]=(c<<4)|c
                return _MIXC[k]
            seq=[_px(p) for p in seq]
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
                _fm=name.split("_")[0]
                _sec=(' __attribute__((section(".mapgap")))' if _fm in os.environ.get("MANIFOLD_GAPFAMS","").split(",") else ' __attribute__((section(".mapextra")))') if _fm in ("zombieman","sergeant","imp","demon","spectre","baron") else (' __attribute__((section(".mapextra")))' if name.startswith(("fball","fbx","rocketp","rbx")) else "")   # r068: .mapgap = free bytes inside the fixed layout of the map block
                lines.append(f"static const u16{_sec} {a}[] = {{{','.join(map(str,spans))}}};")
                lines.append(f"static const u8{_sec} {b}[] = {{{','.join(map(str,texels))}}};")
                cols.append(f"{{.num_spans={len(spans)//2},.spans={a},.texels={b}}}"); _ci.append(len(spans)//2)
            else: cols.append("{.num_spans=0,.spans=0,.texels=0}"); _ci.append(0)
        lines.append(f"const rle_sprite __attribute__((section(\".rodata.m12hdr\"))) {ident} = {{.num_columns=64,.columns={{")
        lines.append(",\n".join(cols))
        lines.append("}};")
        templates.append((ident,name,width,height))
        mapping[kind]=idx
        seen[_sk]=idx
    if not templates: raise ValueError("M12 needs at least one sprite from local WAD")
    placements=[];skipped=Counter()
    for x,y,angle,kind,flags in lumps["THINGS"]:
        if kind not in mapping or flags&16 or not (flags&2): continue      # skill 3 (Hurt Me Plenty) only
        matches=[i for i,c in enumerate(cells) if point_inside([w["a"] for w in c["walls"]],(x*16,y*16))]
        if len(matches)!=1:
            # on a cell edge / vertex: nudge a few units until exactly one cell holds it
            for r in (1,2,3,4,6):
                for ddx,ddy in ((r,0),(-r,0),(0,r),(0,-r),(r,r),(-r,r),(r,-r),(-r,-r)):
                    m2=[i for i,c in enumerate(cells) if point_inside([w["a"] for w in c["walls"]],((x+ddx)*16,(y+ddy)*16))]
                    if len(m2)==1: matches=m2; x+=ddx; y+=ddy; break
                if len(matches)==1: break
        if len(matches)!=1: skipped[kind]+=1;continue
        placements.append((matches[0],x,y,mapping[kind]))
        ZCODE[(matches[0],x,y)]=((angle*128//360)&127)|(128 if flags&8 else 0)   # facing (7 bits) + deaf/ambush
    if extra and __import__("os").environ.get("MANIFOLD_MAP","E1M1")=="E1M1" and __import__("os").environ.get("MANIFOLD_GRATE_SPRITES","1")=="1":
        for x,y,kind in grate_placements():
            if kind not in mapping: continue
            m=[i for i,c in enumerate(cells) if point_inside([wl["a"] for wl in c["walls"]],(x*16,y*16))]
            if len(m)!=1:
                # on a cell boundary: nudge one unit into the room
                m=[i for i,c in enumerate(cells) if point_inside([wl["a"] for wl in c["walls"]],((x+(1 if x<3000 else -1))*16,y*16))]
            if len(m)!=1: print("M14 grate slice skipped",x,y,len(m));continue
            placements.append((m[0],x+(1 if x<3000 else -1),y,mapping[kind]))
    import os as _os
    monster_idx={mapping[k] for k in (3004,9,3001,3002,58,3003) if k in mapping}
    if _os.environ.get("MANIFOLD_MONSTERS","0")=="1":
        mons=[pl for pl in placements if pl[3] in monster_idx]
        decs=[pl for pl in placements if pl[3] not in monster_idx]
        if len(mons)>60:
            st=len(mons)/60.0; mons=[mons[int(i*st)] for i in range(60)]
    else:
        mons=[]
        decs=[pl for pl in placements if pl[3] not in monster_idx] if len(placements)>126 else placements
    # Decorations share one pool (255 slots with the M14 patch).  Pickups first, then
    # monsters, then pure scenery; keep a reserve for corpses of killed monsters.
    ITEM_KINDS={2011,2012,2007,2001,2014,2015,2002,2003,2008,2018,2019,2046,2048,2049,2025,2013,2024,
                2045,2026,2010,2005,8,5,6,13}
    item_idx={mapping[k] for k in ITEM_KINDS if k in mapping}
    total=int(_os.environ.get("MANIFOLD_DEC_CAP","254"))
    cap=total-len(mons)-int(_os.environ.get("MANIFOLD_CORPSE_RESERVE","24"))
    items=[pl for pl in decs if pl[3] in item_idx]
    scen=[pl for pl in decs if pl[3] not in item_idx]
    if len(items)>cap:
        bon={mapping[k] for k in (2014,2015) if k in mapping}
        keep=[pl for pl in items if pl[3] not in bon]; bons=[pl for pl in items if pl[3] in bon]
        n=max(0,cap-len(keep))
        if n and bons:
            st=len(bons)/n; keep+= [bons[int(i*st)] for i in range(min(n,len(bons)))]
        items=keep[:cap]
        print(f"M14 pickups cut -> {len(items)}")
    room=cap-len(items)
    if len(scen)>room:
        st=len(scen)/room if room else 1; scen=[scen[int(i*st)] for i in range(room)] if room else []
    decs=items+scen
    placements=decs+mons
    print("M12 THINGS inserted",len(placements),"skipped ambiguous:",dict(skipped))
    return "\n".join(lines)+"\n",templates,placements

def install_templates(out,templates):
    p=Path(out)/"src/object.c";s=p.read_text()
    a=s.index("const object_template object_types[32+1] = {")
    b=s.index("\n\nint look_for_player(",a)
    externs="".join(f"extern const rle_sprite {ident};\n" for ident,*_ in templates)
    entries=['{.name="player",.type=OBJECT}']
    import os as _os
    mon=_os.environ.get("MANIFOLD_MONSTERS","0")=="1"
    hdr=["#ifndef M14_IDS_H","#define M14_IDS_H"]
    for i,(ident,name,width,height) in enumerate(templates):
        hdr.append(f"#define M14_ID_{name.upper()} {i+1}")
    hdr.append("#endif")
    (Path(out)/"src/m14_ids.h").write_text("\n".join(hdr)+"\n")
    _hp=int(os.environ.get('MANIFOLD_OBJ_HEIGHT_PCT','100'))
    for ident,name,width,height in templates:
        if mon and name.split("_")[0] in ("zombieman","sergeant","imp","demon","spectre","baron") and name.split("_")[-1] not in ("dh","d0","dead"):   # r070: EVERY live frame is an OBJECT (shots only hit OBJECT sprites)
            _inact = os.environ.get("MANIFOLD_MONSTERS_INACTIVE","0")=="1"
            _ist = 0 if _inact else 1
            _typ = "DECORATION" if _inact else "OBJECT"
            entries.append(f'{{.sprite=&{ident},.name="{name}",.width={width*3//2},.height={height*24*_hp//100},.flags=FLAGS_ANCHOR_BOT_MASK,.init_state={_ist},.type={_typ}}}')
            continue
        # The visual test showed an oversized barrel; reduce both projected
        # dimensions by 25% while preserving the same sprite pixels/THINGS.
        entries.append(f'{{.sprite=&{ident},.name="{name}",.width={width*3//2},.height={height*24*_hp//100},.flags=FLAGS_ANCHOR_BOT_MASK,.init_state=IDLE_STATE,.type=DECORATION}}')
    p.write_text(s[:a]+externs+"const object_template object_types[128] = {\n"+",\n".join(entries)+"\n};"+s[b:])
