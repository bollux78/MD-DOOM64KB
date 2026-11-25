"""Native sprite regression: decode reference resource data at the test boundary only."""
import ctypes as C, pathlib, tempfile, sys, json, importlib.util, hashlib
from test_native import Frame, Asset, U8,U16,I16,I32,U32, W,H,load_native,diff
P=pathlib.Path
class Span(C.Structure):_fields_=[("offset",I32),("lo",I16),("hi",I16)]
class Column(C.Structure):_fields_=[("first",U32),("count",U32)]
class Sprite(C.Structure):_fields_=[("width",I32),("origin",I32),("pixels",Asset),("columns",C.POINTER(Column)),("spans",C.POINTER(Span)),("span_count",U32)]
class Part(C.Structure):_fields_=[("sprite",C.POINTER(Sprite)),("dx",I32),("dy",I32)]
class Stats(C.Structure):_fields_=[(k,U32) for k in ("writes","tags","projected","overflow")]
class Order(C.Structure):_fields_=[("id",U32),("key",I32)]
def bind(lib):
    common=[I32,I32,I32,U16,C.POINTER(I16),C.POINTER(I16),C.POINTER(Stats)]
    lib.fr_sprite.argtypes=[C.POINTER(Frame),C.POINTER(Sprite)]+common;lib.fr_sprite.restype=C.c_int
    lib.fr_composite.argtypes=[C.POINTER(Frame),C.POINTER(Part),U32]+common;lib.fr_composite.restype=C.c_int
    lib.fr_sprite_order.argtypes=[C.POINTER(Order),U32];lib.fr_sprite_order.restype=None
    lib.fr_door_phase.argtypes=[I32,I32,I32,C.POINTER(I32),C.POINTER(I32)];lib.fr_door_phase.restype=C.c_int
    lib.fr_door_lerp.argtypes=[I32,I32,I32];lib.fr_door_lerp.restype=I32
def synthetic(lib):
    # No ROM, two independently constructed simple resources and a composite.
    table=(I16*(2048*H))();factor=(I16*2048)(*([16384]*2048))
    c=(Column*16)(*[Column(i,1) for i in range(16)])
    p=(Span*16)(*[Span(0,-256,256) for _ in range(16)])
    a=(U8*1024)(*([0x22]*1024));b=(U8*1024)(*([0x66]*1024))
    s=Sprite(16,8,Asset(a,1024,512),c,p,16);t=Sprite(16,8,Asset(b,1024,512),c,p,16)
    f=Frame();lib.fr_begin(C.byref(f));f.depth[79]=65535
    st=Stats()
    parts=(Part*2)(Part(C.pointer(s),0,0),Part(C.pointer(t),-16,0))
    assert lib.fr_composite(C.byref(f),parts,2,0,640,0,17,factor,table,C.byref(st))==0
    assert st.projected==2 and st.writes>0 and 0x22 in f.pixels and 0x66 in f.pixels
    assert f.owner[79]==0 and all(f.pixels[(79//2)*144+1+2*y]==0 for y in range(H))
    return {"parts":st.projected,"writes":st.writes,"tags":st.tags,"occlusion_pass":True,"original_rom_required":False}
def main():
    root,romfile,library,out=map(P,sys.argv[1:]);rom=romfile.read_bytes()
    assert hashlib.sha256(rom).hexdigest()=="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
    lib=load_native(library);bind(lib);custom=synthetic(lib);print("SPRITE CUSTOM "+json.dumps(custom),flush=True)
    spec=importlib.util.spec_from_file_location("r5",P(__file__).parent.parent/"ferret-round5"/"compare.py")
    r5=importlib.util.module_from_spec(spec);spec.loader.exec_module(r5)
    with tempfile.TemporaryDirectory() as t:
        r5.load_models(root,P(t))
        from visibility import Memory
        class Bus(Memory):
            def __init__(self,rom,ram,sram=None):
                super().__init__(rom,ram)
                self.sram=sram
            def get(self,a,n):
                a &= 0xffffff
                if self.sram is not None and 0x200000<=a and a+n<=0x210000:
                    return self.sram[a-0x200000:a-0x200000+n]
                return super().get(a,n)
        from ferret_contract import scaler,s16,u16,i16,u32,sprite_column
        from ferret_stage import actor_list,s32,door_step
        table=(I16*(2048*H))();factors=(I16*2048)()
        for i in range((0x500000//81>>5)+1):
            factor,offsets=scaler(rom,i*32);factors[i]=factor;table[i*H:(i+1)*H]=offsets
        rombuf=(U8*len(rom)).from_buffer_copy(rom)
        cache={}
        def decode(r):
            if r not in cache:
                w=u16(rom,r);assert not u32(rom,r+4) and 0<w<32768
                cols=[];spans=[]
                for i in range(w):
                    v=sprite_column(rom,r,i);cols.append(Column(len(spans),len(v)));spans.extend(Span(*x) for x in v)
                ca=(Column*len(cols))(*cols);pa=(Span*len(spans))(*spans)
                cache[r]=(Sprite(w,i16(rom,r+2),Asset(rombuf,len(rom),r),ca,pa,len(spans)),ca,pa)
            return cache[r][0]
        total={k:0 for k in ("frames","pass","callbacks","composites","projected","writes","tag_columns","overflow","transform_diff","order_diff","pixel_diff","tag_diff","errors")}
        cases={}
        for rnd,run in [(4,45645383728),(5,45657627918)]:
            for folder in sorted((root/f"round{rnd}"/str(run)).glob("sram*-*")):
                if not (folder/"summary.json").exists():continue
                n=json.loads((folder/"summary.json").read_text())["scenes"];raw=(folder/"wram.bin").read_bytes()
                sram=(folder/"sram.bin").read_bytes() if (folder/"sram.bin").exists() else None
                assert len(raw)==n*4*65536 and (sram is None or len(sram)==len(raw))
                def snapshot(i,j):
                    off=(i*4+j)*65536
                    return Bus(rom,raw[off:off+65536],None if sram is None else sram[off:off+65536])
                row={k:0 for k in total}
                for i in range(n):
                    m=snapshot(i,2);ref=snapshot(i,3)
                    f=Frame();base=m.u32(0xff2c72);f.pixels[:]=m.get(base,W*H)
                    f.depth[:]=[m.u16(0xff1524+8*x) for x in range(W)];f.owner[:]=[m.u16(0xff1526+8*x) for x in range(W)]
                    txz={};order=[]
                    td=cb=err=0
                    for a in actor_list(m):
                        cell=m.u32(a+8)
                        if not cell or m.u16(cell+8)!=m.u16(0xff1a28):continue
                        dx=s16(m.s16(a+34)-m.s16(0xff1a32));dy=s16(m.s16(a+36)-m.s16(0xff1a30))
                        tx,tz=I32(),I32()
                        lib.fr_transform(0,0,-dx,-dy,m.s16(0xff1a2c),m.s16(0xff1a2a),C.byref(tx),C.byref(tz))
                        txz[a]=(tx.value,tz.value)
                        td+=int(tx.value!=ref.s16(a+40) or tz.value!=ref.s16(a+42))
                        order.append(Order(a,s32(((tz.value&65535)<<16)|m.u16(a+44))))
                    ar=(Order*len(order))(*order);lib.fr_sprite_order(ar,len(ar))
                    actual=[o.id for o in ar];od=int(actual!=actor_list(ref))
                    for a in reversed(actual):
                        r=m.u32(a+30)&0xffffff
                        if not r:continue
                        tx,tz=txz[a]
                        if m.u8(a+14) and -256<=tx<=256 and -256<=tz<=256:cb+=1;continue
                        delta=s16((s16(m.s16(0xff1a2e)-m.s16(m.u32(a+8)+12))<<6)-m.s16(a+38))>>7
                        st=Stats()
                        if u32(rom,r+4):
                            parts=[]
                            for k in range(256):
                                p=r+8*k;child=u32(rom,p+4)&0xffffff
                                if not child:break
                                parts.append(Part(C.pointer(decode(child)),i16(rom,p),i16(rom,p+2)))
                            else:raise ValueError("unterminated composite")
                            arr=(Part*len(parts))(*parts);row["composites"]+=1
                            ret=lib.fr_composite(C.byref(f),arr,len(arr),tx,tz,delta,m.u16(a+50),factors,table,C.byref(st))
                        else:
                            ret=lib.fr_sprite(C.byref(f),C.byref(decode(r)),tx,tz,delta,m.u16(a+50),factors,table,C.byref(st))
                        err+=int(ret<0)
                        for k,v in (("writes",st.writes),("projected",st.projected),("tag_columns",st.tags),("overflow",st.overflow)):row[k]+=v
                    pd=diff(f.pixels,ref.get(ref.u32(0xff2c72),W*H));tag=diff(f.owner,[ref.u16(0xff1526+8*x) for x in range(W)])
                    row["frames"]+=1;row["pass"]+=int(not(td or od or cb or err or pd or tag))
                    for k,v in (("transform_diff",td),("order_diff",od),("callbacks",cb),("errors",err),("pixel_diff",pd),("tag_diff",tag)):row[k]+=v
                cases[f"r{rnd}/{folder.name}"]=row
                for k,v in row.items():total[k]+=v
                print(json.dumps({"case":f"r{rnd}/{folder.name}",**row}),flush=True)
        door={"phase_cases":0,"phase_diff":0,"lerp_cases":0,"lerp_diff":0}
        for phase in (0,1,4096,8192,16383,16384):
            for speed in (-1024,-1,0,1,1024):
                for ticks in (0,1,4,16):
                    a,b=I32(),I32();ret=lib.fr_door_phase(phase,speed,ticks,C.byref(a),C.byref(b))
                    ex=door_step(phase,speed,ticks,1)
                    door["phase_cases"]+=1;door["phase_diff"]+=int((a.value,b.value,ret)!=ex[:3])
            for a,b in ((-1000,1000),(1000,-1000),(0,1),(-32768,32767)):
                door["lerp_cases"]+=1;door["lerp_diff"]+=int(lib.fr_door_lerp(a,b,phase)!=s16(a+((b-a)*phase>>14)))
    out.write_text(json.dumps({"custom":custom,"totals":total,"door":door,"cases":cases},indent=2))
    print("SPRITE TOTALS "+json.dumps(total),flush=True);print("DOOR MODEL "+json.dumps(door),flush=True)
    if total["frames"]!=352 or total["pass"]!=352 or door["phase_diff"] or door["lerp_diff"]:sys.exit(2)
if __name__=="__main__":main()
