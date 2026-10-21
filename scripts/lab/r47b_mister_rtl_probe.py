#!/usr/bin/env python3
"""Pin/inspect upstream MiSTer Nuked-MD YM7101 RTL, optionally elaborate it.

Outputs provenance, source verification and tool availability. RTL
elaboration is NOT a functional bus/DMA benchmark; this does not run Doom.
No copy of upstream GPL RTL is committed to our repository.
"""
import hashlib, json, shutil, subprocess, tempfile, urllib.request
from pathlib import Path
import argparse

CORE_COMMIT="becbdee78c48e6eb536871cd03c869f43d7afa4d"
FILE="rtl/nuked-md/ym7101.v"
GIT_BLOB_SHA="0862948114ddb7abec87e46fdbb16d4fa2172804"
DEPENDENCY="rtl/nuked-md/ym_lib.v"
DEPENDENCY_BLOB_SHA="26fce976757bda2612e7ec0effcc93868660e108"
BASE=f"https://raw.githubusercontent.com/MiSTer-devel/MegaDrive_MiSTer/{CORE_COMMIT}/"

def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="")
    args=p.parse_args()
    report={"source":"MiSTer-devel/MegaDrive_MiSTer",
            "commit":CORE_COMMIT,"module":FILE,
            "rtl_fetched_and_sha_verified":False,
            "rtl_elaborated":False,
            "actual_vdp_dma_simulated":False,
            "full_rom_tested":False,
            "iverilog_available":bool(shutil.which("iverilog")),
            "verilator_available":bool(shutil.which("verilator"))}
    with tempfile.TemporaryDirectory(prefix="doom-r47b-rtl-") as td:
        try:
            inputs=[]
            for source,expected in ((FILE,GIT_BLOB_SHA),(DEPENDENCY,DEPENDENCY_BLOB_SHA)):
                with urllib.request.urlopen(BASE+source,timeout=45) as response:
                    raw=response.read(500000)
                assert git_blob_sha(raw)==expected,("pinned RTL mismatch",source)
                v=raw.decode("utf-8")
                if source==FILE:
                    assert "module ym7101" in v
                    assert "assign vdp_dma = " in v
                    assert "DMA/FIFO block" in v
                else:
                    assert "module ym_slatch" in v and "module ym_sr_bit" in v
                target=Path(td)/Path(source).name
                target.write_bytes(raw)
                inputs.append(str(target))
                report.setdefault("pinned_sources",{})[source]={
                    "bytes":len(raw),"git_blob_sha1":git_blob_sha(raw),
                    "sha256":hashlib.sha256(raw).hexdigest()}
            report["rtl_fetched_and_sha_verified"]=True
            report["source_length_bytes"]=report["pinned_sources"][FILE]["bytes"]
            report["git_blob_sha1"]=report["pinned_sources"][FILE]["git_blob_sha1"]
            report["source_sha256"]=report["pinned_sources"][FILE]["sha256"]
            if shutil.which("iverilog"):
                p=subprocess.run(["iverilog","-g2012","-tnull","-s","ym7101"]+inputs,
                                 capture_output=True,text=True,timeout=120)
                report["iverilog_exit_status"]=p.returncode
                report["iverilog_diagnostics"]=p.stderr[-1800:]
                report["rtl_elaborated"]=(p.returncode==0)
            elif shutil.which("verilator"):
                p=subprocess.run(["verilator","--lint-only","--top-module","ym7101",
                                  "-Wno-fatal"]+inputs,
                                 capture_output=True,text=True,timeout=120)
                report["verilator_exit_status"]=p.returncode
                report["verilator_diagnostics"]=p.stderr[-1800:]
                report["rtl_elaborated"]=(p.returncode==0)
            else:
                report["elaboration_note"]="Icarus/Verilator missing; pinned source only verified"
        except Exception as exc:
            report["error"]=repr(exc)
    if args.out:
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    # Fetching failures are a separate availability problem. Do not mark
    # source integrity failures as success when upstream is accessible.
    if report["rtl_fetched_and_sha_verified"] is False:
        raise SystemExit("R47B FAIL: upstream pinned RTL could not be verified")
    if "iverilog_exit_status" in report and not report["rtl_elaborated"]:
        raise SystemExit("R47B FAIL: YM7101 RTL failed Icarus elaboration")

if __name__=="__main__":
    main()
