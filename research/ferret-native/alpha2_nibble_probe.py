"""Independent Alpha2 profile on pinned Genesis Plus GX.
Authentic ROM only on runner. Counts list records, actual project/dispatch calls,
scaler entries and CPU VDP writes, plus disjoint PC-region cycle attribution.
No original code/assets exported. Camera coordinates from Claudio's contract.
"""
import ctypes as C, json, os, pathlib, sys, statistics, hashlib
P=pathlib.Path
sys.path.insert(0,str(P(__file__).resolve().parent.parent/"ferret-round5"))
from capture import locate,SHA
from test_demo import Info
COLS=("start_frame","start_cycle","x8","y8","z","angle","cell","records","project","after_transform","dispatch_linear","dispatch_perspective","dispatch_width","wall_scaler_entries","sprite_scaler_entries","visibility_cycles","projection_cycles","kernel_cycles","wall_scaler_cycles","sprite_cycles","sprite_scaler_cycles","conversion_cycles","other_cycles","list_complete","walls_end_frame","walls_end_cycle","sprites_end_frame","sprites_end_cycle","direct_first_frame","direct_first_cycle","direct_last_frame","direct_last_cycle","direct_words","direct_calls","sram_convert_calls","bad_list","render_end_frame","render_end_cycle","total_instructions","scaler_instructions","wall_scale_pixels","wall_scale_master_cycles","wall_scale_dbf","wall_scale_jmp","wall_scale_nop","wall_scale_other","wall_scale_entries","wall_scale_entry_row_sum")
def patch(root):
    p=root/"core/m68k/m68kcpu.c";s=p.read_text()
    decl=r"""
/* Werk independent profile: aggregate only, no ROM bytes in report. */
unsigned int retro_ap_active,retro_ap_n,retro_ap_overflow,retro_ap_direct;
unsigned int retro_ap_rows[256][48],retro_ap_prev_pc;
static unsigned int *retro_ap_row;
static unsigned int retro_ap_phase;
static unsigned char wall_written[65536], wall_mask[11520], wall_value[11520];
unsigned char retro_packed_mask[11520], retro_packed_value[11520];
extern unsigned int retro_research_captured;
static void retro_ap_before(unsigned int pc) {
 if(!retro_ap_active)return;
 if(pc==0x77402){
   memset(wall_written,0,sizeof(wall_written));
   if(retro_ap_row){retro_ap_row[36]=retro_trace_frame;retro_ap_row[37]=m68k.cycles;}
   if(retro_ap_n>=256){retro_ap_overflow++;retro_ap_active=0;retro_ap_row=0;return;}
   retro_ap_row=retro_ap_rows[retro_ap_n++];
   unsigned int *r=retro_ap_row;
   r[0]=retro_trace_frame;r[1]=m68k.cycles;
   r[2]=m68ki_read_16(0xff1a32);r[3]=m68ki_read_16(0xff1a30);
   r[4]=m68ki_read_16(0xff1a2e);r[5]=m68ki_read_16(0xff31cc);
   r[6]=(m68ki_read_32(0xff31c6)-m68ki_read_32(0xff1008))/14;
   retro_ap_phase=1;retro_ap_direct=0;
 }
 unsigned int *r=retro_ap_row;
 if(!r)return;
 if(pc==0x7751c){
   unsigned int n=0;
   while(n<598 && m68ki_read_16(0xff01e4+6*n)!=0xffff)n++;
   r[7]=n;r[23]=1;r[35]=(n==598);retro_ap_phase=2;
 }
 if(pc==0x770b6)r[8]++;
 if(pc==0x7716e)r[9]++;
 if(pc==0x7731e || pc==0x773fc){r[pc==0x7731e?10:11]++;r[12]+=m68ki_read_16(0xff0018);}
 if(pc==0x7e368 && !retro_research_captured){
   memcpy(retro_packed_mask,wall_mask,11520);
   memcpy(retro_packed_value,wall_value,11520);
 }
 if(pc==0x7e13e){
   unsigned int base=m68ki_read_32(0xff2c72)&65535;
   for(unsigned int i=0;i<11520;i++){
     wall_mask[i]=wall_written[(base+i)&65535];
     wall_value[i]=m68ki_read_8(0xff0000|((base+i)&65535));
   }
 r[24]=retro_trace_frame;r[25]=m68k.cycles;retro_ap_phase=3;}
 if(pc==0x7e14e){r[26]=retro_trace_frame;r[27]=m68k.cycles;retro_ap_phase=4;}
 if(pc==0x7e368){retro_ap_direct=1;r[33]++;}
 if(pc==0x7e3e8)retro_ap_direct=0;
 if(pc==0x7e3ea)r[34]++;
 if(pc>=0x21b1c&&pc<0x6d4ae &&
    !(retro_ap_prev_pc>=0x21b1c&&retro_ap_prev_pc<0x6d4ae)){
    if(retro_ap_phase==2)r[13]++;
    else if(retro_ap_phase==3)r[14]++;
 }
 if(pc>=0x4b992 && pc<0x6d4ae && !(retro_ap_prev_pc>=0x4b992 && retro_ap_prev_pc<0x6d4ae)){
    r[46]++;r[47]+=((pc-0x4b992)%868)/12;
 }
 retro_ap_prev_pc=pc;
}
static void retro_ap_after(unsigned int pc,unsigned int cycles) {
 if(!retro_ap_active||!retro_ap_row)return;
 unsigned int *r=retro_ap_row;unsigned int bin=22;
 r[38]++;
 if(pc>=0x4b992 && pc<0x6d4ae){
    unsigned int off=(pc-0x4b992)%868;
    r[41]+=cycles;
    if(off<864 && off%12==8){
   r[40]++;
   unsigned int op=m68ki_read_16(pc), mode=(op>>6)&7, reg=(op>>9)&7;
   if((op>>12)==1 && (mode==2 || mode==3)){
     unsigned int addr=m68k_get_reg((m68k_register_t)(8+reg))-(mode==3?(reg==7?2:1):0);
     if((addr&0xff0000)==0xff0000)wall_written[addr&65535]=1;
   }
 }
    else if(off<864 && off%12==0)r[42]++;
    else if(off==864 || off%12==4)r[43]++;
    else if(off==866 || off%12==6)r[44]++;
    else r[45]++;
 }
 if(pc>=0x21b1c&&pc<0x6d4ae){
    r[39]++;
    if(retro_ap_phase==2)bin=18;else if(retro_ap_phase==3)bin=20;
 }else if(pc>=0x77402&&pc<0x7751e)bin=15;
 else if(pc>=0x770b6&&pc<0x77402)bin=16;
 else if(pc>=0x6f8a0&&pc<0x76ec2)bin=17;
 else if(pc>=0x6f4ae&&pc<0x6f8a0)bin=19;
 else if(pc>=0x7e368&&pc<0x7e446)bin=21;
 r[bin]+=cycles;
}
void retro_ap_vdp_word(void){
 if(!retro_ap_active||!retro_ap_direct||!retro_ap_row)return;
 unsigned int *r=retro_ap_row;
 if(!r[32]){r[28]=retro_trace_frame;r[29]=m68k.cycles;}
 r[30]=retro_trace_frame;r[31]=m68k.cycles;r[32]++;
}
"""
    anchor="void m68k_run(unsigned int cycles)"
    before="    unsigned int research_start = m68k.cycles;"
    after="    /* Execute instruction */\n    m68ki_instruction_jump_table[REG_IR]();\n    USE_CYCLES(CYC_INSTRUCTION[REG_IR]);"
    assert all(s.count(a)==1 for a in (anchor,before,after)),[(a,s.count(a)) for a in (anchor,before,after)]
    p.write_text(s.replace(anchor,decl+"\n"+anchor).replace(before,before+"\n    retro_ap_before(research_pc & 0xffffff);").replace(after,after+"\n    retro_ap_after(research_pc & 0xffffff,m68k.cycles-research_start);"))
    p=root/"core/vdp_ctrl.c";s=p.read_text()
    anchor="static void vdp_68k_data_w_m5(unsigned int data)\n{"
    assert s.count(anchor)==1
    p.write_text(s.replace(anchor,"extern void retro_ap_vdp_word(void);\n"+anchor+"\n  retro_ap_vdp_word();"))
def profile(core,rom,pose,mode,frames=480):
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==SHA
    lib=C.CDLL(str(core));pad=set();callbacks=[]
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
        ("input_state",C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint),lambda port,dev,index,b:int(port==0 and dev==1 and b in pad))]:
        c=typ(fn);callbacks.append(c);getattr(lib,"retro_set_"+name)(c)
    lib.retro_init();raw=C.create_string_buffer(rom.read_bytes())
    lib.retro_load_game.argtypes=[C.POINTER(Info)];lib.retro_load_game.restype=C.c_bool
    assert lib.retro_load_game(C.byref(Info(os.fsencode(rom),C.cast(raw,C.c_void_p),len(raw)-1,None)))
    assert lib.retro_get_region()==0
    lib.retro_set_controller_port_device(0,1)
    var=lambda k:C.c_uint.in_dll(lib,k)
    var("retro_sram_block").value=mode
    lib.retro_get_memory_data.argtypes=[C.c_uint];lib.retro_get_memory_data.restype=C.c_void_p
    ram=lib.retro_get_memory_data(2);assert ram
    def put(off,val,n):
        b=(val&((1<<(8*n))-1)).to_bytes(n,"big")
        C.memmove(ram+off,b"".join(b[i:i+2][::-1] for i in range(0,n,2)),n)
    def step(n,b=None):
        pad.clear()
        if b is not None:pad.add(b)
        for _ in range(n):lib.retro_run()
    try:
        for n,b in [(120,None),(20,3),(40,None),(20,8),(40,None),(20,8),(60,None)]:step(n,b)
        x,y,z,a=pose
        for off,val,n in [(0x31e6,x*65536,4),(0x31e2,y*65536,4),(0x31de,z*65536,4),(0x31da,0,4),(0x31d6,0,4),(0x31d2,0,4),(0x31ca,a<<8,2),(0x31cc,a,2),(0x1a32,x*8,2),(0x1a30,y*8,2),(0x1a2e,z,2),(0x31c6,0,4)]:put(off,val,n)
        step(120)
        var("retro_ap_n").value=0;var("retro_ap_overflow").value=0
        arr=(C.c_uint*(256*48)).in_dll(lib,"retro_ap_rows")
        C.memset(C.addressof(arr),0,C.sizeof(arr))
        var("retro_ap_active").value=1;var("retro_trace_active").value=1
        var("retro_research_probes").value=0
        var("retro_research_captured").value=0
        var("retro_research_entry_seen").value=0
        var("retro_research_active").value=1
        start=var("retro_trace_dmas").value
        step(frames)
        var("retro_research_active").value=0
        var("retro_ap_active").value=0;var("retro_trace_active").value=0
        count=var("retro_ap_n").value
        assert count>10 and not var("retro_ap_overflow").value,count
        rows=[dict(zip(COLS,arr[i*48:(i+1)*48])) for i in range(count-1)]
        clock=53693175;period=896040
        signed=lambda v:v-65536 if v>=32768 else v
        tick=lambda f,c:f*period+c
        for r in rows:
            for k in ("x8","y8","z"):r[k]=signed(r[k])
            r["render_interval_ms"]=(tick(r["render_end_frame"],r["render_end_cycle"])-tick(r["start_frame"],r["start_cycle"]))*1000/clock
            r["wall_pipeline_ms"]=(tick(r["walls_end_frame"],r["walls_end_cycle"])-tick(r["start_frame"],r["start_cycle"]))*1000/clock
            r["dispatch"]=r["dispatch_linear"]+r["dispatch_perspective"]
        valid=[r for r in rows[1:] if r["list_complete"] and not r["bad_list"] and 0<r["wall_pipeline_ms"]<r["render_interval_ms"]<2000]
        assert len(valid)>=8,(len(valid),len(rows))
        direct=[r for r in valid if r["direct_words"]>=10000]
        intervals=[(tick(b["direct_first_frame"],b["direct_first_cycle"])-tick(a["direct_first_frame"],a["direct_first_cycle"]))*1000/clock for a,b in zip(direct,direct[1:])]
        ndma=var("retro_trace_dmas").value
        dma=(C.c_uint*(32768*6)).in_dll(lib,"retro_trace_dma")
        events=[list(dma[i*6:i*6+6]) for i in range(start,min(ndma,32768))]
        from collections import Counter
        groups=Counter((e[3],e[4]) for e in events)
        means={k:round(statistics.mean(r[k] for r in valid),3) for k in ("records","project","after_transform","dispatch","dispatch_width","wall_scaler_entries","sprite_scaler_entries","render_interval_ms","wall_pipeline_ms","direct_words","direct_calls","sram_convert_calls")}
        cycles={k:sum(r[k] for r in valid) for k in COLS[15:23]}
        total=sum(cycles.values())
        result={"mode":mode,"camera":pose,"complete_frames":len(valid),"means":means,"fps_from_render_interval":1000/means["render_interval_ms"],"direct_bursts":len(direct),"direct_burst_mean_interval_ms":statistics.mean(intervals) if intervals else None,"direct_burst_fps":1000/statistics.mean(intervals) if intervals else None,"dma_groups":[{"destination":a,"words":b,"events":n} for (a,b),n in groups.most_common(10)],"pc_region_percent":{k:round(v*100/total,2) for k,v in cycles.items()},"actual_cameras":sorted({(r["x8"],r["y8"],r["z"],r["angle"],r["cell"]) for r in valid}),"scope":"render-entry cadence and direct-conversion write bursts; PC bins exclusive, not inclusive subroutine times; projection counts and kernel dispatch are actual executed entry points; scaler entries count transitions into generated code, not all flat columns"}
        sc={k:sum(r[k] for r in valid) for k in COLS[40:48]}
        sc["cpu_cycles_per_byte"]=sc["wall_scale_master_cycles"]/7/max(1,sc["wall_scale_pixels"])
        sc["mean_entry_row"]=sc["wall_scale_entry_row_sum"]/max(1,sc["wall_scale_entries"])
        result["wall_scaler_exact"]=sc
        assert sc["wall_scale_pixels"] and sc["wall_scale_other"]==0,sc
        assert mode!=1 or len(direct)>=8,("no-SRAM direct bursts",len(direct))
        assert var("retro_research_captured").value
        def read(key,n):
            return bytes((C.c_ubyte*n).in_dll(lib,key))
        mask=read("retro_packed_mask",11520)
        walls=read("retro_packed_value",11520)
        src=read("retro_research_completed_source",11520)
        vram=read("retro_research_completed_tiles",23040)
        mappings=[]
        for colmajor in (False,True):
            for xswap in (0,1):
                for doubled in (False,True):
                    addresses=[]
                    for i in range(11520):
                        x=2*(i//144)+(i%2)
                        y=(i%144)//2
                        pair=[]
                        for yp in ((2*y,2*y+1) if doubled else (y,y+72)):
                            tile=(x//4)*18+yp//8 if colmajor else (yp//8)*40+x//4
                            pair.append(tile*32+(yp%8)*4+((x%4)^xswap))
                        addresses.append(pair)
                    score=sum(vram[a]==src[i] for i,pair in enumerate(addresses) for a in pair)
                    mappings.append((score,addresses))
        matched,addresses=max(mappings,key=lambda item:item[0])
        chosen={i for i in range(11520) if mask[i] and walls[i]==src[i]}
        assert chosen, "No tracked wall stores survived presentation"
        def counts(parity):
            valid=sorted(i for i in chosen if (i//2)%2==parity)
            values=src if matched!=23040 else bytes(vram[pair[0]] for pair in addresses)
            pairs=[(values[i], values[i+2]) for i in valid if i%144<142 and i+2 in chosen]
            return {"bytes":len(valid),"equal_nibbles":sum(values[i]>>4==values[i]&15 for i in valid),
                    "adjacent_row_pairs":len(pairs),"same":sum(a==b for a,b in pairs),
                    "swapped_distinct":sum(a!=b and a==((b<<4)|(b>>4))&255 for a,b in pairs)}
        result["wall_nibbles"]={"source":"VRAM" if matched==23040 else "WRAM pre-conversion",
                                "layout_matching_bytes":matched,"even":counts(0),"odd":counts(1)}
        return result,valid
    finally:lib.retro_unload_game();lib.retro_deinit()
def main():
    if sys.argv[1]=="patch":patch(P(sys.argv[2]));return
    core,private,report=map(P,sys.argv[2:5]);rom=locate();assert rom
    private.mkdir(parents=True,exist_ok=True)
    scenes={"spawn":(1056,-160,-40,192),**{f"zigzag-{a}":(2980,170,-16,a) for a in (0,64,128,192)}}
    result={}
    for mode in (1,):
        for label,pose in scenes.items():
            k=f"sram{mode}-{label}"
            r,raw=profile(core,rom,pose,mode);result[k]=r
            (private/(k+".json")).write_text(json.dumps(raw,indent=2))
            report.write_text(json.dumps(result,indent=2))
            print("ALPHA2 PROFILE "+k+" "+json.dumps(r),flush=True)
if __name__=="__main__":main()
