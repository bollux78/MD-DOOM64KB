"""S1d Z1: complete E1M1 map-lump geometry preflight on Sega CD sub CPU.
Must also reach G_Ticker on the MD after START/timeout fallback.
This test does not claim P_SetupLevel or G_Ticker on the sub CPU.
"""
import os, subprocess, sys, struct
from pathlib import Path
from r64a_rsp_capture import RSP

rom, elf = map(Path, sys.argv[1:])
nm = Path("/home/dan/mars/m68k-elf/bin/m68k-elf-nm")
sym={}
for line in subprocess.check_output([nm,str(elf)],text=True).splitlines():
    v=line.split()
    if len(v)==3:
        try: sym[v[2].split(".")[0]]=int(v[0],16)&0xFFFFFF
        except ValueError: pass

g=RSP(os.environ["BLASTEM"],rom,16000,600)
try:
    g.req("qSupported")
    for key in ("s1b_complete","I_Error"):
        assert g.req("Z0,%x,2"%sym[key])=="OK",key
    result=None
    for _ in range(10):
        g.cont()
        pc=int(g.req("g")[17*8:18*8],16)&0xFFFFFF
        if pc==sym["I_Error"]:
            raise RuntimeError("I_Error during S1b WAD transport")
        if pc==sym["s1b_complete"]:
            raw=g.readmem(0x61F000,24)
            stage,served,errors,zone_marker,bytes_sent,mdcrc,subcrc,timeouts=struct.unpack(">4H4I",raw)
            result=dict(stage=stage,served=served,errors=errors,zone_marker=hex(zone_marker),bytes=bytes_sent,
                        mdcrc=hex(mdcrc),subcrc=hex(subcrc),timeouts=timeouts)
            break
    assert result is not None, "S1b complete breakpoint not reached"
    print("S1d Z1: real sub E1M1 lump/geometry validation",result,flush=True)
    passed=(result["stage"]==5 and zone_marker==0x5A2D and result["served"]==10 and
            result["errors"]==0 and result["timeouts"]==0 and
            result["bytes"]>0 and result["mdcrc"]==result["subcrc"])
    # After diagnostic let the 15-second timeout start the MD R128 engine.
    for k in ("s1b_complete","I_Error"):
        g.req("z0,%x,2"%sym[k])
    assert g.req("Z0,%x,2"%sym["G_Ticker"])=="OK"
    g.cont()
    pc=int(g.req("g")[17*8:18*8],16)&0xFFFFFF
    played=pc==sym["G_Ticker"]
    print("MD gameplay after START/timeout:",played,flush=True)
    print("S1d Z1 build: PASS; blastem:", "PASS" if passed and played else "FAIL",flush=True)
    assert passed and played
finally:
    g.close()
