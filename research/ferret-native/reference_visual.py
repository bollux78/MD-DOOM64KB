"""Private actual Alpha2 video reference capture, no runtime dependency.
Uses the known, authenticated Alpha2 ROM and existing debug pose convention.
Images and raw CRAM stay on x360; only aggregate image statistics may leave.
"""
import ctypes as C,os,pathlib,sys,json,collections
from PIL import Image
P=pathlib.Path
sys.path.insert(0,str(P(__file__).resolve().parent.parent/"ferret-round5"))
from capture import locate
from test_demo import Info
def run(core,rom,out,pose):
    lib=C.CDLL(str(core));cb=[];pad=set();fmt=0;last=None
    def env(cmd,p):
        nonlocal fmt
        if cmd==3:C.cast(p,C.POINTER(C.c_bool))[0]=True;return True
        if cmd==10:
            fmt=C.cast(p,C.POINTER(C.c_int))[0];return fmt in (0,1,2)
        return False
    def video(data,w,h,pitch):
        nonlocal last
        if not data or data==C.c_void_p(-1).value or w<=0 or h<=0:return
        bpp=4 if fmt==1 else 2
        raw=C.string_at(data,pitch*h)
        last=(w,h,bpp,fmt,b"".join(raw[y*pitch:y*pitch+w*bpp] for y in range(h)))
    for name,typ,fn in [
        ("environment",C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p),env),
        ("video_refresh",C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t),video),
        ("audio_sample",C.CFUNCTYPE(None,C.c_int16,C.c_int16),lambda *a:None),
        ("audio_sample_batch",C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t),lambda d,n:n),
        ("input_poll",C.CFUNCTYPE(None),lambda:None),
        ("input_state",C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint),lambda port,dev,index,b:int(port==0 and dev==1 and b in pad))]:
        c=typ(fn);cb.append(c);getattr(lib,"retro_set_"+name)(c)
    lib.retro_init();raw=C.create_string_buffer(rom.read_bytes())
    lib.retro_load_game.argtypes=[C.POINTER(Info)];lib.retro_load_game.restype=C.c_bool
    assert lib.retro_load_game(C.byref(Info(os.fsencode(rom),C.cast(raw,C.c_void_p),len(raw)-1,None)))
    lib.retro_set_controller_port_device(0,1)
    C.c_uint.in_dll(lib,"retro_sram_block").value=0
    lib.retro_get_memory_data.argtypes=[C.c_uint];lib.retro_get_memory_data.restype=C.c_void_p
    ram=lib.retro_get_memory_data(2);assert ram
    lib.retro_dread_cram_word.argtypes=[C.c_uint];lib.retro_dread_cram_word.restype=C.c_uint
    def put(off,val,n):
        b=(val&((1<<(n*8))-1)).to_bytes(n,"big")
        C.memmove(ram+off,b"".join(b[i:i+2][::-1] for i in range(0,n,2)),n)
    def step(n,b=None):
        pad.clear()
        if b is not None:pad.add(b)
        for _ in range(n):lib.retro_run()
    try:
        for n,b in [(120,None),(20,3),(40,None),(20,8),(40,None),(20,8),(60,None)]:step(n,b)
        if pose is not None:
            x,y,z,angle=pose
            for off,val,n in [(0x31e6,x*65536,4),(0x31e2,y*65536,4),(0x31de,z*65536,4),(0x31da,0,4),(0x31d6,0,4),(0x31d2,0,4),(0x31ca,angle<<8,2),(0x31cc,angle,2),(0x1a32,x*8,2),(0x1a30,y*8,2),(0x1a2e,z,2),(0x31c6,0,4)]:put(off,val,n)
        step(180);assert last is not None
        w,h,bpp,fmt,buf=last
        if fmt==1:im=Image.frombytes("RGB",(w,h),buf,"raw","BGRX")
        else:
            pixels=[]
            for i in range(0,len(buf),2):
                v=int.from_bytes(buf[i:i+2],sys.byteorder)
                if fmt==2:pixels.append(((v>>11&31)*255//31,(v>>5&63)*255//63,(v&31)*255//31))
                else:pixels.append(((v>>10&31)*255//31,(v>>5&31)*255//31,(v&31)*255//31))
            im=Image.new("RGB",(w,h));im.putdata(pixels)
        im.save(out.with_suffix(".png"))
        cram=[int(lib.retro_dread_cram_word(i*2)) for i in range(64)]
        out.with_suffix(".cram.json").write_text(json.dumps(cram))
        colors=collections.Counter(im.getdata())
        return {"width":w,"height":h,"unique_rgb":len(colors),"nonblack_fraction":1-colors.get((0,0,0),0)/(w*h),"format":fmt}
    finally:lib.retro_unload_game();lib.retro_deinit()
def main():
    core,out,report=map(P,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
    rom=locate();assert rom,"verified original Alpha2 unavailable"
    scenes={"spawn":None,**{f"zigzag-{a}":(2980,170,-16,a) for a in (0,64,128,192)}}
    rows={}
    for k,p in scenes.items():rows[k]=run(core,rom,out/k,p)
    report.write_text(json.dumps(rows,indent=2));print("ALPHA2 ACTUAL VIDEO "+json.dumps(rows),flush=True)
if __name__=="__main__":main()
