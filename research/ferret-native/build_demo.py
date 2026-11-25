"""Build bare-metal R01 without SGDK startup dependencies.
Only generated fixture ROM is intended for artifact publication.
"""
import argparse,json,pathlib,struct,subprocess,hashlib
P=pathlib.Path
def main():
    p=argparse.ArgumentParser();p.add_argument("out",type=P);p.add_argument("gcc",type=P);p.add_argument("--label",default="FERRET-MD R01");a=p.parse_args()
    src=P(__file__).resolve().parent;out=a.out.resolve();gcc=a.gcc.resolve()
    flags=["-m68000","-std=c99","-O2","-ffreestanding","-fno-builtin","-ffunction-sections","-fdata-sections","-fno-common","-fno-pic","-fno-unwind-tables","-fno-asynchronous-unwind-tables"]
    def run(args):subprocess.run([str(x) for x in args],check=True)
    run(["cc","-std=c99","-O2","-fPIC","-shared","-I",out,src/"demo.c","-o",out/"demo-host.so"])
    run([gcc,*flags,"-I",out,"-c",src/"demo.c","-o",out/"demo.o"])
    run([gcc,"-m68000","-c",src/"boot.s","-o",out/"boot.o"])
    run([gcc,"-m68000","-nostdlib","-Wl,--gc-sections","-Wl,-T,"+str(src/"md.ld"),"-Wl,-Map,"+str(out/"demo.map"),out/"boot.o",out/"demo.o","-lgcc","-o",out/"demo.elf"])
    objcopy=gcc.with_name(gcc.name.replace("gcc","objcopy"))
    run([objcopy,"-O","binary",out/"demo.elf",out/"demo.bin"])
    b=bytearray((out/"demo.bin").read_bytes());assert len(b)>512
    length=max(131072,(len(b)+65535)&~65535);assert length<=0x200000
    b.extend(b"\xff"*(length-len(b)))
    def field(a,n,v):b[a:a+n]=v.encode("ascii")[:n].ljust(n,b" ")
    field(0x100,16,"SEGA MEGA DRIVE");field(0x110,16,"(C) BOLLUX 2026")
    field(0x120,48,a.label);field(0x150,48,a.label);field(0x180,14,"GM 00000000-00")
    field(0x190,16,"J");struct.pack_into(">IIII",b,0x1a0,0,length-1,0xff0000,0xffffff)
    b[0x1b0:0x1b4]=b"RA\xf8\x20";struct.pack_into(">II",b,0x1b4,0x200000,0x20ffff)
    field(0x1bc,12,"");field(0x1c8,40,"R01 DIAGNOSTIC");field(0x1f0,16,"U")
    struct.pack_into(">H",b,0x18e,sum(v[0] for v in struct.iter_unpack(">H",b[0x200:]))&65535)
    (out/"FERRET-MD-R01.bin").write_bytes(b)
    result={"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"entry":struct.unpack_from(">I",b,4)[0],"sram_start":0x200000,"sram_end":0x20ffff}
    (out/"build.json").write_text(json.dumps(result));print("ROM BUILD "+json.dumps(result),flush=True)
if __name__=="__main__":main()
