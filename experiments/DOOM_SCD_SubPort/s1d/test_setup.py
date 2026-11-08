"""S1d-Z4: real P_SetupLevel geometry phase on Sega CD sub 68000.
Proof marker is emitted only after returning from the actual R128 function.
G_Ticker remains on the MD after START; full P_SetupLevel is not claimed.
"""
import os, subprocess, sys, struct
from pathlib import Path
from r64a_rsp_capture import RSP
visual=len(sys.argv)==4 and sys.argv[1]=="--visual"
engine=len(sys.argv)==4 and sys.argv[1] in ("--engine", "--visual")
ticker=len(sys.argv)==4 and sys.argv[1] in ("--ticker", "--engine", "--visual")
full=len(sys.argv)==4 and sys.argv[1] in ("--full", "--ticker", "--engine", "--visual")
if len(sys.argv)!=(4 if full else 3):
    raise SystemExit("usage: test_setup.py [--full] ROM ELF")
rom, elf=map(Path,sys.argv[2:] if full else sys.argv[1:])
expected=0x5A8D if engine else (0x5A7D if ticker else (0x5A6D if full else 0x5A5D))
nm=Path("/home/dan/mars/m68k-elf/bin/m68k-elf-nm")
symbols={}
for line in subprocess.check_output([nm,str(elf)],text=True).splitlines():
    fields=line.split()
    if len(fields)==3:
        try: symbols[fields[2].split(".")[0]]=int(fields[0],16)&0xFFFFFF
        except ValueError: pass
for attempt in range(3):
    g=RSP(os.environ["BLASTEM"],rom,16000,600)
    try:
        g.req("qSupported")
        break
    except (RuntimeError, BrokenPipeError):
        g.proc.wait(timeout=5)
        err=g.proc.stderr.read().decode(errors="replace")
        g.close()
        if "out of range of a 32-bit displacement" not in err or attempt==2: raise
        print("BlastEm startup JIT allocation failed; retrying before ROM execution",flush=True)
try:
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
    print("Z5 full P_SetupLevel" if full else "Z4 P_SetupLevel geometry",report,flush=True)
    passed=(stage==5 and marker==expected and served==(12 if engine else (11 if ticker else 10)) and errors==0
            and timeouts==0 and bytes_sent>0 and (subcrc!=0 if ticker else mdcrc==subcrc))
    if ticker:
        print("sub last tic",int.from_bytes(g.readmem(0xA12026,2),"big"),flush=True)
        if stage==6:
            print("SUB I_Error:",g.readmem(0x61D000,128).split(b"\0")[0].decode(errors="replace"),flush=True)
        assert passed,"Z6 did not complete; inspect stage/marker/tic above"
        import csv
        fields=("tic","player_x","player_y","player_z","angle","health","mobjs","prndindex")
        raw=g.readmem(0x61E000,27*32)
        rows=[dict(zip(fields,struct.unpack(">IiiiIiII",raw[i*32:(i+1)*32]))) for i in range(27)]
        assert [r["tic"] for r in rows]==list(range(0,2601,100)),rows
        assert len({(r["player_x"],r["player_y"]) for r in rows})>1,"player never moved"
        h=2166136261
        for row in rows:
            for key in fields:h=((h^(row[key]&0xffffffff))*16777619)&0xffffffff
        assert h==subcrc,"trace hash does not match sub completion"
        with (rom.parent/"sub_trace.csv").open("w") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        print("Z8 G_Ticker" if engine else "Z6 P_Ticker", "2600 / trace PASS",rows[-1],flush=True)
        if engine:
            ticks,rebirth,firstdead,leveltime=struct.unpack(">4I",g.readmem(0x61E360,16))
            assert ticks==2600 and rebirth==1 and leveltime==1,(ticks,rebirth,firstdead,leveltime)
            print("Z8 separate controlled real G_Ticker rebirth PASS; first dead natural tic",firstdead,flush=True)
    if visual:
        print("S2a sub trace and rebirth PASS; visual rendering checked in independent process",flush=True)
        raise SystemExit(0)
    for name in ("s1b_complete","I_Error"):
        g.req("z0,%x,2"%symbols[name])
    fallback_symbol="S2A_MDFrameDone" if visual else "G_Ticker"
    assert g.req("Z0,%x,2"%symbols[fallback_symbol])=="OK"
    g.cont()
    pc=int(g.req("g")[17*8:18*8],16)&0xFFFFFF
    fallback=pc==symbols[fallback_symbol]
    print("Z5 build PASS / BlastEm" if full else "Z4 build PASS / BlastEm", "PASS" if passed and fallback else "FAIL",
          "/ MD fallback",fallback,flush=True)
    assert passed and fallback
finally:
    g.close()
