"""R01 emulator verification: compare actual 68000 framebuffer hash and VRAM
against host execution of the same independent engine. No video files published.
"""
import argparse,ctypes as C,hashlib,json,pathlib,struct,sys,os
P=pathlib.Path
U8=C.c_uint8;U32=C.c_uint32
class Info(C.Structure):
    _fields_=[("path",C.c_char_p),("data",C.c_void_p),("size",C.c_size_t),("meta",C.c_char_p)]
class Stats(C.Structure):
    _fields_=[(k,U32) for k in ("candidates","projected","errors","closed","hash","tiles_hash","leaf","tests")]
def fnv(b):
    h=2166136261
    for x in b:h=((h^x)*16777619)&0xffffffff
    return h
def host(out):
    n=json.loads((out/"scene.json").read_text())["poses"]
    lib=C.CDLL(str(out/"demo-host.so"));f=lib.fr_demo_frame
    f.argtypes=[C.c_uint,C.POINTER(Stats),C.POINTER(U8),C.POINTER(U8)];f.restype=C.c_int
    results=[]
    for i in range(n):
        s=Stats();fb=(U8*11520)();tiles=(U8*23040)()
        rc=f(i,C.byref(s),fb,tiles);assert rc==0,(i,rc)
        row={k:getattr(s,k) for k,_ in s._fields_}
        assert row["hash"]==fnv(fb) and row["tiles_hash"]==fnv(tiles)
        # independent tile decoding from logical buffer
        expected=bytes(fb[(x//2)*144+(x&1)+2*(y//2)] for ty in range(18) for tx in range(40) for ry in range(8) for k in range(4) for x,y in [(tx*4+k,ty*8+ry)])
        assert expected==bytes(tiles)
        results.append(row)
    return results
def emulate(core,out,mode,expected,maxframes):
    lib=C.CDLL(str(core));cb=[];frames=0
    def env(cmd,p):
        if cmd==3:C.cast(p,C.POINTER(C.c_bool))[0]=True;return True
        if cmd==10:return C.cast(p,C.POINTER(C.c_int))[0] in (0,1,2)
        return False
    for name,typ,fn in [
        ("environment",C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p),env),
        ("video_refresh",C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t),lambda *a:None),
        ("audio_sample",C.CFUNCTYPE(None,C.c_int16,C.c_int16),lambda *a:None),
        ("audio_sample_batch",C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t),lambda d,n:n),
        ("input_poll",C.CFUNCTYPE(None),lambda:None),
        ("input_state",C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint),lambda *a:0)]:
        c=typ(fn);cb.append(c);getattr(lib,"retro_set_"+name)(c)
    lib.retro_init();rompath=(out/"FERRET-MD-R01.bin").resolve();rom=rompath.read_bytes();buf=C.create_string_buffer(rom)
    # Use the real absolute filename, matching successful Alpha2 capture.
    info=Info(os.fsencode(rompath),C.cast(buf,C.c_void_p),len(rom),None)
    lib.retro_load_game.argtypes=[C.POINTER(Info)];lib.retro_load_game.restype=C.c_bool
    if not lib.retro_load_game(C.byref(info)):
        lib.retro_deinit()
        return {"pass":False,"fatal":"retro_load_game rejected absolute path","mode":mode,"rom_bytes":len(rom),"header":rom[0x100:0x110].decode("ascii",errors="replace"),"expected_poses":len(expected)}
    lib.retro_set_controller_port_device(0,1)
    C.c_uint.in_dll(lib,"retro_sram_block").value=mode
    C.c_uint.in_dll(lib,"retro_trace_active").value=1
    lib.retro_get_memory_data.argtypes=[C.c_uint];lib.retro_get_memory_data.restype=C.c_void_p
    ptr=lib.retro_get_memory_data(2);assert ptr
    lib.retro_dread_vram_word.argtypes=[C.c_uint];lib.retro_dread_vram_word.restype=C.c_uint
    lib.retro_trace_sraminfo.argtypes=[C.c_uint];lib.retro_trace_sraminfo.restype=C.c_uint
    lib.retro_research_cpu.argtypes=[C.c_uint];lib.retro_research_cpu.restype=C.c_uint
    def mailbox():
        b=C.string_at(ptr+0xf000,68)
        b=b"".join(b[i:i+2][::-1] for i in range(0,len(b),2))
        return struct.unpack(">17I",b)
    checks=[];seen=set();last=0;last_seq=0;fatal=None
    try:
        for frames in range(1,maxframes+1):
            lib.retro_run();m=mailbox()
            if m[0]!=0x46523031:continue
            if m[2]&0x80000000:fatal={"stage":m[2],"exception_frame":C.string_at(ptr+0xf0a0,52).hex()};break
            if m[1]==0 or m[1]==last_seq:continue
            i=m[4]
            if i>=len(expected):fatal="invalid pose";break
            if i in seen:continue
            # If another DMA has started, skip this sample rather than
            # attribute a partially updated VRAM to the previous pose.
            if m[2]==4:continue
            last_seq=m[1]
            e=expected[i]
            vram=bytearray()
            for a in range(0x20,0x20+23040,2):vram.extend((lib.retro_dread_vram_word(a)&65535).to_bytes(2,"big"))
            h=fnv(vram);ok=m[5]==e["hash"] and m[6]==e["tiles_hash"] and h==e["tiles_hash"] and m[7]==e["candidates"] and m[8]==e["projected"] and m[9]==e["errors"] and m[10]==e["closed"] and m[12]==0
            if m[11]!=0:ok=False # mandatory WRAM baseline, all cartridge configurations
            checks.append({"pose":i,"frame":frames,"elapsed_video_frames":frames-last,"match":ok,"fb":m[5],"expected_fb":e["hash"],"tile":m[6],"vram":h,"expected_tile":e["tiles_hash"],"sram":m[11],"errors":m[9],"candidates":m[7],"projected":m[8]})
            seen.add(i);last=frames
            if len(seen)==len(expected):break
        m=mailbox()
        ndma=C.c_uint.in_dll(lib,"retro_trace_dmas").value
        d=(C.c_uint*(32768*6)).in_dll(lib,"retro_trace_dma")
        events=[list(d[i*6:i*6+6]) for i in range(min(ndma,32768))]
        pubs=[e for e in events if e[3]==0x20 and e[4]==11520]
        result={"mode":mode,"video_frames":frames,"checks":checks,"matched":sum(x["match"] for x in checks),"expected_poses":len(expected),"fatal":fatal,"last_mailbox":list(m),"sram_mapping":[lib.retro_trace_sraminfo(i) for i in range(6)],"dma_publications":len(pubs),"dma_sources":sorted(set(e[2] for e in pubs)),"emulated_only":True}
        # DMA must actually have occurred, not just matching the host plan.
        result["pass"]=len(checks)==len(expected) and all(x["match"] for x in checks) and len(pubs)>=len(expected) and fatal is None
        return result
    finally:lib.retro_unload_game();lib.retro_deinit()
def main():
    p=argparse.ArgumentParser();p.add_argument("out",type=P);p.add_argument("core",type=P);p.add_argument("report",type=P);p.add_argument("--maxframes",type=int,default=3600);p.add_argument("--mode",type=int,choices=(0,1,2),required=True);a=p.parse_args()
    expected=host(a.out)
    r=emulate(a.core,a.out,a.mode,expected,a.maxframes)
    a.report.write_text(json.dumps(r,indent=2));print("EMULATOR "+json.dumps(r),flush=True)
    if not r["pass"]:sys.exit(2)
if __name__=="__main__":main()
