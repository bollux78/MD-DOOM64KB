"""Private exact R09 timing in the same Genesis Plus GX clock as Alpha2.
Hook observes existing mailbox stages before each instruction, no ROM changes
except optional forcing of the already qualified SRAM staging path.
"""
import ctypes as C, pathlib, sys, json, os, statistics
from test_demo import Info,host,fnv
P=pathlib.Path
def patch(root):
    p=root/"core/m68k/m68kcpu.c";s=p.read_text()
    decl=r"""
unsigned int retro_r09_active,retro_r09_count,retro_r09_overflow;
unsigned int retro_r09_rows[256][16];
static unsigned int retro_r09_stage;
static unsigned int *retro_r09_row;
static void retro_r09_hook(void){
 if(!retro_r09_active || m68ki_read_32(0xfff000)!=0x46523031)return;
 unsigned int st=m68ki_read_32(0xfff008);
 if(st==retro_r09_stage)return;
 retro_r09_stage=st;
 if(st==3){
   if(retro_r09_row){retro_r09_row[6]=retro_trace_frame;retro_r09_row[7]=m68k.cycles;}
   if(retro_r09_count==256){retro_r09_overflow++;retro_r09_active=0;return;}
   retro_r09_row=retro_r09_rows[retro_r09_count++];
   retro_r09_row[0]=retro_trace_frame;retro_r09_row[1]=m68k.cycles;
 }
 if(!retro_r09_row)return;
 unsigned int *r=retro_r09_row;
 if(st==4){r[2]=retro_trace_frame;r[3]=m68k.cycles;}
 if(st==5){
   r[4]=retro_trace_frame;r[5]=m68k.cycles;
   r[8]=m68ki_read_32(0xfff010);r[9]=m68ki_read_32(0xfff01c);
   r[10]=m68ki_read_32(0xfff020);r[11]=m68ki_read_32(0xfff024);
   r[12]=m68ki_read_32(0xfff02c);r[13]=m68ki_read_32(0xfff00c);
   r[14]=m68ki_read_32(0xfff030);r[15]=m68ki_read_32(0xfff028);
 }
}
"""
    anchor="void m68k_run(unsigned int cycles)"
    hook="    unsigned int research_start = m68k.cycles;"
    assert s.count(anchor)==s.count(hook)==1
    p.write_text(s.replace(anchor,decl+"\n"+anchor).replace(hook,hook+"\n    retro_r09_hook();"))
def run(core,out,mode):
    expected=host(out);lib=C.CDLL(str(core));cb=[]
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
    lib.retro_load_game.argtypes=[C.POINTER(Info)];lib.retro_load_game.restype=C.c_bool
    assert lib.retro_load_game(C.byref(Info(os.fsencode(rompath),C.cast(buf,C.c_void_p),len(rom),None)))
    assert lib.retro_get_region()==0
    lib.retro_set_controller_port_device(0,1)
    var=lambda k:C.c_uint.in_dll(lib,k)
    var("retro_sram_block").value=mode
    var("retro_r09_count").value=0;var("retro_r09_active").value=1;var("retro_trace_active").value=1
    arr=(C.c_uint*(256*16)).in_dll(lib,"retro_r09_rows")
    lib.retro_get_memory_data.argtypes=[C.c_uint];lib.retro_get_memory_data.restype=C.c_void_p
    ram=lib.retro_get_memory_data(2);assert ram
    lib.retro_dread_vram_word.argtypes=[C.c_uint];lib.retro_dread_vram_word.restype=C.c_uint
    seen=set();checks=[]
    try:
        for frames in range(1,16000):
            lib.retro_run()
            import struct
            b=C.string_at(ram+0xf000,68);m=struct.unpack(">17I",b"".join(b[i:i+2][::-1] for i in range(0,68,2)))
            if m[0]==0x46523031:
                assert not m[2]&0x80000000,("fatal",m[2])
                if m[1] and m[2]!=4 and m[4] not in seen and m[4]<len(expected):
                    i=m[4];target=(out/f"expected-tiles-{i}.bin").read_bytes()
                    actual=b"".join((lib.retro_dread_vram_word(a)&65535).to_bytes(2,"little") for a in range(0x20,0x20+23040,2))
                    checks.append({"pose":i,"vram_match":actual==target,"sram_selected":m[11],"sram_detected":m[3],"errors":m[9]})
                    seen.add(i)
            if var("retro_r09_count").value>=13:break
        var("retro_r09_active").value=0
        assert len(seen)==12 and all(c["vram_match"] and not c["errors"] for c in checks),checks
        assert var("retro_r09_count").value>=13 and not var("retro_r09_overflow").value
        clock=53693175;period=896040
        def t(f,c):return f*period+c
        rows=[]
        for i in range(12):
            r=list(arr[16*i:16*(i+1)])
            start,end,pub,nxt=(t(*r[k:k+2]) for k in (0,2,4,6))
            assert start<end<=pub<=nxt,(i,r)
            rows.append({"pose":r[8],"wall_pipeline_ms":(end-start)*1000/clock,"publication_ms":(pub-start)*1000/clock,"frame_ms":(nxt-start)*1000/clock,"candidates":r[9],"projected":r[10],"errors":r[11],"sram_selected":r[12],"sram_detected":r[13],"dma_rc":r[14],"closed":r[15]})
        assert [r["pose"] for r in rows]==list(range(12))
        assert all(not r["errors"] and not r["dma_rc"] for r in rows)
        dma=(C.c_uint*(32768*6)).in_dll(lib,"retro_trace_dma")
        pubs=[list(dma[i*6:i*6+6]) for i in range(min(var("retro_trace_dmas").value,32768)) if dma[i*6+3]==0x20 and dma[i*6+4]==11520]
        result={"mode":mode,"actual_sram_selected":sorted({r["sram_selected"] for r in rows}),"dma_sources":sorted({e[2] for e in pubs}),"rows":rows,"warm_cameras":[dict(rows[2*i+1],camera=label) for i,label in enumerate(("spawn","zigzag-0","zigzag-64","zigzag-128","zigzag-192"))],"vram_checks":checks,"scope":"stage3-to4 includes visibility and wall render, no hashes in FR_BENCH; stage3-to-next-stage3 full diagnostic frame including presentation, no gameplay. SRAM path copies and checks WRAM staging; no claim of accelerated SRAM."}
        return result
    finally:lib.retro_unload_game();lib.retro_deinit()
if __name__=="__main__":
    if sys.argv[1]=="patch":patch(P(sys.argv[2]))
    else:
        core,out,report=map(P,sys.argv[2:5]);mode=int(sys.argv[5])
        r=run(core,out,mode);report.write_text(json.dumps(r,indent=2));print("R09 GPGX "+json.dumps(r),flush=True)
