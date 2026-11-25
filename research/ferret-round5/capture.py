import ctypes as C, hashlib, json, os, pathlib, sys
from collections import Counter
P=pathlib.Path
SHA="47eb717552cd1ed7d5bd11c060582ffd3a50b7753efc5dd3aedbf8e2245ca267"
STAGES=(0x77402,0x7751c,0x7e13e,0x7e14e)
PCS=(0x6f4ae,0x6f606,0x6f646,0x6f6e6,0x6f7ac,0x7dcf2,0x7e0f6,0x7e130,0x7e4f0,0x85f64,0x7e58c,0x7e368,0x7e3e8,0x7e3ea,0x7e444)
def patch(src):
    p=src/"core/m68k/m68kcpu.c"
    s=p.read_text()
    decl=r"""
unsigned int retro_r4_active,retro_r4_scenes,retro_r4_next,retro_r4_bad,retro_r4_n,retro_r4_overflow;
unsigned char retro_r4_ram[16][4][65536],retro_r4_sram[16][4][65536];
unsigned int retro_r4_events[65536][24];
extern unsigned int retro_sram_block;
static void retro_r4_hook(unsigned int pc) {
 if (!retro_r4_active) return;
 unsigned int scene=retro_r4_scenes;
 int stage=-1;
 switch(pc) {case 0x77402:stage=0;break;case 0x7751c:stage=1;break;case 0x7e13e:stage=2;break;case 0x7e14e:stage=3;break;}
 if (stage==0 && retro_r4_next!=0) {retro_r4_bad++;retro_r4_next=0;}
 if (stage>=0 && (unsigned int)stage==retro_r4_next && retro_r4_scenes<16) {
  unsigned int n=retro_r4_scenes;
  for(unsigned int i=0;i<65536;i++) {
   retro_r4_ram[n][stage][i]=m68ki_read_8(0xff0000+i);
   if(!retro_sram_block) retro_r4_sram[n][stage][i]=m68ki_read_8(0x200000+i);
  }
  retro_r4_next++;
  if(stage==3) {retro_r4_next=0;retro_r4_scenes++;}
 }
 if(stage>=0 || pc==0x6f4ae || pc==0x6f606 || pc==0x6f646 || pc==0x6f6e6 || pc==0x6f7ac || pc==0x7dcf2 || pc==0x7e0f6 || pc==0x7e130 || pc==0x7e4f0 || pc==0x85f64 || pc==0x7e58c || pc==0x7e368 || pc==0x7e3e8 || pc==0x7e3ea || pc==0x7e444 || pc==0x82a42 || pc==0x82a48 || pc==0x82bf4 || pc==0x82bfa || pc==0x7731e || pc==0x773fc || pc==0x86c70) {
  if(retro_r4_n>=65536) {retro_r4_overflow++;return;}
  unsigned int *e=retro_r4_events[retro_r4_n++];
  e[0]=pc;e[1]=scene;e[2]=retro_trace_frame;e[3]=m68k.cycles;
  for(unsigned int i=0;i<16;i++) e[4+i]=m68k_get_reg((m68k_register_t)i);
  e[20]=m68k_get_reg(M68K_REG_SR);
  e[21]=m68ki_read_32(0xff31c6);e[22]=m68ki_read_32(0xff1008);e[23]=m68ki_read_32(0xff2c72);
 }
 if(retro_r4_scenes==16)retro_r4_active=0;
}
"""
    anchor="void m68k_run(unsigned int cycles)"
    hook="    if (retro_phase2_active) {"
    assert s.count(anchor)==1 and s.count(hook)==1
    p.write_text(s.replace(anchor,decl+"\n"+anchor).replace(hook,"    retro_r4_hook((REG_PC - 2) & 0xffffff);\n"+hook))
def locate():
    # Search only known ROM filenames (not arbitrary private files); never print paths.
    roots=[P.home()/"Projetos",P.home()/"Downloads",P.home()/"Games",P.home()/"ROMs",P.home()/"roms",P.home()/".local/share/ferret-research"]
    if os.environ.get("FERRET_ROM"):
        roots.insert(0,P(os.environ["FERRET_ROM"]))
    def verified(p):
        try:return p.is_file() and p.stat().st_size==1441792 and hashlib.sha256(p.read_bytes()).hexdigest()==SHA
        except OSError:return False
    for root in roots:
        if root.is_file() and verified(root):return root
        if not root.is_dir():continue
        for directory,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if d not in (".git","node_modules",".cache",".venv")]
            for name in files:
                if name.lower().endswith((".bin",".md",".gen",".smd",".rom")) and ("alpha2" in name.lower() or "ferret" in name.lower()):
                    p=P(directory)/name
                    if verified(p):return p
    return None
def capture(core,rom,out,mode,pose):
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==SHA
    class Info(C.Structure):
        _fields_=[("path",C.c_char_p),("data",C.c_void_p),("size",C.c_size_t),("meta",C.c_char_p)]
    lib=C.CDLL(str(core))
    pad=set()
    def env(cmd,p):
        if cmd==3:C.cast(p,C.POINTER(C.c_bool))[0]=True;return True
        if cmd==10:return C.cast(p,C.POINTER(C.c_int))[0] in (0,1,2)
        return False
    callbacks=[]
    for name,typ,fn in [
        ("environment",C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p),env),
        ("video_refresh",C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t),lambda *a:None),
        ("audio_sample",C.CFUNCTYPE(None,C.c_int16,C.c_int16),lambda *a:None),
        ("audio_sample_batch",C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t),lambda d,n:n),
        ("input_poll",C.CFUNCTYPE(None),lambda:None),
        ("input_state",C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint),lambda port,dev,index,b:int(port==0 and dev==1 and b in pad))]:
        cb=typ(fn);callbacks.append(cb);getattr(lib,"retro_set_"+name)(cb)
    lib.retro_init(); raw=C.create_string_buffer(rom.read_bytes())
    lib.retro_load_game.argtypes=[C.POINTER(Info)];lib.retro_load_game.restype=C.c_bool
    assert lib.retro_load_game(C.byref(Info(os.fsencode(rom),C.cast(raw,C.c_void_p),len(raw)-1,None)))
    assert lib.retro_get_region()==0
    lib.retro_set_controller_port_device(0,1)
    def var(name):return C.c_uint.in_dll(lib,name)
    var("retro_sram_block").value=mode
    lib.retro_get_memory_data.argtypes=[C.c_uint];lib.retro_get_memory_data.restype=C.c_void_p
    ram=lib.retro_get_memory_data(2)
    assert ram
    def put(off,val,n):
        b=(val&((1<<(8*n))-1)).to_bytes(n,"big")
        C.memmove(ram+off,b"".join(b[i:i+2][::-1] for i in range(0,n,2)),n)
    def step(n,b=None):
        pad.clear()
        if b is not None:pad.add(b)
        for _ in range(n):lib.retro_run()
    try:
        for n,b in [(120,None),(20,3),(40,None),(20,8),(40,None),(20,8),(60,None)]:step(n,b)
        # Poses from the original research's capture_control_flow.py. Fresh game per case.
        # Debug camera repositioning modifies live state; it is not a normal gameplay route.
        poses={"door":(1480,960,-40,0),"stairs":(64,224,-144,0),"patio":(1400,450,16,0)}
        for angle in (0,64,128,192):poses["zigzag"+str(angle)]=(2980,170,-16,angle)
        if pose in poses:
            x,y,z,angle=poses[pose]
            for off,val,n in [(0x31e6,x*65536,4),(0x31e2,y*65536,4),(0x31de,z*65536,4),(0x31da,0,4),(0x31d6,0,4),(0x31d2,0,4),(0x31ca,angle<<8,2),(0x31cc,angle,2),(0x1a32,x*8,2),(0x1a30,y*8,2),(0x1a2e,z,2),(0x31c6,0,4)]:put(off,val,n)
        # Activate stage capture before the move/first full frame; no seed pose from old dumps.
        var("retro_r4_active").value=1
        var("retro_research_active").value=1
        var("retro_trace_active").value=1
        for i in range(300):
            b=8 if pose=="door" else (6 if pose=="walk" and i<120 else 4 if pose=="walk" else None)
            step(1,b)
        var("retro_research_active").value=0
        var("retro_trace_active").value=0
        var("retro_r4_active").value=0
        scenes=var("retro_r4_scenes").value
        count=var("retro_r4_n").value
        bad=var("retro_r4_bad").value;overflow=var("retro_r4_overflow").value
        memory=bytes((C.c_ubyte*(16*4*65536)).in_dll(lib,"retro_r4_ram"))
        events=(C.c_uint*(65536*24)).in_dll(lib,"retro_r4_events")
        hits=Counter(hex(events[i*24]) for i in range(count))
        out.mkdir(parents=True,exist_ok=True)
        (out/"wram.bin").write_bytes(memory[:scenes*4*65536])
        if mode==0:(out/"sram.bin").write_bytes(bytes((C.c_ubyte*(16*4*65536)).in_dll(lib,"retro_r4_sram"))[:scenes*4*65536])
        (out/"events.json").write_text(json.dumps([list(events[i*24:(i+1)*24]) for i in range(count)]))
        def frame(i,j):
            ram=memory[(i*4+j)*65536:(i*4+j+1)*65536]
            addr=int.from_bytes(ram[0x2c72:0x2c76],"big")&0xffffff
            if not 0xff0000<=addr<=0x1000000-11520:raise ValueError("Unexpected framebuffer pointer")
            return ram[addr-0xff0000:addr-0xff0000+11520]
        changes=[sum(a!=b for a,b in zip(frame(i,2),frame(i,3))) for i in range(scenes)]
        # Instruction attribution excludes interrupts charged within another opcode only insofar
        # as the existing core profiler does. Not pure CPU-exclusive cycle estimates.
        hits_arr=(C.c_uint*1048576).in_dll(lib,"retro_research_hits")
        cycle_arr=(C.c_ulonglong*1048576).in_dll(lib,"retro_research_cycles")
        ranges={"scalers":[(0x21b1c,0x6d4ae)],"sprite_stage":[(0x6f4ae,0x6f8a0)],"wall_kernels":[(0x6f8a0,0x76ec2)],"wall_projection":[(0x770b6,0x77402)],"visibility":[(0x77402,0x7751e)],"wall_dispatch":[(0x7751e,0x77550)],"conversion":[(0x7e368,0x7e446)]}
        # Ranges are exploratory bins, not exact exclusive subroutine timings.
        bins={k:{"hits":sum(sum(hits_arr[a//2:b//2]) for a,b in rr),"master_cycles":sum(sum(cycle_arr[a//2:b//2]) for a,b in rr)} for k,rr in ranges.items()}
        ndma=var("retro_trace_dmas").value
        dma=(C.c_uint*(32768*6)).in_dll(lib,"retro_trace_dma")
        published=sum(dma[i*6+3]==0xe100 and dma[i*6+4]==1152 for i in range(min(ndma,32768)))
        coords=[]
        for i in range(scenes):
            start=i*4*65536
            q=memory[start:start+65536]
            w=lambda x:int.from_bytes(q[x:x+2],"big",signed=True)
            L=lambda x:int.from_bytes(q[x:x+4],"big")
            coords.append([w(0x1a32),w(0x1a30),w(0x1a2e),w(0x31cc),(L(0x31c6)-L(0x1008))//14,list(q[0x1b85:0x1b8a])])
        result={"sram_block":mode,"pose":pose,"video_frames":300,"publication_count":published,"fps":published*53693175/896040/300,"profile_bins":bins,"projection_calls":hits_arr[0x770b6//2],"kernel_calls":hits_arr[0x7731e//2]+hits_arr[0x773fc//2],"render_calls":hits_arr[0x77402//2],"coords_and_conditions":coords,"scenes":scenes,"sequence_resets":bad,"event_overflow":overflow,"event_counts":dict(hits),"sprite_stage_changed_bytes":changes,"complete":scenes==16 and not overflow,"rom_sha256":SHA,"core_sha256":hashlib.sha256(core.read_bytes()).hexdigest()}
        (out/"summary.json").write_text(json.dumps(result,indent=2))
        print(json.dumps(result))
        if not result["complete"]:sys.exit(2)
    finally:
        lib.retro_unload_game();lib.retro_deinit()
if __name__=="__main__":
    if sys.argv[1]=="patch":patch(P(sys.argv[2]))
    elif sys.argv[1]=="locate":
        p=locate()
        if p is None:sys.exit(3)
        P(sys.argv[2]).write_text(str(p))
    elif sys.argv[1]=="capture":capture(P(sys.argv[2]),P(sys.argv[3]),P(sys.argv[4]),int(sys.argv[5]),sys.argv[6])
