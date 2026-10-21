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
        target=Path(td)/"ym7101.v"
        try:
            with urllib.request.urlopen(BASE+FILE,timeout=45) as response:
                raw=response.read(500000)
            assert git_blob_sha(raw)==GIT_BLOB_SHA,"pinned source integrity mismatch"
            text=raw.decode("utf-8")
            assert "module ym7101" in text
            assert "assign vdp_dma = " in text
            assert "DMA/FIFO block" in text
            target.write_bytes(raw)
            report["rtl_fetched_and_sha_verified"]=True
            report["source_length_bytes"]=len(raw)
            report["git_blob_sha1"]=git_blob_sha(raw)
            report["source_sha256"]=hashlib.sha256(raw).hexdigest()
            if shutil.which("iverilog"):
                p=subprocess.run(["iverilog","-g2012","-tnull","-s","ym7101",str(target)],
                                 capture_output=True,text=True,timeout=90)
                report["iverilog_exit_status"]=p.returncode
                report["iverilog_diagnostics"]=p.stderr[-1800:]
                report["rtl_elaborated"]=(p.returncode==0)
            elif shutil.which("verilator"):
                p=subprocess.run(["verilator","--lint-only","--top-module","ym7101",
                                  "-Wno-fatal",str(target)],
                                 capture_output=True,text=True,timeout=90)
                report["verilator_exit_status"]=p.returncode
                report["verilator_diagnostics"]=p.stderr[-1800:]
                report["rtl_elaborated"]=(p.returncode==0)
            else:
                report["elaboration_note"]="Neither Icarus Verilog nor Verilator installed; no HDL compile attempted"
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
