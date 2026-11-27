"""Generate target C arrays from own fixture or local classic WAD.
Calibrated scaler rows are optional: fixture requires neither Ferret nor WAD.
No ROM or WAD source is committed. Output directories are runner-local.
"""
import argparse, hashlib, json, math, pathlib, struct, sys
P=pathlib.Path
sys.path.insert(0,str(P(__file__).parent.parent/"ferret-wad"))
from compiler import WAD,Resources,geometry,name,need
from visibility_compile import Compiler,pack_dag,find_leaf
from test_visibility import cameras,cell_sector
from render_scene import make_fixture
def rows(fsc,source_scale=False):
    if source_scale:
        assert not fsc, 'source-derived scaling and private calibration are mutually exclusive'
        from dread_source_math import generate
        full,_=generate()
    elif fsc:
        b=fsc.read_bytes();assert b[:4]==b"FSC1"
        n=struct.unpack_from(">H",b,4)[0];assert len(b)==6+10*n
        full=[]
        for i in range(n):
            end,step,bias=struct.unpack_from(">Hii",b,6+10*i)
            full.extend([tuple((y*step+bias)//65536 for y in range(72))]*(end+1-len(full)))
        assert len(full)==2048
    else:
        # Original, independently quantized reciprocal buckets for the fixture.
        def bucket(i):
            i=max(i,1);shift=max(0,i.bit_length()-5)
            return (i>>shift)<<shift
        full=[tuple((y-35)*128//bucket(i)-1 for y in range(72)) for i in range(2048)]
    unique={};indices=[]
    for r in full:
        if r not in unique:unique[r]=len(unique)
        indices.append(unique[r])
    assert len(unique)<=256,len(unique)
    return list(unique),indices
def emit(f,ctype,n,values):
    values=list(values)
    if not values:values=[0]
    f.write(f"static const {ctype} {n}[{len(values)}] = {{\n")
    for i in range(0,len(values),24):f.write(",".join(map(str,values[i:i+24]))+",\n")
    f.write("};\n")
def export(wad,k,output,fsc,fixture,asymmetric=False,art=False,dread=False,source_scale=False):
    g=geometry(wad,k)
    if art:
        if dread:
            from dread_art import DreadArt
            r=DreadArt(wad,g)
        else:
            from art_palette import Art
            r=Art(wad,g)
        (output.parent/"art-report.json").write_text(json.dumps(r.report,indent=2))
        print("ART PALETTE "+json.dumps(r.report),flush=True)
    else:r=Resources(wad)
    c=Compiler(g)
    asset_bytes=8192 if art else 4096
    cp=c.compile("occlusion96");dag,_=pack_dag(g,cp)
    assets=[];asset_index={};keys={}
    def texture(k,z,light=255):
        if k not in r.defs:raw=bytes([0 if art else 0x55])*asset_bytes;key=("fallback",0)
        else:
            if dread:
                from dread_art import bucket
                _,h,_=r.raw(k);key=(k,z%h,bucket(light))
            else:_,h,_=r.texture(k);key=(k,z%h)
            if key in keys:return keys[key]
            if dread:raw=r.pair_texture(k,z%h,light)
            elif art:raw=r.pair_texture(k,z%h)
            else:
                b,o=r.packed_texture(k,z%h);t=b[o:o+8192]
                raw=bytes((t[i]&240)|(t[i+1]&15) for i in range(0,8192,2))
        if raw not in asset_index:asset_index[raw]=len(assets);assets.append(raw)
        keys[key]=asset_index[raw];return keys[key]
    walls=[];leaf_floors=[];leaf_ceilings=[]
    for i,(n,a) in enumerate(g["subsectors"]):
        floor,ceil=cell_sector(g,i)[:2];leaf_floors.append(floor);leaf_ceilings.append(ceil)
    for v0,v1,_,lid,d,ofs in g["segs"]:
        l=g["lines"][lid];side=l[5+d];other=l[6-d]
        if side==65535:
            walls.append((v0,v1,255,0,0,0,0,0,0,0,0,0,0,0));continue
        sd=g["sides"][side];front=g["sectors"][sd[-1]]
        floor,ceil=front[:2];skyf=name(front[3])=="F_SKY1"
        back=g["sectors"][g["sides"][other][-1]] if other!=65535 else None
        solid=back is None or max(floor,back[0])>=min(ceil,back[1])
        if floor>=ceil:
            walls.append((v0,v1,255,0,0,0,0,0,0,0,0,0,0,0));continue
        if solid:
            variant=2 if skyf else 0;heights=(-ceil,-floor,-floor,-floor)
            uk=name(sd[4]);lk="-"
            if uk=="-":uk=next((name(t) for t in sd[2:4] if name(t)!="-"),"-")
            textured=True
        else:
            bf,bc=back[:2]
            upper=bc<ceil and not(skyf and name(back[3])=="F_SKY1")
            lower=bf>floor
            variant=({(False,False):13,(True,False):16,(False,True):14,(True,True):17} if skyf else {(False,False):7,(True,False):10,(False,True):8,(True,True):11})[(upper,lower)]
            heights=(-ceil,-min(ceil,bc) if upper else -ceil,-max(floor,bf),-floor)
            uk,lk=name(sd[2]),name(sd[3]);textured=upper or lower
        u0=((sd[0]+ofs)//2)%64;u1=u0+round(math.dist(g["vertices"][v0],g["vertices"][v1]))//2
        au=texture(uk,ceil+sd[1],front[4]) if textured else 0
        al=texture(lk,(back[0] if back else floor)+sd[1],front[4]) if textured else 0
        cc,fc=(r.color(name(front[3]),front[4]),r.color(name(front[2]),front[4])) if dread else (r.color(name(front[3])),r.color(name(front[2])))
        walls.append((v0,v1,variant,161 if textured else 160,u0,u1,*heights,cc,fc,au,al))
    sk=next((k for k in ("SKY1","SKY2","SKY3","SKY4") if k in r.defs),None)
    sw,sh,sky=r.texture(sk) if sk else (1,1,[bytes([0])])
    allposes=cameras(g,c,not fixture)
    spawn=[p for label,p,_,_ in allposes if label=="spawn"]
    zig=[p for label,p,_,_ in allposes if label=="zigzag-walkway"]
    poses=spawn[:4]+zig[:8] if zig else spawn[:4]
    if asymmetric:
        from asymmetric_fixture import POSES
        poses=POSES
    assert poses
    rs,idx=rows(fsc,source_scale)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w") as f:
        f.write("/* Generated locally; no original executable code. */\n")
        for n,v in (("SC_ART_PAIR",int(art)),("SC_ASSET_BYTES",asset_bytes),("SC_NODES",len(g["nodes"])),("SC_LEAVES",len(g["subsectors"])),("SC_WALLS",len(walls)),("SC_ASSETS",len(assets)),("SC_POSES",len(poses)),("SC_ROWS",len(rs)),("SC_SKYW",sw),("SC_SKYH",sh),("SC_FRV_BYTES",len(dag))):
            f.write(f"#define {n} {v}\n")
        emit(f,"uint8_t","sc_frv",dag)
        emit(f,"int16_t","sc_planes",(x for n in g["nodes"] for x in n[:4]))
        emit(f,"uint16_t","sc_children",(x for n in g["nodes"] for x in n[-2:]))
        emit(f,"int16_t","sc_vertices",(x for v in g["vertices"] for x in v))
        emit(f,"uint16_t","sc_leaves",(x for v in g["subsectors"] for x in v))
        emit(f,"int16_t","sc_floor",leaf_floors);emit(f,"int16_t","sc_ceiling",leaf_ceilings)
        emit(f,"int16_t","sc_walls",(x for w in walls for x in w))
        emit(f,"uint8_t","sc_textures",(x for a in assets for x in a))
        emit(f,"uint8_t","sc_sky",(x for row in sky for x in row))
        emit(f,"int16_t","sc_scalers",(x for row in rs for x in row))
        emit(f,"uint8_t","sc_indices",idx)
        emit(f,"int16_t","sc_poses",(x for p in poses for x in p))
        emit(f,"int16_t","sc_trig",(v for a in range(360) for v in (round(math.cos(math.radians(90-a))*16384),round(math.sin(math.radians(90-a))*16384))))
        emit(f,"uint16_t","sc_palette",((round(b*7/255)<<9)|(round(g*7/255)<<5)|(round(r*7/255)<<1) for r,g,b in r.palette))
    info={"fixture":fixture,"asymmetric":asymmetric,"map":k,"poses":len(poses),"zigzag_poses":0 if fixture else len(poses)-min(4,len(spawn)),"packed_textures":len(assets),"packed_texture_bytes":asset_bytes*len(assets),"art_pair":art,"dread_profile":dread,"visibility_bytes":len(dag),"scale_rows":len(rs),"scale_table_bytes":144*len(rs)+2048,"calibrated_scalers":bool(fsc),"source_derived_scalers":source_scale,"reference_rom_required_at_runtime":False}
    print("SCENE "+json.dumps(info),flush=True);return info
def main():
    p=argparse.ArgumentParser();p.add_argument("out",type=P);p.add_argument("--wad",type=P);p.add_argument("--fsc",type=P);p.add_argument("--source-scale",action="store_true");p.add_argument("--asymmetric",action="store_true");p.add_argument("--art",action="store_true");p.add_argument("--dread-art",action="store_true");a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    fixture=not a.wad;wad=a.wad or a.out/"fixture.wad"
    if a.asymmetric:
        assert fixture,"asymmetric fixture cannot use external WAD"
        from asymmetric_fixture import make
        make(wad)
    elif fixture:make_fixture(wad)
    assert not ((a.art or a.dread_art) and fixture),"art mode needs actual WAD materials"
    info=export(WAD(wad),"E1M1",a.out/"scene.h",a.fsc,fixture,a.asymmetric,a.art or a.dread_art,a.dread_art,a.source_scale)
    (a.out/"scene.json").write_text(json.dumps(info,indent=2))
if __name__=="__main__":main()
