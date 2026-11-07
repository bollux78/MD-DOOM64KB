"""S1d-Z4: real P_SetupLevel geometry phase on Sega CD sub 68000.
Proof marker is emitted only after returning from the actual R128 function.
G_Ticker remains on the MD after START; full P_SetupLevel is not claimed.
"""
import os, subprocess, sys, struct
from pathlib import Path
from r64a_rsp_capture import RSP
rom, elf=map(Path,sys.argv[1:])
nm=Path("/home/dan/mars/m68k-elf/bin/m68k-elf-nm")
symbols={}
for line in subprocess.check_output([nm,str(elf)],text=True).splitlines():
    fields=line.split()
    if len(fields)==3:
        try: symbols[fields[2].split(".")[0]]=int(fields[0],16)&0xFFFFFF
        except ValueError: pass
g=RSP(os.environ["BLASTEM"],rom,16000,600)
try:
    g.req("qSupported")
    for name in ("s1b_complete","I_Error"):
        assert g.req("Z0,%x,2"%symbols[name])=="OK",name
    report=None
    for _ in range(10):
        g.cont()
        pc=int(g.req("g")[17*8:18*8],16)&0xFFFFFF
        if pc==symbols["I_Error"]: raise RuntimeError("R128 MD I_Error")
        if pc==symbols["s1b_complete"]:
            raw=g.readmem(0x61F000,24)
            stage,served,errors,marker,bytes_sent,mdcrc,subcrc,timeouts=struct.unpack(">4H4I",raw)
            report=dict(stage=stage,served=served,errors=errors,
                        marker=hex(marker),bytes=bytes_sent,
                        mdcrc=hex(mdcrc),subcrc=hex(subcrc),timeouts=timeouts)
            break
    assert report is not None,"missing S1d-Z4 completion"
    print("S1d-Z4 actual P_SetupLevel(1) through P_GroupLines:",report,flush=True)
    passed=(stage==5 and marker==0x5A5D and served==10 and errors==0
            and timeouts==0 and bytes_sent>0 and mdcrc==subcrc)
    for name in ("s1b_complete","I_Error"):
        g.req("z0,%x,2"%symbols[name])
    assert g.req("Z0,%x,2"%symbols["G_Ticker"])=="OK"
    g.cont()
    pc=int(g.req("g")[17*8:18*8],16)&0xFFFFFF
    fallback=pc==symbols["G_Ticker"]
    print("Z4 build PASS / BlastEm", "PASS" if passed and fallback else "FAIL",
          "/ MD fallback",fallback,flush=True)
    assert passed and fallback
finally:
    g.close()
