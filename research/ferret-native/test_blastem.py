"""BlastEm RSP verification after the R01 publication checkpoint."""
import argparse, pathlib, json, struct, sys
P=pathlib.Path
sys.path.insert(0,str(P(__file__).resolve().parents[2]/"scripts/lab"))
from r64a_rsp_capture import RSP,symbols
from test_demo import host,fnv
def main():
    p=argparse.ArgumentParser();p.add_argument("out",type=P);p.add_argument("blastem");p.add_argument("report",type=P);a=p.parse_args()
    expected=host(a.out);syms=symbols(a.out/"demo.elf")
    checkpoint=syms.get("fr_published",syms.get("_fr_published"));assert checkpoint,"checkpoint missing"
    frame=next(v for k,v in syms.items() if k=="frame" or k.startswith("frame."))
    work=next((v for k,v in syms.items() if k=="worktiles" or k.startswith("worktiles.")),None)
    g=RSP(a.blastem,str(a.out/"FERRET-MD-R01.bin"),6000,90)
    checks=[];err=None
    try:
        g.req("qSupported");assert g.req(f"Z0,{checkpoint:x},2")=="OK"
        for i,e in enumerate(expected):
            g.cont();m=struct.unpack(">17I",g.readmem(0xfff000,68))
            h=fnv(g.readmem(frame&0xffffff,11520))
            dst=0x20a600 if m[11] else work
            tile=fnv(g.readmem(dst&0xffffff,23040)) if dst else None
            ok=m[0]==0x46523031 and m[1]==i+1 and m[2]==5 and m[4]==i and m[5]==h==e["hash"] and m[6]==tile==e["tiles_hash"] and m[7]==e["candidates"] and m[8]==e["projected"] and m[9]==e["errors"] and m[10]==e["closed"] and m[12]==0
            checks.append({"pose":i,"match":ok,"fb":h,"expected_fb":e["hash"],"tiles":tile,"expected_tiles":e["tiles_hash"],"sram":m[11],"mailbox":list(m)})
    except Exception as ex:err=type(ex).__name__+": "+str(ex)
    finally:g.close()
    result={"expected":len(expected),"checks":checks,"matched":sum(c["match"] for c in checks),"error":err,"pass":err is None and len(checks)==len(expected) and all(c["match"] for c in checks),"scope":"actual CPU and DMA completion status; staging bytes checked, VRAM not independently read"}
    a.report.write_text(json.dumps(result,indent=2));print("BLASTEM "+json.dumps(result),flush=True)
    if not result["pass"]:sys.exit(2)
if __name__=="__main__":main()
